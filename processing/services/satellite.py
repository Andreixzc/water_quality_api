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
        image_list = collection_to_export.toList(collection_to_export.size())
        
        # Start exports and collect task information
        tasks_info = []
        size = collection_to_export.size().getInfo()
        
        for i in range(size):
            image = image_list.get(i)
            task_info = self._create_export_task(image, aoi, folder_name)
            tasks_info.append(task_info)
            
        return tasks_info

    def _prepare_for_export(self, image):
        """Your existing prepare_for_export function"""
        # ... (same as your current code)
        
    def _create_export_task(self, image, aoi, folder_name):
        """Creates a single export task and returns task information"""
        image = ee.Image(image)
        date = ee.Date(image.get("system:time_start")).format("yyyy-MM-dd").getInfo()
        
        export_params = {
            "image": image, 
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
            "status": "STARTED"
        }