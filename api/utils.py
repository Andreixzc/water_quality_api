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

def generate_intensity_map(coordinates_json, raster_path, min_value, max_value, parameter_name):
    try:
        # Initialize Earth Engine
        initialize_ee()
        
        # Convert JSON coordinates to ee.Geometry.Polygon
        aoi = ee.Geometry.Polygon(coordinates_json)
        
        # Create and setup the map
        center = aoi.centroid().getInfo()['coordinates']
        Map = folium.Map(
            location=[center[1], center[0]], 
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

        # Read and process the GeoTIFF
        with rasterio.open(raster_path) as src:
            raster_data = src.read(1)
            raster_bounds = src.bounds

        # Create a masked array for NoData values
        masked_data = np.ma.masked_equal(raster_data, -9999)
        
        # Calculate actual min and max from valid data
        valid_data = masked_data[~masked_data.mask]
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
        normalized_data = np.ma.zeros_like(masked_data)
        normalized_data[~masked_data.mask] = (
            (masked_data[~masked_data.mask] - data_min) / (data_max - data_min)
        )
        normalized_data.mask = masked_data.mask
        
        # Apply the colormap
        colored_data = np.zeros((*masked_data.shape, 4))  # RGBA array
        colored_data[~masked_data.mask] = custom_cmap(normalized_data[~masked_data.mask])
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
            bounds=[[raster_bounds.bottom, raster_bounds.left], 
                    [raster_bounds.top, raster_bounds.right]],
            name=f'{parameter_name} Intensity',
            opacity=0.7,
            overlay=True
        ).add_to(Map)

        # Get coordinates for map bounds
        coords = aoi.getInfo()['coordinates'][0]

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

        # Fit map to AOI bounds
        Map.fit_bounds([[coord[1], coord[0]] for coord in coords])

        # Return the HTML representation of the map
        return Map._repr_html_()

    except Exception as e:
        print(f"Error in generate_intensity_map: {str(e)}")
        raise e