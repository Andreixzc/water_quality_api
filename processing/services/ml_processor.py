import joblib
import rasterio
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from io import BytesIO

class WaterQualityPredictor:
    def __init__(self, model_file, scaler_file):
        # Convert memoryview to bytes if necessary
        if isinstance(model_file, memoryview):
            model_file = model_file.tobytes()
        if isinstance(scaler_file, memoryview):
            scaler_file = scaler_file.tobytes()

        print(f"Loading model and scaler from binary data...")
        print(f"Model file size: {len(model_file)} bytes")
        print(f"Scaler file size: {len(scaler_file)} bytes")

        # Load models using BytesIO
        model_buffer = BytesIO(model_file)
        scaler_buffer = BytesIO(scaler_file)
        
        self.model = joblib.load(model_buffer)
        self.scaler = joblib.load(scaler_buffer)
        
        # Match the exact feature groups from training
        self.band_columns = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11']
        self.index_columns = ['NDCI', 'NDVI', 'FAI', 'MNDWI', 
                            'B3_B2_ratio', 'B4_B3_ratio', 'B5_B4_ratio']
        self.temporal_columns = ['Month', 'Season']
        self.feature_columns = self.band_columns + self.index_columns + self.temporal_columns

    def process_chunk(self, bands_chunk, month, season):
        """Process a chunk of the image"""
        # Extract bands
        b2, b3, b4, b5, b8, b11 = bands_chunk[0:6]
        
        # Calculate indices
        # MNDWI (included in training)
        mndwi = np.where((b3 + b11) != 0, (b3 - b11) / (b3 + b11), 0)
        
        # Other indices
        ndci = np.where((b5 + b4) != 0, (b5 - b4) / (b5 + b4), 0)
        ndvi = np.where((b8 + b4) != 0, (b8 - b4) / (b8 + b4), 0)
        
        # Calculate FAI
        nir_wl, red_wl, swir_wl = 842, 665, 1610
        fai = b8 - (b4 + (b11 - b4) * (nir_wl - red_wl) / (swir_wl - red_wl))
        
        # Calculate band ratios
        b3_b2_ratio = np.where(b2 != 0, b3 / b2, 0)
        b4_b3_ratio = np.where(b3 != 0, b4 / b3, 0)
        b5_b4_ratio = np.where(b4 != 0, b5 / b4, 0)
        
        # Create water mask
        water_mask = mndwi > 0.3
        
        # Create a dictionary to store features
        feature_dict = {
            'B2': b2.ravel(),
            'B3': b3.ravel(),
            'B4': b4.ravel(),
            'B5': b5.ravel(),
            'B8': b8.ravel(),
            'B11': b11.ravel(),
            'NDCI': ndci.ravel(),
            'NDVI': ndvi.ravel(),
            'FAI': fai.ravel(),
            'MNDWI': mndwi.ravel(),
            'B3_B2_ratio': b3_b2_ratio.ravel(),
            'B4_B3_ratio': b4_b3_ratio.ravel(),
            'B5_B4_ratio': b5_b4_ratio.ravel(),
            'Month': np.full_like(b2.ravel(), month),
            'Season': np.full_like(b2.ravel(), season)
        }
        
        # Create DataFrame with named features
        features_df = pd.DataFrame(feature_dict)
        
        # Ensure columns are in the correct order
        features_df = features_df[self.feature_columns]
        
        # Apply water mask
        valid_features = features_df[water_mask.ravel()]
        
        if len(valid_features) > 0:
            # Scale features
            scaled_features = self.scaler.transform(valid_features)
            
            # Make predictions
            predictions = self.model.predict(scaled_features)
            
            # Prepare output
            chunk_result = np.full(water_mask.shape, -9999, dtype=np.float32)
            chunk_result[water_mask] = predictions
            return chunk_result
        else:
            return np.full(water_mask.shape, -9999, dtype=np.float32)

    def process_image(self, image_path, output_dir, chunk_size=500):
        """Process a single satellite image in chunks"""
        print(f"Processing {image_path}...")
        
        with rasterio.open(image_path) as src:
            # Get image information
            height = src.height
            width = src.width
            print(f"Image dimensions: {width}x{height}")
            
            # Get date information from the filename
            date_parts = Path(image_path).stem.split('_')[1:]  # Assuming format like 'analysis_YYYY_MM_DD'
            date_str = '_'.join(date_parts)
            try:
                image_date = datetime.strptime(date_str, '%Y_%m_%d')
                month = image_date.month
                season = ((month + 2) // 3) % 4 + 1
            except ValueError as e:
                print(f"Error parsing date from filename: {e}")
                # Use current date as fallback
                now = datetime.now()
                month = now.month
                season = ((month + 2) // 3) % 4 + 1
            
            # Prepare output array
            output_data = np.full((height, width), -9999, dtype=np.float32)
            
            # Process image in chunks
            total_chunks = ((height + chunk_size - 1) // chunk_size) * ((width + chunk_size - 1) // chunk_size)
            chunk_count = 0
            
            for y in range(0, height, chunk_size):
                y_end = min(y + chunk_size, height)
                for x in range(0, width, chunk_size):
                    x_end = min(x + chunk_size, width)
                    chunk_count += 1
                    
                    print(f"Processing chunk {chunk_count}/{total_chunks} ({(chunk_count/total_chunks)*100:.1f}%)")
                    
                    # Read chunk
                    window = rasterio.windows.Window(x, y, x_end - x, y_end - y)
                    chunk_data = src.read(window=window)
                    
                    try:
                        chunk_result = self.process_chunk(chunk_data, month, season)
                        output_data[y:y_end, x:x_end] = chunk_result
                    except Exception as e:
                        print(f"Error processing chunk at position ({x},{y}): {str(e)}")
                        continue
            
            # Save predictions
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"prediction_{date_str}.tif")
            
            # Copy metadata from input
            output_meta = src.meta.copy()
            output_meta.update({
                'count': 1,
                'dtype': 'float32',
                'nodata': -9999
            })
            
            with rasterio.open(output_path, 'w', **output_meta) as dst:
                dst.write(output_data.astype(np.float32), 1)
            
            print(f"Saved prediction to {output_path}")
            return output_path