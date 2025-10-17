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


class WaterQualityPredictor:
    def __init__(self, model_file, scaler_file, use_parallel=True, max_workers=None):
        """
        Initialize water quality predictor with optional parallel processing

        Args:
            model_file: Binary model data
            scaler_file: Binary scaler data
            use_parallel: Whether to use parallel chunk processing (default: True)
            max_workers: Maximum number of threads for parallel processing
        """
        if isinstance(model_file, memoryview):
            model_file = model_file.tobytes()
        if isinstance(scaler_file, memoryview):
            scaler_file = scaler_file.tobytes()

        self.use_parallel = use_parallel

        if use_parallel:
            self.model_data = model_file
            self.scaler_data = scaler_file

            self.thread_local = threading.local()

            self.max_workers = max_workers or min(os.cpu_count() or 4, 6)
            print(f"Parallel processing enabled with {self.max_workers} worker threads")
        else:
            # Load  directly for sequential processing
            print(f"Loading model and scaler from binary data...")
            print(f"Model file size: {len(model_file)} bytes")
            print(f"Scaler file size: {len(scaler_file)} bytes")

            # Load models using BytesIO
            model_buffer = BytesIO(model_file)
            scaler_buffer = BytesIO(scaler_file)

            self.model = joblib.load(model_buffer)
            self.scaler = joblib.load(scaler_buffer)

        self.band_columns = ["B2", "B3", "B4", "B5", "B8", "B11"]
        self.index_columns = [
            "NDCI",
            "NDVI",
            "FAI",
            "MNDWI",
            "B3_B2_ratio",
            "B4_B3_ratio",
            "B5_B4_ratio",
        ]
        self.temporal_columns = ["Month", "Season"]
        self.feature_columns = (
            self.band_columns + self.index_columns + self.temporal_columns
        )

    def _get_thread_models(self):
        """Get thread-local model and scaler instances for parallel processing"""
        if not hasattr(self.thread_local, "model"):
            model_buffer = BytesIO(self.model_data)
            scaler_buffer = BytesIO(self.scaler_data)

            self.thread_local.model = joblib.load(model_buffer)
            self.thread_local.scaler = joblib.load(scaler_buffer)

            thread_id = threading.current_thread().ident
            print(f"Loaded models for thread {thread_id}")

        return self.thread_local.model, self.thread_local.scaler

    def process_chunk(self, chunk_info_or_bands, month=None, season=None):
        """
        Process a chunk of the image - supports both parallel and sequential modes

        Args:
            chunk_info_or_bands: Either chunk info dict (parallel) or bands array (sequential)
            month: Month (for sequential mode)
            season: Season (for sequential mode)

        Returns:
            Chunk result array or tuple with coordinates (for parallel mode)
        """
        if self.use_parallel and isinstance(chunk_info_or_bands, dict):
            # Parallel mode
            return self._process_chunk_parallel(chunk_info_or_bands)
        else:
            # Sequential mode
            return self._process_chunk_sequential(chunk_info_or_bands, month, season)

    def _process_chunk_parallel(
        self, chunk_info: Dict[str, Any]
    ) -> Tuple[int, int, np.ndarray]:
        """Process a single chunk in parallel mode"""
        bands_chunk = chunk_info["data"]
        month = chunk_info["month"]
        season = chunk_info["season"]
        chunk_x = chunk_info["x"]
        chunk_y = chunk_info["y"]

        model, scaler = self._get_thread_models()

        try:
            result = self._calculate_chunk_predictions(
                bands_chunk, month, season, model, scaler
            )
            return chunk_x, chunk_y, result
        except Exception as e:
            print(f"Error processing chunk at position ({chunk_x},{chunk_y}): {str(e)}")
            return (
                chunk_x,
                chunk_y,
                np.full(
                    (bands_chunk.shape[1], bands_chunk.shape[2]),
                    -9999,
                    dtype=np.float32,
                ),
            )

    def _process_chunk_sequential(self, bands_chunk, month, season):
        """Process a single chunk in sequential mode"""
        return self._calculate_chunk_predictions(
            bands_chunk, month, season, self.model, self.scaler
        )

    def _calculate_chunk_predictions(self, bands_chunk, month, season, model, scaler):
        """Core chunk processing logic used by both parallel and sequential modes"""
        b2, b3, b4, b5, b8, b11 = bands_chunk[0:6]

        with np.errstate(divide="ignore", invalid="ignore"):
            mndwi = np.where((b3 + b11) != 0, (b3 - b11) / (b3 + b11), 0)
            ndci = np.where((b5 + b4) != 0, (b5 - b4) / (b5 + b4), 0)
            ndvi = np.where((b8 + b4) != 0, (b8 - b4) / (b8 + b4), 0)

        nir_wl, red_wl, swir_wl = 842, 665, 1610
        fai = b8 - (b4 + (b11 - b4) * (nir_wl - red_wl) / (swir_wl - red_wl))

        with np.errstate(divide="ignore", invalid="ignore"):
            b3_b2_ratio = np.where((b2 != 0) & (b3 != 0), b3 / b2, 0)
            b4_b3_ratio = np.where((b3 != 0) & (b4 != 0), b4 / b3, 0)
            b5_b4_ratio = np.where((b4 != 0) & (b5 != 0), b5 / b4, 0)

        mndwi = np.nan_to_num(mndwi)
        ndci = np.nan_to_num(ndci)
        ndvi = np.nan_to_num(ndvi)
        fai = np.nan_to_num(fai)
        b3_b2_ratio = np.nan_to_num(b3_b2_ratio)
        b4_b3_ratio = np.nan_to_num(b4_b3_ratio)
        b5_b4_ratio = np.nan_to_num(b5_b4_ratio)

        water_mask = mndwi > 0.3

        feature_dict = {
            "B2": b2.ravel(),
            "B3": b3.ravel(),
            "B4": b4.ravel(),
            "B5": b5.ravel(),
            "B8": b8.ravel(),
            "B11": b11.ravel(),
            "NDCI": ndci.ravel(),
            "NDVI": ndvi.ravel(),
            "FAI": fai.ravel(),
            "MNDWI": mndwi.ravel(),
            "B3_B2_ratio": b3_b2_ratio.ravel(),
            "B4_B3_ratio": b4_b3_ratio.ravel(),
            "B5_B4_ratio": b5_b4_ratio.ravel(),
            "Month": np.full_like(b2.ravel(), month),
            "Season": np.full_like(b2.ravel(), season),
        }

        features_df = pd.DataFrame(feature_dict)

        features_df = features_df[self.feature_columns]

        valid_features = features_df[water_mask.ravel()]

        if len(valid_features) > 0:
            scaled_features = scaler.transform(valid_features)

            predictions = model.predict(scaled_features)

            chunk_result = np.full(water_mask.shape, -9999, dtype=np.float32)
            chunk_result[water_mask] = predictions
            return chunk_result
        else:
            return np.full(water_mask.shape, -9999, dtype=np.float32)

    def _prepare_chunks(
        self, src, chunk_size: int, month: int, season: int
    ) -> List[Dict[str, Any]]:
        """Prepare list of chunks for parallel processing"""
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
                    "data": chunk_data,
                    "month": month,
                    "season": season,
                    "x": x,
                    "y": y,
                    "x_end": x_end,
                    "y_end": y_end,
                    "window": window,
                }
                chunks.append(chunk_info)

        return chunks

    def process_image_parallel(self, image_data, output_file, chunk_size: int = 500):
        """Process image using parallel chunk processing"""
        print(f"Starting parallel image processing with {self.max_workers} threads...")

        with rasterio.MemoryFile(image_data) as memfile:
            with memfile.open() as src:
                height = src.height
                width = src.width
                print(f"Image dimensions: {width}x{height}")

                image_date = src.tags().get(
                    "DATE_ACQUIRED", datetime.now().strftime("%Y-%m-%d")
                )
                month = datetime.strptime(image_date, "%Y-%m-%d").month
                season = ((month + 2) // 3) % 4 + 1

                output_data = np.full((height, width), -9999, dtype=np.float32)

                print("Preparing chunks for parallel processing...")
                chunks = self._prepare_chunks(src, chunk_size, month, season)
                total_chunks = len(chunks)
                print(f"Created {total_chunks} chunks for processing")

                completed_chunks = 0
                failed_chunks = 0

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_chunk = {
                        executor.submit(self.process_chunk, chunk): chunk
                        for chunk in chunks
                    }

                    for future in as_completed(future_to_chunk):
                        chunk = future_to_chunk[future]
                        try:
                            chunk_x, chunk_y, chunk_result = future.result()

                            x_end = chunk["x_end"]
                            y_end = chunk["y_end"]
                            output_data[chunk_y:y_end, chunk_x:x_end] = chunk_result

                            completed_chunks += 1

                            if completed_chunks % 10 == 0:
                                progress = (completed_chunks / total_chunks) * 100
                                print(
                                    f"Progress: {completed_chunks}/{total_chunks} chunks ({progress:.1f}%)"
                                )

                        except Exception as e:
                            failed_chunks += 1
                            print(f"Chunk processing failed: {str(e)}")

                print(f"Parallel processing completed!")
                print(
                    f"Successfully processed: {completed_chunks}/{total_chunks} chunks"
                )
                if failed_chunks > 0:
                    print(f"Failed chunks: {failed_chunks}")

                self._save_predictions(src, output_data, output_file)
                return output_file

    def process_image_sequential(self, image_data, output_file):
        """Process image using sequential chunk processing (original method)"""
        print(f"Processing image data sequentially...")

        with rasterio.MemoryFile(image_data) as memfile:
            with memfile.open() as src:
                height = src.height
                width = src.width
                print(f"Image dimensions: {width}x{height}")

                image_date = src.tags().get(
                    "DATE_ACQUIRED", datetime.now().strftime("%Y-%m-%d")
                )
                month = datetime.strptime(image_date, "%Y-%m-%d").month
                season = ((month + 2) // 3) % 4 + 1

                output_data = np.full((height, width), -9999, dtype=np.float32)

                chunk_size = 500
                total_chunks = ((height + chunk_size - 1) // chunk_size) * (
                    (width + chunk_size - 1) // chunk_size
                )
                chunk_count = 0

                for y in range(0, height, chunk_size):
                    y_end = min(y + chunk_size, height)
                    for x in range(0, width, chunk_size):
                        x_end = min(x + chunk_size, width)
                        chunk_count += 1

                        if chunk_count % 10 == 0:  # Progress update every 10 chunks
                            progress = (chunk_count / total_chunks) * 100
                            print(
                                f"Processing chunk {chunk_count}/{total_chunks} ({progress:.1f}%)"
                            )

                        # Read chunk
                        window = rasterio.windows.Window(x, y, x_end - x, y_end - y)
                        chunk_data = src.read(window=window)

                        try:
                            chunk_result = self.process_chunk(chunk_data, month, season)
                            output_data[y:y_end, x:x_end] = chunk_result
                        except Exception as e:
                            print(
                                f"Error processing chunk at position ({x},{y}): {str(e)}"
                            )
                            continue

                # Save predictions
                self._save_predictions(src, output_data, output_file)
                return output_file

    def _save_predictions(self, src, output_data, output_file):
        """Save prediction results to output file"""
        with rasterio.MemoryFile() as memfile:
            kwargs = src.meta.copy()
            kwargs.update(
                {"driver": "GTiff", "count": 1, "dtype": "float32", "nodata": -9999}
            )

            with memfile.open(**kwargs) as dst:
                dst.write(output_data.astype(np.float32), 1)

            output_file.write(memfile.read())

        print(f"Saved prediction to output file")

    def process_image(self, image_data, output_file):
        """
        Main processing method - automatically chooses parallel or sequential processing

        Args:
            image_data: Binary image data
            output_file: Output file object

        Returns:
            Output file with predictions
        """
        if self.use_parallel:
            return self.process_image_parallel(image_data, output_file)
        else:
            return self.process_image_sequential(image_data, output_file)

    def predict_single_pixel(self, feature_vector):
        """
        Predict water quality for a single pixel using the ML model

        Args:
            feature_vector: List of spectral values and indices for one pixel

        Returns:
            Predicted water quality value
        """
        try:
            if (
                len(feature_vector) != 15
            ):  # Expected: B2,B3,B4,B5,B8,B11,NDCI,NDVI,FAI,MNDWI,B3_B2,B4_B3,B5_B4,Month,Season
                print(f"Warning: Expected 15 features, got {len(feature_vector)}")
                feature_vector = (feature_vector + [0] * 15)[:15]

            features = np.array(feature_vector).reshape(1, -1)

            if self.use_parallel:
                model, scaler = self._get_thread_models()
            else:
                model, scaler = self.model, self.scaler

            scaled_features = scaler.transform(features)

            prediction = model.predict(scaled_features)[0]

            return float(prediction)

        except Exception as e:
            print(f"Error in single pixel prediction: {e}")
            return 0.0
