# :world_map:  mapper
Plot all your photos on a map using cartopy

# Usage
Build the container or use
[josefilipeferreira/mapper](https://hub.docker.com/repository/docker/josefilipeferreira/mapper)

Configure behaviour via env variables

| Variable            | Description                       | Deafult           |
|---------------------|-----------------------------------|-------------------|
| `IMAGE_FOLDER`      | location of image folder          | `/images`         |
| `EXPORT_IMAGE`      | loaction of image to export       | `/export/map.png` |
| `CACHE_FOLDER`      | location of cache folder          | `/cache`          |
| `IMAGE_RATIO`       | change image aspect ratio         | `1.6`             |
| `BG_COLOR`          | image background color            | `#000000`         |
| `FG_COLOR`          | image foreground color            | `"#FFFFFF`        |
| `MARKER_COLOR`      | marker color                      | `#FF0000`         |
| `COAST_WIDTH`       | width of the coast line in pixels | `4`               |
| `BORDERS_WIDTH`     | width of the borders in pixels    | `2`               |
| `MARKER_WIDTH`      | width of the markers in piixels   | `15`              |


# Examples
An example with the coordinates of all the capitals
![Entire World](examples/all_countries.png)

An example with some random coordinates
![A part of the world](examples/some_countries.png)
