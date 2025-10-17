import joblib
import rasterio
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any


# ============================================================================
# GLOBAL WORKER FUNCTION (Required for multiprocessing)
# ============================================================================
def _global_worker_process_chunk(
    chunk_info: Dict[str, Any],
) -> Tuple[int, int, np.ndarray]:
    """
    Global worker function for multiprocessing.
    Must be at module level for pickle serialization.

    This function does what process_chunk() used to do, but at module level.
    """
    bands_chunk = chunk_info["data"]
    month = chunk_info["month"]
    season = chunk_info["season"]
    chunk_x = chunk_info["x"]
    chunk_y = chunk_info["y"]
    model_data = chunk_info["model_data"]
    scaler_data = chunk_info["scaler_data"]
    feature_columns = chunk_info["feature_columns"]

    try:
        # Load models from binary data (each process loads its own copy)
        model_buffer = BytesIO(model_data)
        scaler_buffer = BytesIO(scaler_data)
        model = joblib.load(model_buffer)
        scaler = joblib.load(scaler_buffer)

        # Extract bands
        b2, b3, b4, b5, b8, b11 = bands_chunk[0:6]

        # Calculate spectral indices
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

        # Clean up NaN values
        mndwi = np.nan_to_num(mndwi)
        ndci = np.nan_to_num(ndci)
        ndvi = np.nan_to_num(ndvi)
        fai = np.nan_to_num(fai)
        b3_b2_ratio = np.nan_to_num(b3_b2_ratio)
        b4_b3_ratio = np.nan_to_num(b4_b3_ratio)
        b5_b4_ratio = np.nan_to_num(b5_b4_ratio)

        # Water mask
        water_mask = mndwi > 0.3

        # Prepare features
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
        features_df = features_df[feature_columns]
        valid_features = features_df[water_mask.ravel()]

        if len(valid_features) > 0:
            scaled_features = scaler.transform(valid_features)
            predictions = model.predict(scaled_features)

            chunk_result = np.full(water_mask.shape, -9999, dtype=np.float32)
            chunk_result[water_mask] = predictions

            return chunk_x, chunk_y, chunk_result
        else:
            return chunk_x, chunk_y, np.full(water_mask.shape, -9999, dtype=np.float32)

    except Exception as e:
        print(f"Error processing chunk at position ({chunk_x},{chunk_y}): {str(e)}")
        return (
            chunk_x,
            chunk_y,
            np.full(
                (bands_chunk.shape[1], bands_chunk.shape[2]), -9999, dtype=np.float32
            ),
        )


# ============================================================================
# MAIN CLASS (Same name and structure as original)
# ============================================================================
class ParallelWaterQualityPredictor:
    """
    Water quality predictor with parallel processing support.

    This version uses ProcessPoolExecutor instead of ThreadPoolExecutor
    for true parallel CPU processing, bypassing Python's GIL.

    The public API remains 100% identical to the original version.
    """

    def __init__(self, model_file, scaler_file, max_workers=None):
        """
        Initialize predictor with model and scaler.

        Args:
            model_file: Binary model data or path
            scaler_file: Binary scaler data or path
            max_workers: Number of parallel workers (default: min(CPU count, 8))
        """
        if isinstance(model_file, memoryview):
            model_file = model_file.tobytes()
        if isinstance(scaler_file, memoryview):
            scaler_file = scaler_file.tobytes()

        print(f"Loading model and scaler from binary data...")
        print(f"Model file size: {len(model_file)} bytes")
        print(f"Scaler file size: {len(scaler_file)} bytes")

        # Store model and scaler as binary data
        self.model_data = model_file
        self.scaler_data = scaler_file

        # Determine number of workers
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)
        print(f"Using {self.max_workers} worker processes for parallel processing")

        # Feature column definitions (same as original)
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

    def process_chunk(self, chunk_info: Dict[str, Any]) -> Tuple[int, int, np.ndarray]:
        """
        Process a single chunk of image data.

        NOTE: With multiprocessing, this method delegates to the global worker function.
        Kept for API compatibility.

        Args:
            chunk_info: Dictionary containing chunk data and metadata

        Returns:
            Tuple of (x_position, y_position, prediction_array)
        """
        # Delegate to global worker function
        return _global_worker_process_chunk(chunk_info)

    def _prepare_chunks(
        self, src, chunk_size: int, month: int, season: int
    ) -> List[Dict[str, Any]]:
        """
        Prepare image chunks for parallel processing.

        Args:
            src: Rasterio dataset source
            chunk_size: Size of each chunk in pixels
            month: Month number (1-12)
            season: Season number (1-4)

        Returns:
            List of chunk dictionaries ready for processing
        """
        chunks = []
        height = src.height
        width = src.width

        for y in range(0, height, chunk_size):
            y_end = min(y + chunk_size, height)
            for x in range(0, width, chunk_size):
                x_end = min(x + chunk_size, width)

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
                    # Pass model data to worker (loaded by each process)
                    "model_data": self.model_data,
                    "scaler_data": self.scaler_data,
                    "feature_columns": self.feature_columns,
                }
                chunks.append(chunk_info)

        return chunks

    def process_image_parallel(
        self, image_data, output_file, chunk_size: int = 500
    ) -> Any:
        """
        Process an entire image using parallel processing.

        Args:
            image_data: Binary image data (GeoTIFF format)
            output_file: Output file object to write results
            chunk_size: Size of processing chunks in pixels (default: 500)

        Returns:
            Output file object with prediction results
        """
        print(
            f"Starting parallel image processing with {self.max_workers} processes..."
        )

        with rasterio.MemoryFile(image_data) as memfile:
            with memfile.open() as src:
                height = src.height
                width = src.width
                print(f"Image dimensions: {width}x{height}")

                # Extract temporal information
                image_date = src.tags().get(
                    "DATE_ACQUIRED", datetime.now().strftime("%Y-%m-%d")
                )
                month = datetime.strptime(image_date, "%Y-%m-%d").month
                season = ((month + 2) // 3) % 4 + 1

                # Initialize output array
                output_data = np.full((height, width), -9999, dtype=np.float32)

                # Prepare chunks
                print("Preparing chunks for parallel processing...")
                chunks = self._prepare_chunks(src, chunk_size, month, season)
                total_chunks = len(chunks)
                print(f"Created {total_chunks} chunks for processing")

                completed_chunks = 0
                failed_chunks = 0

                # Process chunks in parallel using ProcessPoolExecutor
                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all chunks to process pool
                    future_to_chunk = {
                        executor.submit(_global_worker_process_chunk, chunk): chunk
                        for chunk in chunks
                    }

                    # Collect results as they complete
                    for future in as_completed(future_to_chunk):
                        chunk = future_to_chunk[future]
                        try:
                            chunk_x, chunk_y, chunk_result = future.result()

                            # Write chunk result to output array
                            x_end = chunk["x_end"]
                            y_end = chunk["y_end"]
                            output_data[chunk_y:y_end, chunk_x:x_end] = chunk_result

                            completed_chunks += 1

                            # Progress reporting
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

                # Save output to file
                with rasterio.MemoryFile() as memfile:
                    kwargs = src.meta.copy()
                    kwargs.update(
                        {
                            "driver": "GTiff",
                            "count": 1,
                            "dtype": "float32",
                            "nodata": -9999,
                        }
                    )

                    with memfile.open(**kwargs) as dst:
                        dst.write(output_data.astype(np.float32), 1)

                    output_file.write(memfile.read())

                print(f"Saved prediction to output file")
                return output_file

    def process_image(self, image_data, output_file):
        """
        Main entry point for image processing.

        Delegates to process_image_parallel for parallel processing.

        Args:
            image_data: Binary image data
            output_file: Output file object

        Returns:
            Output file object with results
        """
        return self.process_image_parallel(image_data, output_file)


# ============================================================================
# COMPATIBILITY WRAPPER (Same as original)
# ============================================================================
class WaterQualityPredictor(ParallelWaterQualityPredictor):
    """
    Convenience wrapper class that sets default max_workers=4.

    This maintains 100% backward compatibility with the original API.
    """

    def __init__(self, model_file, scaler_file):
        """
        Initialize predictor with model and scaler.

        Args:
            model_file: Binary model data or path
            scaler_file: Binary scaler data or path
        """
        super().__init__(model_file, scaler_file, max_workers=4)
