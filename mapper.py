import glob
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

reversed_tags = dict(zip(TAGS.values(), TAGS.keys()))
ID_GPS = reversed_tags['GPSInfo']

RATIO = 16.0/9

def get_all_photos(dir):
    for ext in ['.jpeg', '.jpg', '.png']:
        for file in glob.glob(dir + '/**/*' + ext, recursive=True):
            yield file

def get_decimal_coordinates(gps_info):
    for key in ['Latitude', 'Longitude']:
        if 'GPS' + key in gps_info and 'GPS' + key + 'Ref' in gps_info:
            e = gps_info['GPS' + key]
            ref = gps_info['GPS' + key + 'Ref']
            gps_info[key] = float( e[0] +
                              e[1] / 60 +
                              e[2] / 3600
                            ) * (-1 if ref in ['S','W'] else 1)

    if 'Latitude' in gps_info and 'Longitude' in gps_info:
        return gps_info['Latitude'], gps_info['Longitude']
    else:
        return None

def get_curr_extent(coords, ratio):
    # calculate min and max
    minlat, maxlat = 90, -90
    minlong, maxlong = 180, -180

    for lat, long in coords:
        if lat < minlat:
            minlat = lat
        if lat > maxlat:
            maxlat = lat
        if long < minlong:
            minlong = long
        if long > maxlong:
            maxlong = long

    # calculta center coordinates
    centerlat = (minlat + maxlat)/2
    centerlong = (minlong + maxlong)/2

    # calculate side vector
    veclat = abs(maxlat - minlat)
    veclong = abs(maxlong - minlong)

    if centerlat + veclat > 90 or centerlat - veclat < -90 :
        veclat = veclat / 1.9

    if centerlong + veclong > 180 or centerlong - veclong < -180 :
        veclong = veclong / 1.9

    # set ratio
    if veclat < veclong / ratio:
        veclat = veclong / ratio
    elif veclong < veclat * ratio:
        veclong = veclat * ratio

    # calculate extent
    minlat = centerlat - veclat
    maxlat = centerlat + veclat
    minlong = centerlong - veclong
    maxlong = centerlong + veclong

    # fix out of bounds extent
    if maxlong > 180:
        minlong -= maxlong - 180
        maxlong = 180

    if minlong < -180:
        maxlong -= minlong + 180
        minlong = -180

    if maxlat > 90:
        minlat -= maxlat - 90
        maxlat = 90

    if minlat < -90:
        maxlat -= minlat + 90
        minlat = -90

    return [minlong, maxlong, minlat, maxlat]

all_coords = []
for file in get_all_photos('photos'):
    img_exif = Image.open(file).getexif()

    if img_exif and img_exif.get(ID_GPS):
        gps_info = {}
        gps_dict = img_exif.get(ID_GPS)

        for key, value in gps_dict.items():
            gps_info[GPSTAGS.get(key, key)] = value

        coords = get_decimal_coordinates(gps_info)

        if coords:
            all_coords.append(coords)

plt.figure(figsize=(RATIO * 100, 100 / RATIO))

ax = plt.axes(projection=ccrs.PlateCarree())

ax.set_facecolor((0.0, 0.0, 0.0))

ax.add_feature(
        cfeature.COASTLINE.with_scale('10m'),
        color='white',
        linewidth=4)

ax.add_feature(
        cfeature.BORDERS.with_scale('10m'),
        linestyle=':',
        color='white',
        linewidth=2)

ax.set_extent(
    get_curr_extent(all_coords, RATIO),
    crs=ccrs.PlateCarree())

for lat, long in all_coords:
    ax.plot(long, lat, markersize=15, marker='o', color='red')

plt.savefig(
    'map.png',
    bbox_inches = 'tight',
    pad_inches = 0)
# plt.show()
