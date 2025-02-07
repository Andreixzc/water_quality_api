import ee
from datetime import datetime
from typing import List, Dict

class SatelliteImageExtractor:
    def __init__(self):
        ee.Initialize()
        
    def create_export_tasks(self, coordinates: List[List[float]], start_date: str, end_date: str, folder_name: str) -> List[Dict]:
        """
        Creates export tasks for satellite images and returns task information
        
        Args:
            coordinates: List of [longitude, latitude] pairs defining the polygon
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            folder_name: Name of the folder in Google Drive to store images
            
        Returns:
            List of dictionaries containing task information
        """
        # Define area of interest
        self.coordinates = coordinates
        aoi = ee.Geometry.Polygon([coordinates])
        
        # Filter image collection
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .map(lambda image: image.set("date", image.date().format("yyyy-MM-dd"))))
        
        # Create daily mosaics
        daily = ee.ImageCollection(
            ee.Join.saveAll("images").apply(
                primary=s2,
                secondary=s2,
                condition=ee.Filter.And(
                    ee.Filter.equals(leftField="date", rightField="date"),
                    ee.Filter.equals(leftField="SPACECRAFT_NAME", rightField="SPACECRAFT_NAME"),
                    ee.Filter.equals(leftField="SENSING_ORBIT_NUMBER", rightField="SENSING_ORBIT_NUMBER"),
                ),
            )
        ).map(
            lambda image: ee.ImageCollection(ee.List(image.get("images")))
            .mosaic()
            .set("system:time_start", ee.Date(image.get("date")).millis())
        )
        
        collection_to_export = daily.map(self._prepare_for_export)
        size = collection_to_export.size().getInfo()
        if size == 0:
            print(f"No images found between {start_date} and {end_date}")
            return []
        image_list = collection_to_export.toList(size)
        
        # Start exports and collect task information
        tasks_info = []
        for i in range(size):
            image = image_list.get(i)
            task_info = self._create_export_task(image, aoi, folder_name)
            tasks_info.append(task_info)
        
        print("Tasks info:", tasks_info)  # Debug print
        return tasks_info

    def _prepare_for_export(self, image):
        """Prepare image for export with water and cloud masking"""
        # Convert all bands to float32 first
        bands = ["B2", "B3", "B4", "B5", "B8", "B11"]
        base_image = image.select(bands).toFloat()
        
        # Create cloud mask from QA60 band
        qa60 = image.select("QA60").toInt()
        cloudBitMask = ee.Number(1 << 10)  # Dense cloud
        cirrusBitMask = ee.Number(1 << 11)  # Cirrus
        cloud_mask = (qa60.bitwiseAnd(cloudBitMask).eq(0)
                     .And(qa60.bitwiseAnd(cirrusBitMask).eq(0)))
        
        # Create water mask using MNDWI
        mndwi = base_image.normalizedDifference(["B3", "B11"])
        water_mask = mndwi.gt(0.3)
        
        # Combine masks
        valid_mask = water_mask.And(cloud_mask)
        
        # Scale the base bands to 0-1 range
        base_image = base_image.divide(10000)
        
        # Calculate indices
        ndci = base_image.normalizedDifference(["B5", "B4"]).rename("NDCI")
        ndvi = base_image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        # Calculate FAI
        fai = base_image.expression(
            "NIR - (RED + (SWIR - RED) * (NIR_wl - RED_wl) / (SWIR_wl - RED_wl))",
            {
                "NIR": base_image.select("B8"),
                "RED": base_image.select("B4"),
                "SWIR": base_image.select("B11"),
                "NIR_wl": 842,
                "RED_wl": 665,
                "SWIR_wl": 1610,
            }
        ).rename("FAI")
        
        # Calculate band ratios
        b3_b2_ratio = base_image.select("B3").divide(base_image.select("B2")).rename("B3_B2_ratio")
        b4_b3_ratio = base_image.select("B4").divide(base_image.select("B3")).rename("B4_B3_ratio")
        b5_b4_ratio = base_image.select("B5").divide(base_image.select("B4")).rename("B5_B4_ratio")
        
        # Combine all bands
        final_image = base_image.addBands([ndci, ndvi, fai, mndwi.rename("MNDWI"),
                                         b3_b2_ratio, b4_b3_ratio, b5_b4_ratio])
        
        # Apply mask to all bands
        final_image = final_image.updateMask(valid_mask)
        
        # Calculate cloud percentage
        aoi = ee.Geometry.Polygon(self.coordinates)
        cloud_percentage = calculate_cloud_percentage(image, aoi)
        
        return final_image.set("cloud_percentage", cloud_percentage).set("system:time_start", image.get("system:time_start"))
        
    def _create_export_task(self, image, aoi, folder_name):
        image = ee.Image(image)
        date = ee.Date(image.get("system:time_start")).format("yyyy-MM-dd").getInfo()
        cloud_percentage = image.get("cloud_percentage").getInfo()
        print(f"Cloud percentage for {date}: {cloud_percentage}")
        
        # Create filename with date
        filename = f"{folder_name}_{date}"
        print("-----------------------------------------------------------------")
        print(filename)
        
        export_params = {
            "image": image, 
            "description": filename,  # This will be the filename
            "scale": 10,
            "region": aoi,
            "fileFormat": "GeoTIFF",
            "maxPixels": 1e13,
            "folder": folder_name
        }
        
        task = ee.batch.Export.image.toDrive(**export_params)
        task.start()
        
        return {
            "task_id": task.id,
            "date": date,
            "folder": folder_name,
            "filename": filename,
            "status": "STARTED",
            "cloud_percentage": cloud_percentage
        }
def calculate_cloud_percentage(image, aoi):
    """Calculates the cloud percentage in the image"""
    scl = image.select('SCL')
    cloud_mask = scl.eq(8).Or(scl.eq(9)).Or(scl.eq(3))  # 8: cloud medium probability, 9: cloud high probability, 3: cloud shadows
    
    total_pixels = ee.Number(scl.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=aoi,
        scale=10,
        maxPixels=1e13
    ).get('SCL'))
    
    cloud_pixels = ee.Number(cloud_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,
        maxPixels=1e13
    ).get('SCL'))
    
    cloud_percentage = cloud_pixels.divide(total_pixels).multiply(100)
    
    return cloud_percentage