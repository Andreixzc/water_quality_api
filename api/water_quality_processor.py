import ee
import geemap
import joblib
import numpy as np
import os
from datetime import datetime
import threading
from threading import Lock
import rasterio
from rasterio.merge import merge

class WaterQualityProcessor:
    def __init__(self, model_path, scaler_path):
        """Initialize the processor with model and scaler paths"""
        try:
            ee.Initialize()
        except Exception as e:
            ee.Authenticate()
            ee.Initialize()
            
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        self.feature_names = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'NDCI', 'NDVI', 'FAI', 
                            'B3_B2_ratio', 'B4_B3_ratio', 'B5_B4_ratio', 'Month', 'Season']

    def process_tile(self, tile_geometry, date):
        """Process a single tile of the area of interest for a specific date"""
        sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(tile_geometry) \
            .filterDate(date, ee.Date(date).advance(1, 'day')) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        if sentinel2.size().getInfo() == 0:
            return None

        image = sentinel2.first().clip(tile_geometry)
        
        bands = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11']
        image = image.select(bands)
        
        MNDWI = image.normalizedDifference(['B3', 'B11']).rename('MNDWI')
        water_mask = MNDWI.gt(0.3)
        
        NDCI = image.normalizedDifference(['B5', 'B4']).rename('NDCI')
        NDVI = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        FAI = image.expression(
            'NIR - (RED + (SWIR - RED) * (NIR_wl - RED_wl) / (SWIR_wl - RED_wl))',
            {
                'NIR': image.select('B8'),
                'RED': image.select('B4'),
                'SWIR': image.select('B11'),
                'NIR_wl': 842,
                'RED_wl': 665,
                'SWIR_wl': 1610
            }
        ).rename('FAI')
        
        B3_B2_ratio = image.select('B3').divide(image.select('B2')).rename('B3_B2_ratio')
        B4_B3_ratio = image.select('B4').divide(image.select('B3')).rename('B4_B3_ratio')
        B5_B4_ratio = image.select('B5').divide(image.select('B4')).rename('B5_B4_ratio')
        
        image_date = ee.Date(image.get('system:time_start'))
        month = ee.Image.constant(image_date.get('month')).rename('Month')
        season = ee.Image.constant(image_date.get('month').add(2).divide(3).floor().add(1)).rename('Season')
        
        image_with_indices = image.addBands([NDCI, NDVI, FAI, B3_B2_ratio, B4_B3_ratio, 
                                           B5_B4_ratio, month, season])
        
        scaled_bands = []
        for i, name in enumerate(self.feature_names):
            scaled_band = image_with_indices.select(name) \
                .subtract(ee.Number(self.scaler.mean_[i])) \
                .divide(ee.Number(self.scaler.scale_[i])) \
                .rename(f'scaled_{name}')
            scaled_bands.append(scaled_band)
        
        scaled_image = ee.Image.cat(scaled_bands)
        
        weighted_bands = []
        for i, (name, importance) in enumerate(zip(self.feature_names, self.model.feature_importances_)):
            weighted_band = scaled_image.select(f'scaled_{name}').multiply(ee.Number(importance))
            weighted_bands.append(weighted_band)
        
        predicted_image = ee.Image.cat(weighted_bands).reduce(ee.Reducer.sum()).rename('parameter_pred')
        
        final_image = predicted_image.where(water_mask.Not(), ee.Image.constant(-9999))
        
        return final_image

    def process_reservoir(self, reservoir_name, aoi_coords, start_date, end_date, parameter_name, output_dir='outputs'):
        """Process a reservoir for all available dates in the given range"""
        print("Original AOI coordinates:", aoi_coords)
        
        # Convert the coordinates to an Earth Engine Geometry
        aoi = ee.Geometry.Polygon([aoi_coords])
        print("Converted AOI:", aoi.getInfo())

        os.makedirs(output_dir, exist_ok=True)

        date_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(aoi) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

        dates = date_collection.aggregate_array('system:time_start').getInfo()
        dates = [datetime.fromtimestamp(d/1000).strftime('%Y-%m-%d') for d in dates]

        results = []
        for date in dates:
            try:
                output_tiff, stats_path = self._process_single_date(reservoir_name, aoi, date, parameter_name, output_dir)
                results.append((date, output_tiff, stats_path))
            except Exception as e:
                print(f"Error processing date {date}: {str(e)}")

        return results

    def _process_single_date(self, reservoir_name, aoi, date, parameter_name, output_dir):
        """Process a single date for the reservoir"""
        aoi_bounds = aoi.bounds().getInfo()['coordinates'][0]
        xmin, ymin = aoi_bounds[0][0], aoi_bounds[0][1]
        xmax, ymax = aoi_bounds[2][0], aoi_bounds[2][1]
        
        n_tiles = 2
        x_step = (xmax - xmin) / n_tiles
        y_step = (ymax - ymin) / n_tiles
        
        lock = Lock()
        tile_results = []
        
        def process_and_save_tile(i, j):
            x0, x1 = xmin + i * x_step, xmin + (i + 1) * x_step
            y0, y1 = ymin + j * y_step, ymin + (j + 1) * y_step
            tile_geometry = ee.Geometry.Rectangle([x0, y0, x1, y1])
            
            try:
                tile_result = self.process_tile(tile_geometry, date)
                if tile_result is not None:
                    out_file = os.path.join(output_dir, f'Tile_{date}_{i+1}_{j+1}.tif')
                    with lock:
                        geemap.ee_export_image(
                            tile_result,
                            filename=out_file,
                            scale=30,
                            region=tile_geometry
                        )
                        tile_results.append(out_file)
            except Exception as e:
                print(f"Error processing tile {i+1}_{j+1} for date {date}: {str(e)}")
        
        threads = []
        for i in range(n_tiles):
            for j in range(n_tiles):
                t = threading.Thread(target=process_and_save_tile, args=(i, j))
                threads.append(t)
                t.start()
        
        for t in threads:
            t.join()
        
        if not tile_results:
            raise ValueError(f"No valid data for date {date}")
        
        output_filename = f"{reservoir_name}_{date}_{parameter_name}.tif"
        output_path = os.path.join(output_dir, output_filename)
        
        self.merge_tiff_files(output_dir, f'Tile_{date}', output_path)
        
        stats_filename = f"{reservoir_name}_{date}_{parameter_name}_stats.txt"
        stats_path = os.path.join(output_dir, stats_filename)
        
        with rasterio.open(output_path) as src:
            data = src.read(1)
            valid_data = data[data != -9999]
            min_value = np.min(valid_data)
            max_value = np.max(valid_data)
        
        with open(stats_path, 'w') as f:
            f.write(f"Reservoir: {reservoir_name}\n")
            f.write(f"Parameter: {parameter_name}\n")
            f.write(f"Date: {date}\n")
            f.write(f"Minimum value: {min_value}\n")
            f.write(f"Maximum value: {max_value}\n")
        
        return output_path, stats_path

    def merge_tiff_files(self, directory, pattern, output_file):
        """Merge multiple TIFF files into a single file"""
        tiff_files = [os.path.join(directory, f) for f in os.listdir(directory) 
                    if f.startswith(pattern) and f.endswith('.tif')]
        
        if not tiff_files:
            raise ValueError("No TIFF files found to merge")
        
        src_files_to_mosaic = []
        try:
            for tiff in tiff_files:
                src = rasterio.open(tiff)
                src_files_to_mosaic.append(src)
            
            mosaic, out_trans = merge(src_files_to_mosaic)
            
            out_meta = src_files_to_mosaic[0].meta.copy()
            out_meta.update({
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans,
                "nodata": -9999
            })
            
            with rasterio.open(output_file, "w", **out_meta) as dest:
                dest.write(mosaic)
            
            return tiff_files
        finally:
            for src in src_files_to_mosaic:
                src.close()
            
            # Cleanup temporary files
            for file in tiff_files:
                try:
                    os.remove(file)
                except Exception as e:
                    print(f"Error deleting {file}: {str(e)}")