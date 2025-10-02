import joblib
import rasterio
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from typing import List, Tuple, Dict, Any

class ParallelWaterQualityPredictor:
    def __init__(self, model_file, scaler_file, max_workers=None):
        """
        Initialize parallel water quality predictor
        
        Args:
            model_file: Binary model data
            scaler_file: Binary scaler data  
            max_workers: Maximum number of threads (default: CPU count)
        """
        # Convert memoryview to bytes if necessary
        if isinstance(model_file, memoryview):
            model_file = model_file.tobytes()
        if isinstance(scaler_file, memoryview):
            scaler_file = scaler_file.tobytes()

        print(f"Loading model and scaler from binary data...")
        print(f"Model file size: {len(model_file)} bytes")
        print(f"Scaler file size: {len(scaler_file)} bytes")

        # Store binary data for thread-local model loading
        self.model_data = model_file
        self.scaler_data = scaler_file
        
        # Thread-local storage for models
        self.thread_local = threading.local()
        
        # Set max workers (default to CPU count, but limit to reasonable number)
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)
        print(f"Using {self.max_workers} worker threads for parallel processing")
        
        # Match the exact feature groups from training
        self.band_columns = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11']
        self.index_columns = ['NDCI', 'NDVI', 'FAI', 'MNDWI', 
                              'B3_B2_ratio', 'B4_B3_ratio', 'B5_B4_ratio']
        self.temporal_columns = ['Month', 'Season']
        self.feature_columns = self.band_columns + self.index_columns + self.temporal_columns

    def _get_thread_models(self):
        """Get thread-local model and scaler instances"""
        if not hasattr(self.thread_local, 'model'):
            # Load models for this thread
            model_buffer = BytesIO(self.model_data)
            scaler_buffer = BytesIO(self.scaler_data)
            
            self.thread_local.model = joblib.load(model_buffer)
            self.thread_local.scaler = joblib.load(scaler_buffer)
            
            thread_id = threading.current_thread().ident
            print(f"Loaded models for thread {thread_id}")
            
        return self.thread_local.model, self.thread_local.scaler

    def process_chunk(self, chunk_info: Dict[str, Any]) -> Tuple[int, int, np.ndarray]:
        """
        Process a single chunk of the image
        
        Args:
            chunk_info: Dictionary containing chunk data and metadata
            
        Returns:
            Tuple of (chunk_x, chunk_y, result_array)
        """
        bands_chunk = chunk_info['data']
        month = chunk_info['month']
        season = chunk_info['season']
        chunk_x = chunk_info['x']
        chunk_y = chunk_info['y']
        
        # Get thread-local models
        model, scaler = self._get_thread_models()
        
        try:
            # Extract bands
            b2, b3, b4, b5, b8, b11 = bands_chunk[0:6]
            
            # Calculate indices
            with np.errstate(divide='ignore', invalid='ignore'):
                mndwi = np.where((b3 + b11) != 0, (b3 - b11) / (b3 + b11), 0)
                ndci = np.where((b5 + b4) != 0, (b5 - b4) / (b5 + b4), 0)
                ndvi = np.where((b8 + b4) != 0, (b8 - b4) / (b8 + b4), 0)
            
            # Calculate FAI
            nir_wl, red_wl, swir_wl = 842, 665, 1610
            fai = b8 - (b4 + (b11 - b4) * (nir_wl - red_wl) / (swir_wl - red_wl))
            
            # Calculate band ratios
            with np.errstate(divide='ignore', invalid='ignore'):
                b3_b2_ratio = np.where((b2 != 0) & (b3 != 0), b3 / b2, 0)
                b4_b3_ratio = np.where((b3 != 0) & (b4 != 0), b4 / b3, 0)
                b5_b4_ratio = np.where((b4 != 0) & (b5 != 0), b5 / b4, 0)

            # Replace NaN and inf values with 0
            mndwi = np.nan_to_num(mndwi)
            ndci = np.nan_to_num(ndci)
            ndvi = np.nan_to_num(ndvi)
            fai = np.nan_to_num(fai)
            b3_b2_ratio = np.nan_to_num(b3_b2_ratio)
            b4_b3_ratio = np.nan_to_num(b4_b3_ratio)
            b5_b4_ratio = np.nan_to_num(b5_b4_ratio)
            
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
                scaled_features = scaler.transform(valid_features)
                
                # Make predictions
                predictions = model.predict(scaled_features)
                
                # Prepare output
                chunk_result = np.full(water_mask.shape, -9999, dtype=np.float32)
                chunk_result[water_mask] = predictions
                
                return chunk_x, chunk_y, chunk_result
            else:
                return chunk_x, chunk_y, np.full(water_mask.shape, -9999, dtype=np.float32)
                
        except Exception as e:
            print(f"Error processing chunk at position ({chunk_x},{chunk_y}): {str(e)}")
            # Return empty result for failed chunks
            return chunk_x, chunk_y, np.full((bands_chunk.shape[1], bands_chunk.shape[2]), -9999, dtype=np.float32)

    def _prepare_chunks(self, src, chunk_size: int, month: int, season: int) -> List[Dict[str, Any]]:
        """
        Prepare list of chunks for parallel processing
        
        Args:
            src: Rasterio dataset source
            chunk_size: Size of each chunk
            month: Month of the image
            season: Season of the image
            
        Returns:
            List of chunk information dictionaries
        """
        chunks = []
        height = src.height
        width = src.width
        
        for y in range(0, height, chunk_size):
            y_end = min(y + chunk_size, height)
            for x in range(0, width, chunk_size):
                x_end = min(x + chunk_size, width)
                
                # Read chunk data
                window = rasterio.windows.Window(x, y, x_end - x, y_end - y)
                chunk_data = src.read(window=window)
                
                chunk_info = {
                    'data': chunk_data,
                    'month': month,
                    'season': season,
                    'x': x,
                    'y': y,
                    'x_end': x_end,
                    'y_end': y_end,
                    'window': window
                }
                chunks.append(chunk_info)
                
        return chunks

    def process_image_parallel(self, image_data, output_file, chunk_size: int = 500) -> Any:
        """
        Process a satellite image using parallel chunk processing
        
        Args:
            image_data: Binary image data
            output_file: Output file object
            chunk_size: Size of processing chunks
            
        Returns:
            Output file with predictions
        """
        print(f"Starting parallel image processing with {self.max_workers} threads...")
        
        with rasterio.MemoryFile(image_data) as memfile:
            with memfile.open() as src:
                # Get image information
                height = src.height
                width = src.width
                print(f"Image dimensions: {width}x{height}")
                
                # Get date information from metadata if available
                image_date = src.tags().get('DATE_ACQUIRED', datetime.now().strftime('%Y-%m-%d'))
                month = datetime.strptime(image_date, '%Y-%m-%d').month
                season = ((month + 2) // 3) % 4 + 1
                
                # Prepare output array
                output_data = np.full((height, width), -9999, dtype=np.float32)
                
                # Prepare all chunks
                print("Preparing chunks for parallel processing...")
                chunks = self._prepare_chunks(src, chunk_size, month, season)
                total_chunks = len(chunks)
                print(f"Created {total_chunks} chunks for processing")
                
                # Process chunks in parallel
                completed_chunks = 0
                failed_chunks = 0
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all chunk processing tasks
                    future_to_chunk = {
                        executor.submit(self.process_chunk, chunk): chunk 
                        for chunk in chunks
                    }
                    
                    # Process completed chunks as they finish
                    for future in as_completed(future_to_chunk):
                        chunk = future_to_chunk[future]
                        try:
                            chunk_x, chunk_y, chunk_result = future.result()
                            
                            # Place result in output array
                            x_end = chunk['x_end']
                            y_end = chunk['y_end']
                            output_data[chunk_y:y_end, chunk_x:x_end] = chunk_result
                            
                            completed_chunks += 1
                            
                            if completed_chunks % 10 == 0:  # Progress update every 10 chunks
                                progress = (completed_chunks / total_chunks) * 100
                                print(f"Progress: {completed_chunks}/{total_chunks} chunks ({progress:.1f}%)")
                                
                        except Exception as e:
                            failed_chunks += 1
                            print(f"Chunk processing failed: {str(e)}")
                
                print(f"Parallel processing completed!")
                print(f"Successfully processed: {completed_chunks}/{total_chunks} chunks")
                if failed_chunks > 0:
                    print(f"Failed chunks: {failed_chunks}")
                
                # Save predictions
                with rasterio.MemoryFile() as memfile:
                    kwargs = src.meta.copy()
                    kwargs.update({
                        'driver': 'GTiff',
                        'count': 1,
                        'dtype': 'float32',
                        'nodata': -9999
                    })

                    with memfile.open(**kwargs) as dst:
                        dst.write(output_data.astype(np.float32), 1)

                    output_file.write(memfile.read())
                
                print(f"Saved prediction to output file")
                return output_file

    def process_image(self, image_data, output_file):
        """
        Main processing method - uses parallel processing by default
        
        Args:
            image_data: Binary image data
            output_file: Output file object
            
        Returns:
            Output file with predictions
        """
        return self.process_image_parallel(image_data, output_file)

# Backward compatibility wrapper
class WaterQualityPredictor(ParallelWaterQualityPredictor):
    """
    Backward-compatible wrapper that maintains the original interface
    but uses parallel processing under the hood
    """
    def __init__(self, model_file, scaler_file):
        super().__init__(model_file, scaler_file, max_workers=4)  # Conservative default
