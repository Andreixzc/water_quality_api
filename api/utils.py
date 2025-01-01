import ee
import geemap
import os
from IPython.display import display

def initialize_ee():
    try:
        ee.Initialize()
    except Exception as e:
        ee.Authenticate()
        ee.Initialize()

def generate_intensity_map(coordinates_json, raster_path, min_value, max_value, parameter_name):
    # Initialize Earth Engine
    initialize_ee()
    
    # Convert JSON coordinates to ee.Geometry.Polygon
    aoi = ee.Geometry.Polygon(coordinates_json)
    # Create and setup the map
    Map = geemap.Map()
    Map.centerObject(aoi, zoom=10)
    Map.add_basemap('SATELLITE')

    # Get the water mask from Sentinel-2 data
    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterBounds(aoi) \
        .filterDate('2020-01-01', '2020-04-01') \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .median()

    # Calculate MNDWI for water masking
    MNDWI = sentinel2.normalizedDifference(['B3', 'B11'])
    water_mask = MNDWI.gt(0.3)

    # Add raster layer
    Map.add_raster(
        raster_path,
        palette=[
            '#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff7f00', '#ff0000',
            '#8b0000', '#800080', '#ff00ff', '#8b4513', '#000000'
        ],
        vmin=min_value,
        vmax=max_value,
        nodata=-9999,
        layer_name='Parameter Intensity'
    )

    # Add water mask
    Map.addLayer(
        water_mask, 
        {'min': 0, 'max': 1, 'palette': ['black', 'blue']}, 
        'Water Mask',
        False
    )

    Map.addLayer(
        aoi, 
        {'color': 'white', 'width': 2, 'fillColor': '00000000'}, 
        'AOI Boundary'
    )

    Map.addLayerControl()

    # Add legend
    add_legend(
        Map, 
        f'Predicted {parameter_name}',
        [
            '#0000ff', '#00ffff', '#00ff00', '#ffff00', '#ff7f00', '#ff0000',
            '#8b0000', '#800080', '#ff00ff', '#8b4513', '#000000'
        ],
        min_value,
        max_value
    )
    return Map

def add_legend(map_obj, title, palette, min_value, max_value):
    legend_html = f"""
    <div style='padding: 10px; background-color: white; border-radius: 5px;'>
        <h4>{title}</h4>
        <div style='display: flex; align-items: center;'>
            <span>{min_value:.2f}</span>
            <div style='flex-grow: 1; height: 20px; background: linear-gradient(to right, {", ".join(palette)}); margin: 0 10px;'></div>
            <span>{max_value:.2f}</span>
        </div>
    </div>
    """
    map_obj.add_html(legend_html)