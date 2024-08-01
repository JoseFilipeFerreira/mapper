"""create a map with all the places of the photos in a folder"""

import json
import os
from typing import Generator, Iterable, Tuple, Optional, List
import subprocess

from datetime import datetime, timedelta
from math import cos
import matplotlib.pyplot as plt
import cartopy
from cartopy import crs, feature
from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS, IFD
from tqdm import tqdm
from scipy.spatial import cKDTree
from dataclasses import dataclass

class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime('%Y:%m:%d %H:%M:%S')

        return json.JSONEncoder.default(self, o)

def hex_to_rgb(value: str) -> Tuple[float, float, float]:
    """convert hex colors to rgb"""
    value = value.lstrip('#')
    length = len(value)
    return tuple(int(value[i:i + length // 3], 16)/255 for i in range(0, length, length // 3))

IMAGE_RATIO=float(os.environ.get("IMAGE_RATIO", default=16/9))
FILTER_DISTANCE=float(os.environ.get("FILTER_DISTANCE", default=10))

CACHE_FOLDER=os.environ.get("CACHE_FOLDER", default="/cache")
CACHE_COORDINATES=CACHE_FOLDER + "/coordinates.json"
CACHE_CARTOPY=CACHE_FOLDER + "/cartopy"

IMAGE_FOLDER=os.environ.get("IMAGE_FOLDER", default="/images")
EXPORT_PATH=os.environ.get("EXPORT_PATH", default="/export/")

# Image config
BG_COLOR=hex_to_rgb(os.environ.get("BG_COLOR", default="#000000"))
FG_COLOR=hex_to_rgb(os.environ.get("FG_COLOR", default="#FFFFFF"))
MARKER_COLOR=hex_to_rgb(os.environ.get("MARKER_COLOR", default="#FF0000"))

COAST_WIDTH = int(os.environ.get("COAST_WIDTH", default=3))
BORDERS_WIDTH = int(os.environ.get("BORDERS_WIDTH", default=2))
MARKER_WIDTH= int(os.environ.get("MARKER_WIDTH",default=12))
FRAMERATE = int(os.environ.get("FRAMERATE",default=5))


def create_gif(images: List[str]):
    command = ["ffmpeg", "-framerate", str(FRAMERATE), "-pattern_type", "glob", "-i", f"{EXPORT_PATH}*.png"]
    # command.extend(images)
    command.extend(["-vf", "scale=2048:-1", f"{EXPORT_PATH}map.gif"])

    print(command)

    result = subprocess.run(command, capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)

@dataclass
class Photo:
    filename: str
    coords: Tuple[float, float]
    date: "datetime"

    def __init__(self, filename: str, coords: Tuple[float, float], date:str):
        self.filename = filename
        self.coords = coords
        self.date = datetime.strptime(date, '%Y:%m:%d %H:%M:%S')

    def __eq__(self, other):
        return self.date == other.date

    def __lt__(self, other):
        return self.date < other.date

def filter_dates(photos: Iterable[Photo], threshold_date: datetime) -> Generator[Photo, None, None]:

    for photo in photos:
        if photo.date < threshold_date:
            yield photo
        else:
            break

def create_date_slices(photos: List[Photo]) -> Generator[List[Photo], None, None]:

    start_date = photos[0].date
    end_date = photos[-1].date
    days = [start_date + timedelta(days=x + 1) for x in range((end_date - start_date).days)]

    last_number_photos = 0
    for day in tqdm(days, desc="Creating Day Slices  "):
        photos_before = list(filter_dates(photos, day))

        current_number_photos = len(photos_before)

        if last_number_photos != current_number_photos:
            last_number_photos = current_number_photos
            yield photos_before

def main():
    """ main function """

    cartopy.config["data_dir"] = CACHE_CARTOPY

    paths = get_all_photo_paths(IMAGE_FOLDER)
    photos = get_photos_from_paths(paths)

    sorted_photos = sorted(photos)

    photos_slices = create_date_slices(sorted_photos)

    filtered_photos = []
    for slice in tqdm(photos_slices, desc="Filtering Day Slices "):
        filtered_photos.append(filter_nearby_photos(slice))

    created_images = []
    for filtered in tqdm(filtered_photos, desc="Creating Maps        "):

        path = f"{EXPORT_PATH}map_{filtered[-1].date.strftime('%Y%m%d%H%M%S')}.png"
        created_images.append(path)

        if os.path.exists(path):
            continue

        plt.figure(figsize=(IMAGE_RATIO * 100, 100 / IMAGE_RATIO))

        plot = plt.axes(projection=crs.PlateCarree())

        plot.set_facecolor(BG_COLOR)

        plot.add_feature(
            feature.COASTLINE.with_scale('10m'),
            color=FG_COLOR,
            linewidth=COAST_WIDTH)

        plot.add_feature(
            feature.BORDERS.with_scale('10m'),
            linestyle=':',
            color=FG_COLOR,
            linewidth=BORDERS_WIDTH)

        plot.set_extent(get_curr_extent(filtered), crs=crs.PlateCarree())

        for photo in filtered:
            lat, long = photo.coords
            plot.plot(long, lat, markersize=MARKER_WIDTH, marker='o', color=MARKER_COLOR)

        # save image
        plt.savefig(path, bbox_inches = 'tight', pad_inches = 0)

        plt.close()

    create_gif(created_images)



def get_all_photo_paths(folder: str) -> Generator[str, None, None]:
    """return all photos in a folder recursively"""
    for currentpath, _, files in tqdm(os.walk(folder), desc="Fetching Paths       "):
        for file in files:
            _, extension = os.path.splitext(file)
            if extension in ['.jpeg', '.jpg', '.png']:
                yield os.path.join(currentpath, file)

def decimal_coords(coords: Tuple[int, int, int], ref: str) -> float:
    """convert from coords tuples to deciaml coords"""
    decimal_degrees = coords[0] + coords[1] / 60 + coords[2] / 3600
    if ref in ['S', 'W']:
        decimal_degrees = -decimal_degrees
    return float(decimal_degrees)


def get_photos_from_paths(photos: Iterable[str]) -> Generator[Photo, None, None]:
    """get the coordinates of all photos"""
    try:
        with open(CACHE_COORDINATES, "r", encoding="utf-8") as file:
            coordinates_cache = json.load(file)
    except (IOError, json.JSONDecodeError):
        coordinates_cache = {}

    for photo in tqdm(photos, desc="Fetching Photos      "):

        if photo in coordinates_cache:
            cache = coordinates_cache[photo]
            if cache:
                yield Photo(**cache)
            continue

        img = Image.open(photo)
        exif = img.getexif()

        exif_map = { ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS and type(v) is not bytes }

        gps_info={}
        for key, value in exif.get_ifd(IFD.GPSInfo).items():
            geo_tag=GPSTAGS.get(key)
            gps_info[geo_tag]=value

        try:
            date_taken = exif_map['DateTime']

            convert_coords = (decimal_coords(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef']),
            decimal_coords(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef']))

            photo_obj = Photo(photo, convert_coords, date_taken)
            coordinates_cache[photo] = vars(photo_obj)
            yield photo_obj

        except KeyError:
            coordinates_cache[photo] = None
            continue

    with open(CACHE_COORDINATES, "w", encoding="utf-8") as file:
        json.dump(coordinates_cache, file, cls=DateTimeEncoder)

def km_to_degrees(latitude, km):
    """Convert from kilometers to degrees"""
    # Approximate conversion: 1 degree of latitude ~= 111.12 km
    # Conversion for longitude depends on latitude
    degrees_lat = km / 111.12
    degrees_lon = km / (111.12 * cos(latitude))
    return degrees_lat, degrees_lon

def filter_nearby_photos(photos: List[Photo]) -> Iterable[Photo]:
    """filter photos that have another photo closer than FILTER_DISTANCE"""
    points = [photo.coords for photo in photos]
    tree = cKDTree(points)

    threshold_deg_lat, threshold_deg_lon = km_to_degrees(photos[0].coords[0], FILTER_DISTANCE)
    threshold_deg = max(threshold_deg_lat, threshold_deg_lon)

    filtered_indices = set()
    for i in range(len(photos)):
        if i in filtered_indices:
            continue
        nearby_indices = tree.query_ball_point(points[i], threshold_deg)
        filtered_indices.update(nearby_indices)
        filtered_indices.discard(i)  # Exclude self

    # Filter out the photos based on the filtered indices
    filtered_photos = [photos[i] for i in range(len(photos)) if i not in filtered_indices]

    return filtered_photos

def get_curr_extent(photos: Iterable[Photo]) -> Tuple[float, float, float, float]:
    """ compute a border arround a list of photos respecting a specific ratio"""
    lats = [ x.coords[0] for x in photos ]
    longs = [ x.coords[1] for x in photos ]

    # calculate min and max
    minlat = min(lats)
    maxlat = max(lats)
    minlong = min(longs)
    maxlong = max(longs)

    # calculate center coordinates
    centerlat = (minlat + maxlat)/2
    centerlong = (minlong + maxlong)/2

    # calculate side vector with margin
    veclat = abs(maxlat - minlat)/2 * 1.1
    veclong = abs(maxlong - minlong)/2 * 1.1

    # if there is no vector create small square
    if veclat == 0 or veclong == 0:
        veclat = 0.5
        veclong = 0.5

    # set ratio
    if veclat < veclong / IMAGE_RATIO:
        veclat = veclong / IMAGE_RATIO
    elif veclong < veclat * IMAGE_RATIO:
        veclong = veclat * IMAGE_RATIO

    # calculate extent
    minlat = centerlat - veclat
    maxlat = centerlat + veclat
    minlong = centerlong - veclong
    maxlong = centerlong + veclong

    return (minlong, maxlong, minlat, maxlat)


    # fix out of bounds extent
    # if maxlong > 180:
    #     minlong -= maxlong - 180
    #     maxlong = 180

    # if minlong < -180:
    #     maxlong -= minlong + 180
    #     minlong = -180

    # if maxlat > 90:
    #     minlat -= maxlat - 90
    #     maxlat = 90

    # if minlat < -90:
    #     maxlat -= minlat + 90
    #     minlat = -90

main()
