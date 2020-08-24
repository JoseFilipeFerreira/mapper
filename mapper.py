import glob
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

reversed_tags = dict(zip(TAGS.values(), TAGS.keys()))
ID_GPS = reversed_tags['GPSInfo']

def get_all_photos(dir):
    files = []
    for ext in ['.jpeg', '.jpg', '.png']:
        files.extend(glob.glob(dir + '/**/*' + ext, recursive=True))

    return files

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
        return [gps_info['Latitude'], gps_info['Longitude']]
    else:
        return None

plt.figure(figsize=(200, 200))

ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_global()
ax.set_facecolor((0.0, 0.0, 0.0))
ax.coastlines(resolution='10m', color='white')

ax.add_feature(
        cfeature.BORDERS.with_scale('10m'),
        linestyle=':',
        color='white')

for file in get_all_photos('photos'):
    img_exif = Image.open(file).getexif()

    if img_exif and img_exif.get(ID_GPS):
        gps_info = {}
        gps_dict = img_exif.get(ID_GPS)

        for key, value in gps_dict.items():
            gps_info[GPSTAGS.get(key, key)] = value

        coords = get_decimal_coordinates(gps_info)

        if coords:
            ax.plot(coords[1], coords[0], markersize=2, marker='o', color='red')

plt.savefig('map.png')
plt.show()
