import uuid
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
import glob

from api.models import WaterQualityAnalysis


class WaterQualityProcessor:
    def __init__(self, model_path, scaler_path):
        """Initialize the processor with model and scaler paths"""
        try:
            ee.Initialize()
        except Exception as e:  # noqa
            ee.Authenticate()
            ee.Initialize()

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)

        self.feature_names = [
            "B2",
            "B3",
            "B4",
            "B5",
            "B8",
            "B11",
            "NDCI",
            "NDVI",
            "FAI",
            "B3_B2_ratio",
            "B4_B3_ratio",
            "B5_B4_ratio",
            "Month",
            "Season",
        ]
    def create_daily_mosaic(self, aoi, date):
        """Create a daily mosaic for the given area of interest and date"""
        start_date = ee.Date(date)
        end_date = start_date.advance(1, "day")

        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
              .filterBounds(aoi)
              .filterDate(start_date, end_date)
              .map(lambda image: image.set('date', image.date().format('yyyy-MM-dd'))))

        daily_mosaic = ee.ImageCollection(
            ee.Join.saveAll('images').apply(
                primary=s2,
                secondary=s2,
                condition=ee.Filter.And(
                    ee.Filter.equals(leftField='date', rightField='date'),
                    ee.Filter.equals(leftField='SPACECRAFT_NAME', rightField='SPACECRAFT_NAME'),
                    ee.Filter.equals(leftField='SENSING_ORBIT_NUMBER', rightField='SENSING_ORBIT_NUMBER')
                )
            )
        ).map(lambda image: ee.ImageCollection(ee.List(image.get('images'))).mosaic()
              .set('system:time_start', ee.Date(image.get('date')).millis()))

        return daily_mosaic.first()
    def process_tile(self, tile_geometry, date):
        """Process a single tile of the area of interest"""
        daily_mosaic = self.create_daily_mosaic(tile_geometry, date)
        if daily_mosaic is None:
            return None
        # Criar uma collection de 1 dia
        start_date = ee.Date(date)
        end_date = start_date.advance(1, "day")

        # Sentinel-2 collection for tile
        sentinel2 = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(tile_geometry)
            .filterDate(start_date, end_date)
        )

        if sentinel2.size().getInfo() == 0:
            return None

        # Usar median() mesmo com uma imagem para manter a lógica que funciona
        image = daily_mosaic.clip(tile_geometry)

        qa60 = image.select("QA60").toInt()

        # Bit 10 é nuvem densa e bit 11 é cirrus
        cloudBitMask = ee.Number(1 << 10)
        cirrusBitMask = ee.Number(1 << 11)

        # Se algum dos bits for 1, é nuvem
        cloud_mask = (
            qa60.bitwiseAnd(cloudBitMask)
            .eq(0)
            .And(qa60.bitwiseAnd(cirrusBitMask).eq(0))
        )

        # Select bands of interest
        bands = ["B2", "B3", "B4", "B5", "B8", "B11"]
        image = image.select(bands)

        # Create water mask
        MNDWI = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
        water_mask = MNDWI.gt(0.3)

        valid_mask = water_mask.And(cloud_mask)

        # Calculate indices
        NDCI = image.normalizedDifference(["B5", "B4"]).rename("NDCI")
        NDVI = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        FAI = image.expression(
            "NIR - (RED + (SWIR - RED) * (NIR_wl - RED_wl) / (SWIR_wl - RED_wl))",  # noqa
            {
                "NIR": image.select("B8"),
                "RED": image.select("B4"),
                "SWIR": image.select("B11"),
                "NIR_wl": 842,
                "RED_wl": 665,
                "SWIR_wl": 1610,
            },
        ).rename("FAI")

        # Calculate band ratios
        B3_B2_ratio = (
            image.select("B3").divide(image.select("B2")).rename("B3_B2_ratio")
        )
        B4_B3_ratio = (
            image.select("B4").divide(image.select("B3")).rename("B4_B3_ratio")
        )
        B5_B4_ratio = (
            image.select("B5").divide(image.select("B4")).rename("B5_B4_ratio")
        )

        # Get date information
        image_date = ee.Date(start_date)
        month = ee.Image.constant(image_date.get("month")).rename("Month")
        season = ee.Image.constant(
            image_date.get("month").add(2).divide(3).floor().add(1)
        ).rename("Season")

        # Combine all features
        image_with_indices = image.addBands(
            [
                NDCI,
                NDVI,
                FAI,
                B3_B2_ratio,
                B4_B3_ratio,
                B5_B4_ratio,
                month,
                season,
            ]
        )

        # Create scaled bands
        scaled_bands = []
        for i, name in enumerate(self.feature_names):
            scaled_band = (
                image_with_indices.select(name)
                .subtract(ee.Number(self.scaler.mean_[i]))
                .divide(ee.Number(self.scaler.scale_[i]))
                .rename(f"scaled_{name}")
            )
            scaled_bands.append(scaled_band)

        # Combine scaled bands
        scaled_image = ee.Image.cat(scaled_bands)

        # Create prediction
        weighted_bands = []
        for i, (name, importance) in enumerate(
            zip(self.feature_names, self.model.feature_importances_)
        ):
            weighted_band = scaled_image.select(f"scaled_{name}").multiply(
                ee.Number(importance)
            )
            weighted_bands.append(weighted_band)

        predicted_image = (
            ee.Image.cat(weighted_bands)
            .reduce(ee.Reducer.sum())
            .rename("parameter_pred")
        )

        # Usar where em vez de updateMask para manter a lógica que funciona
        final_image = predicted_image.where(
            valid_mask.Not(), ee.Image.constant(-9999)
        )

        return final_image

    def process_reservoir(self, reservoir_id, parameter_id, coordinates, start_date, end_date, request_user, output_dir="outputs"):
        """Process a reservoir for all available dates in the given range"""
        aoi = ee.Geometry.Polygon([coordinates])
        print("Converted AOI:", aoi.getInfo())

        os.makedirs(output_dir, exist_ok=True)

        # Get all available dates
        date_collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
        )

        dates = date_collection.aggregate_array("system:time_start").getInfo()
        dates = [
            datetime.fromtimestamp(d / 1000).strftime("%Y-%m-%d")
            for d in dates
        ]

        dates = list(set(dates))

        results = []

        for date in dates:
            try:
                output_tiff, processing_statistics = self._process_single_date(
                    reservoir_id, aoi, date, parameter_id, output_dir
                )
                # analyse creation
                water_quality_analysis, _ = (
                    WaterQualityAnalysis.objects.get_or_create(
                        reservoir_id=reservoir_id,
                        analysis_date=date,
                        defaults={"identifier_code": uuid.uuid4()},
                    )
                )
                results.append(
                    (
                        date,
                        output_tiff,
                        processing_statistics,
                        water_quality_analysis,
                    )
                )

            except Exception as e:
                print(f"Error processing date {date}: {str(e)}")

        return results

    def _process_single_date(
        self, reservoir_id, aoi, date, parameter_id, output_dir
    ):
        """Process a single date for the reservoir"""
        aoi_bounds = aoi.bounds().getInfo()["coordinates"][0]
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
                    out_file = os.path.join(
                        output_dir, f"Tile_{date}_{i+1}_{j+1}.tif"
                    )
                    with lock:
                        geemap.ee_export_image(
                            tile_result,
                            filename=out_file,
                            scale=30,
                            region=tile_geometry,
                        )
                        tile_results.append(out_file)
            except Exception as e:
                print(
                    f"Error processing tile {i+1}_{j+1} "
                    + f"for date {date}: {str(e)}"
                )

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

        output_filename = f"{reservoir_id}_{date}_{parameter_id}.tif"
        merged_output_path = self.merge_tiff_files(
            output_dir, f"Tile_{date}", output_filename
        )

        with rasterio.open(merged_output_path) as src:
            data = src.read(1)
            valid_data = data[data != -9999]
            min_value = np.min(valid_data)
            max_value = np.max(valid_data)

        processing_statistics = {
            "min_value": min_value,
            "max_value": max_value,
        }

        return merged_output_path, processing_statistics

    def merge_tiff_files(self, directory, pattern, output_file):
        """Merge multiple TIFF files into a single file"""
        merged_dir = os.path.join(directory, "merged")
        os.makedirs(merged_dir, exist_ok=True)

        tif_files = glob.glob(os.path.join(directory, f"{pattern}*.tif"))

        print("Merging tiff files:")
        for file in tif_files:
            print(file)

        if not tif_files:
            raise ValueError("No TIFF files found to merge")

        src_files_to_mosaic = []
        for tif in tif_files:
            src = rasterio.open(tif)
            src_files_to_mosaic.append(src)

        try:
            mosaic, out_trans = merge(src_files_to_mosaic)

            out_meta = src_files_to_mosaic[0].meta.copy()
            out_meta.update(
                {
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": out_trans,
                    "nodata": -9999,  # Explicitly set the no-data value
                }
            )

            merged_output_file = os.path.join(merged_dir, output_file)
            with rasterio.open(merged_output_file, "w", **out_meta) as dest:
                dest.write(mosaic)

            print(f"Merged TIFF file created: {merged_output_file}")

        finally:
            for src in src_files_to_mosaic:
                src.close()

        # Delete the original tile TIFs (commented out for safety)
        for tif in tif_files:
            try:
                os.remove(tif)
                print(f"Would delete tile file: {tif}")
            except Exception as e:
                print(f"Error deleting {tif}: {str(e)}")

        return merged_output_file