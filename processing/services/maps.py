# processing/services/maps.py

import folium
import rasterio
import numpy as np
from folium.plugins import Fullscreen, MeasureControl
from branca.colormap import LinearColormap
from rasterio.warp import transform_bounds
import matplotlib
# Set the backend to 'Agg' before importing pyplot
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import timedelta
import matplotlib.colors as mcolors
from PIL import Image
import ee

# Initialize the Earth Engine API
ee.Initialize()

class MapGenerator:
   def __init__(self, raster_path, image_date):  # Add image_date parameter
       self.raster_path = raster_path
       self.image_date = image_date  # Store the date for satellite imagery
       
   def mosaicBy(self, imageCollection):
       """
       Create a daily mosaic from an image collection, considering spacecraft and orbit
       """
       def map_dates(image):
           return image.set('date', image.date().format('YYYY-MM-dd'))

       def create_mosaic(date_orbit_spacecraft):
           parts = ee.String(date_orbit_spacecraft).split(" ")
           date1 = ee.Date(parts.get(0))
           orbit = ee.Number.parse(parts.get(1))
           spName = parts.get(2)

           # Filter by date, spacecraft, and orbit before mosaicking
           mosaic = (imageCollection
                   .filterDate(date1, date1.advance(1, 'day'))
                   .filterMetadata('SPACECRAFT_NAME', 'equals', spName)
                   .filterMetadata('SENSING_ORBIT_NUMBER', 'equals', orbit)
                   .mosaic())

           return mosaic.set({
               'system:time_start': date1.millis(),
               'system:date': date1.format('YYYY-MM-dd'),
               'system:id': date_orbit_spacecraft
           })

       # Get lists of unique combinations
       imgList = imageCollection.map(map_dates).toList(imageCollection.size())
       
       # Extract dates, orbits, and spacecraft names
       all_dates = imgList.map(lambda img: ee.Image(img).date().format('YYYY-MM-dd'))
       all_orbits = imgList.map(lambda img: ee.Image(img).get('SENSING_ORBIT_NUMBER'))
       all_spacecraft = imgList.map(lambda img: ee.Image(img).get('SPACECRAFT_NAME'))

       # Combine into unique strings (date_orbit_spacecraft)
       combined = all_dates.zip(all_orbits).zip(all_spacecraft)
       combined = combined.map(lambda x: ee.List(x).flatten().join(' '))
       unique_combinations = combined.distinct()

       # Create mosaics for each unique combination
       mosaic_collection = ee.ImageCollection(unique_combinations.map(create_mosaic))
       
       return mosaic_collection

   def create_interactive_map(self):
       """Creates an interactive Folium map and returns HTML as string"""
       with rasterio.open(self.raster_path) as src:
           data = src.read(1)
           valid_data = data[data != -9999]
           bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
           
           center_lat = (bounds[1] + bounds[3]) / 2
           center_lon = (bounds[0] + bounds[2]) / 2
           m = folium.Map(location=[center_lat, center_lon], 
                         zoom_start=12,
                         control_scale=True)

           # Add base maps
           folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
           folium.TileLayer('cartodbpositron', name='CartoDB Positron').add_to(m)
           folium.TileLayer('cartodbdark_matter', name='CartoDB Dark Matter').add_to(m)

           # Try to add Sentinel-2 imagery
           try:
               start_date = self.image_date.strftime('%Y-%m-%d')
               end_date = (self.image_date + timedelta(days=1)).strftime('%Y-%m-%d')
               
               # Create geometry from bounds
               aoi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])
               
               # Get initial collection
               s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                              .filterBounds(aoi)
                              .filterDate(start_date, end_date))
               
               # Create daily mosaic considering spacecraft and orbit
               daily_mosaic = self.mosaicBy(s2_collection)
               s2_image = daily_mosaic.first()
               
               if s2_image:
                   viz_params = {
                       'bands': ['B4', 'B3', 'B2'],
                       'min': 0,
                       'max': 3000,
                       'gamma': 1.4
                   }
                   map_id_dict = s2_image.getMapId(viz_params)
                   
                   folium.TileLayer(
                       tiles=map_id_dict['tile_fetcher'].url_format,
                       attr='Sentinel-2 Imagery',
                       name=f'Sentinel-2 Mosaic ({start_date})',
                       overlay=True,
                       opacity=0.7
                   ).add_to(m)
                   print(f"Successfully added Sentinel-2 mosaic for {start_date}")
               else:
                   print(f"No Sentinel-2 imagery available for {start_date}")

           except Exception as e:
               print(f"Error adding satellite imagery: {str(e)}")

           # Add the analysis layer
           palette = [
               '#f7fbff',  # Lightest blue
               '#deebf7',
               '#4292c6',
               '#2171b5',
               '#084594'   # Darkest blue
           ]

           norm = mcolors.Normalize(vmin=np.min(valid_data), vmax=np.max(valid_data))
           custom_colors = [mcolors.hex2color(color) for color in palette]
           custom_cmap = mcolors.LinearSegmentedColormap.from_list("custom", custom_colors, N=256)
           
           masked_data = np.ma.masked_equal(data, -9999)
           colored_data = custom_cmap(norm(masked_data.filled(np.nan)))
           colored_data[masked_data.mask] = [0, 0, 0, 0]
           
           img = Image.fromarray((colored_data * 255).astype(np.uint8))
           buffered = BytesIO()
           img.save(buffered, format="PNG")
           img_str = base64.b64encode(buffered.getvalue()).decode()
           
           folium.raster_layers.ImageOverlay(
               image=f"data:image/png;base64,{img_str}",
               bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
               opacity=0.7,
               name='Parameter Map'
           ).add_to(m)
           
           colormap = LinearColormap(
               colors=palette,
               vmin=float(np.min(valid_data)),
               vmax=float(np.max(valid_data)),
               caption='Parameter Concentration'
           )
           colormap.add_to(m)
           
           folium.LayerControl().add_to(m)
           Fullscreen().add_to(m)
           MeasureControl(
               position="topright",
               primary_length_unit="kilometers",
               primary_area_unit="square kilometers"
           ).add_to(m)
           
           return m._repr_html_()

   def create_static_map(self):
       """Creates a static matplotlib map and returns PNG as bytes"""
       with rasterio.open(self.raster_path) as src:
           data = src.read(1)
           masked_data = np.ma.masked_equal(data, -9999)
           
           # Create figure with 'Agg' backend
           plt.figure(figsize=(12, 8))
           im = plt.imshow(masked_data, cmap='YlOrRd')
           plt.colorbar(im, label='Parameter Concentration')
           
           # Save to BytesIO instead of file
           buffer = BytesIO()
           plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
           plt.close()  # Make sure to close the figure
           
           return buffer.getvalue()