"""create a map with all the places of the photos in a folder"""

import json
import os
from typing import Generator, Iterable, Tuple, Optional, List

from math import cos
import matplotlib.pyplot as plt
import cartopy
from cartopy import crs, feature
from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS, IFD
from tqdm import tqdm
from scipy.spatial import cKDTree
from dataclasses import dataclass


def hex_to_rgb(value: str) -> Tuple[float, float, float]:
    """convert hex colors to rgb"""
    value = value.lstrip('#')
    length = len(value)
    return tuple(int(value[i:i + length // 3], 16)/255 for i in range(0, length, length // 3))

IMAGE_RATIO=float(os.environ.get("IMAGE_RATIO", default=16/9))
FILTER_DISTANCE=float(os.environ.get("FILTER_DISTANCE", default=30))

CACHE_FOLDER=os.environ.get("CACHE_FOLDER", default="/cache")
CACHE_COORDINATES=CACHE_FOLDER + "/coordinates.json"
CACHE_CARTOPY=CACHE_FOLDER + "/cartopy"

IMAGE_FOLDER=os.environ.get("IMAGE_FOLDER", default="/images")
EXPORT_IMAGE=os.environ.get("EXPORT_IMAGE", default="/export/map.png")

# Image config
BG_COLOR=hex_to_rgb(os.environ.get("BG_COLOR", default="#000000"))
FG_COLOR=hex_to_rgb(os.environ.get("FG_COLOR", default="#FFFFFF"))
MARKER_COLOR=hex_to_rgb(os.environ.get("MARKER_COLOR", default="#FF0000"))

COAST_WIDTH = int(os.environ.get("COAST_WIDTH", default=4))
BORDERS_WIDTH = int(os.environ.get("BORDERS_WIDTH", default=2))
MARKER_WIDTH= int(os.environ.get("MARKER_WIDTH",default=12))

@dataclass
class Photo:
    filename: str
    coords: Tuple[float, float]
    date: Optional[str]

def main():
    """ main function """

    cartopy.config["data_dir"] = CACHE_CARTOPY

    photos = list(get_all_photos(IMAGE_FOLDER))
    total_photos_len = len(photos)
    print("Total photos: ", total_photos_len)

    photos = list(get_all_coordinates(photos))
    filtered_photos_len = len(photos)
    print(f"Photos with GPS info: {filtered_photos_len} ({int(filtered_photos_len/total_photos_len*100)}%)")

    photos = list(filter_nearby_photos(photos))
    print(f"Photos remaining: {len(photos)}")


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

    plot.set_extent(get_curr_extent(photos), crs=crs.PlateCarree())

    for photo in tqdm(photos, desc="writing coordinates"):
        lat, long = photo.coords
        plot.plot(long, lat, markersize=MARKER_WIDTH, marker='o', color=MARKER_COLOR)

    # save image
    print("Saving image")
    plt.savefig(EXPORT_IMAGE, bbox_inches = 'tight', pad_inches = 0)
    print("Done!")


def get_all_photos(folder: str) -> Generator[str, None, None]:
    """return all photos in a folder recursively"""
    for currentpath, _, files in os.walk(folder):
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


def get_all_coordinates(photos: Iterable[str]) -> Generator[Photo, None, None]:
    """get the coordinates of all photos inside a folder recursively"""
    try:
        with open(CACHE_COORDINATES, "r", encoding="utf-8") as file:
            coordinates_cache = json.load(file)
    except (IOError, json.JSONDecodeError):
        coordinates_cache = {}

    for photo in tqdm(photos, desc="fetching coordinates"):

        if photo in coordinates_cache:
            cache = coordinates_cache[photo]
            if cache:
                yield Photo(**cache)
            continue

        img = Image.open(photo)
        exif = img.getexif()

        exif_map = { ExifTags.TAGS[k]: v for k, v in exif.items() if k in ExifTags.TAGS and type(v) is not bytes }

        date_taken = exif_map.get('DateTime')

        gps_info={}
        for key, value in exif.get_ifd(IFD.GPSInfo).items():
            geo_tag=GPSTAGS.get(key)
            gps_info[geo_tag]=value

        try:
            convert_coords = (decimal_coords(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef']),
            decimal_coords(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef']))

            photo_obj = Photo(photo, convert_coords, date_taken)
            coordinates_cache[photo] = vars(photo_obj)
            yield photo_obj


        except KeyError:
            coordinates_cache[photo] = None
            continue

    with open(CACHE_COORDINATES, "w", encoding="utf-8") as file:
        json.dump(coordinates_cache, file)

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
    for i in tqdm(range(len(photos)), desc="Filtering points"):
        if i in filtered_indices:
            continue
        nearby_indices = tree.query_ball_point(points[i], threshold_deg)
        filtered_indices.update(nearby_indices)
        filtered_indices.discard(i)  # Exclude self

    # Filter out the photos based on the filtered indices
    filtered_photos = [photos[i] for i in range(len(photos)) if i not in filtered_indices]

    return filtered_photos

def get_curr_extent(photos: Iterable[Photo]) -> Tuple[float, float, float, float]:
    """ compute a border arround a list of coords respecting a specific ratio"""
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
