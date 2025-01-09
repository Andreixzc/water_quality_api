import ee
import folium
import rasterio
import numpy as np
from folium.plugins import Fullscreen, MeasureControl
from branca.colormap import LinearColormap
import base64
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def initialize_ee():
    try:
        ee.Initialize()
    except Exception as e:
        ee.Authenticate()
        ee.Initialize()

import pyproj
from rasterio.warp import transform_bounds

import pyproj
from rasterio.warp import transform_bounds

def generate_intensity_map(raster_path, parameter_name):
    try:
        # Initialize Earth Engine
        initialize_ee()
        
        # Read and process the GeoTIFF
        with rasterio.open(raster_path) as src:
            raster_data = src.read(1)
            raster_bounds = src.bounds
            raster_crs = src.crs

        # Convert raster bounds to lat/lon
        wgs84 = pyproj.CRS('EPSG:4326')
        transformer = pyproj.Transformer.from_crs(raster_crs, wgs84, always_xy=True)
        lon_min, lat_min, lon_max, lat_max = transform_bounds(raster_crs, wgs84, *raster_bounds)

        # Create and setup the map
        center_lat = (lat_min + lat_max) / 2
        center_lon = (lon_min + lon_max) / 2
        Map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            control_scale=True
        )
        
        # Add satellite basemap
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite',
            name='Satellite'
        ).add_to(Map)

        # Define color palette
        palette = [
            '#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff7f00', '#ff0000',
            '#8b0000', '#800080', '#ff00ff', '#8b4513', '#000000'
        ]

        # Create a masked array for NoData values
        masked_data = np.ma.masked_equal(raster_data, -9999)
        
        # Calculate actual min and max from valid data
        valid_data = masked_data.compressed()
        data_min = np.min(valid_data)
        data_max = np.max(valid_data)
        
        print("Data distribution:")
        print("Min:", data_min)
        print("Max:", data_max)
        print("Percentiles:", np.percentile(valid_data, [0, 25, 50, 75, 100]))
        
        # Create a custom colormap from the palette
        custom_colors = [mcolors.hex2color(color) for color in palette]
        custom_cmap = mcolors.LinearSegmentedColormap.from_list('custom', custom_colors, N=256)
        
        # Normalize the data using actual min/max
        norm = mcolors.Normalize(vmin=data_min, vmax=data_max)
        
        # Apply the colormap
        colored_data = custom_cmap(norm(masked_data.filled(np.nan)))
        colored_data[masked_data.mask] = [0, 0, 0, 0]  # Transparent for masked values
        
        # Convert to image
        img = Image.fromarray((colored_data * 255).astype(np.uint8))

        # Save image to BytesIO object
        img_io = BytesIO()
        img.save(img_io, format='PNG')

        # Encode image to base64
        img_base64 = base64.b64encode(img_io.getvalue()).decode()

        # Add GeoTIFF overlay
        folium.raster_layers.ImageOverlay(
            image=f'data:image/png;base64,{img_base64}',
            bounds=[[lat_min, lon_min], [lat_max, lon_max]],
            name=f'{parameter_name} Intensity',
            opacity=0.7,
            overlay=True
        ).add_to(Map)

        # Add color scale using branca.colormap
        colormap = LinearColormap(
            colors=palette,
            vmin=data_min,
            vmax=data_max,
            caption=f'Predicted {parameter_name}'
        )
        colormap.add_to(Map)

        # Add layer control
        folium.LayerControl().add_to(Map)

        # Add fullscreen option
        Fullscreen().add_to(Map)

        # Add measure tool
        MeasureControl(
            position='topright',
            primary_length_unit='kilometers',
            secondary_length_unit='miles',
            primary_area_unit='square kilometers',
            secondary_area_unit='acres'
        ).add_to(Map)

        # Fit map to raster bounds
        Map.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])

        # Return the HTML representation of the map
        return Map._repr_html_()

    except Exception as e:
        print(f"Error in generate_intensity_map: {str(e)}")
        raise e
    





if __name__ == "__main__":
    # Define test parameters
    raster_path = "Cacu_2020-02-01_Turbidity.tif"
    parameter_name = "Turbidity"

    try:
        # Generate the map
        map_html = generate_intensity_map(raster_path, parameter_name)

        # Save the HTML to a file
        with open("test_intensity_map.html", "w") as f:
            f.write(map_html)

        print("Map generated successfully. Open 'test_intensity_map.html' in a web browser to view.")
    except Exception as e:
        print(f"Error generating map: {str(e)}")

    # Print raster information
    try:
        with rasterio.open(raster_path) as src:
            print(f"Raster shape: {src.shape}")
            print(f"Raster bounds: {src.bounds}")
            print(f"Raster CRS: {src.crs}")
            data = src.read(1)
            valid_data = data[data != -9999]
            print(f"Data min: {np.min(valid_data)}")
            print(f"Data max: {np.max(valid_data)}")
            print(f"Data mean: {np.mean(valid_data)}")
            print(f"Data median: {np.median(valid_data)}")
    except Exception as e:
        print(f"Error reading raster: {str(e)}")