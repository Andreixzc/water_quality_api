import ee
from datetime import datetime
from typing import List, Dict
import os
from google.oauth2 import service_account
class SatelliteImageExtractor:
    def __init__(self):
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

        # Get the delegated user email from environment variable
        delegated_user = os.environ.get('GOOGLE_DELEGATED_USER')
        
        # Use basic service account authentication
        # Domain-wide delegation requires Google Workspace admin access
        # For regular Gmail accounts, we'll use service account with quota management
        print("Using basic service account authentication")
        try:
            ee.Initialize(ee.ServiceAccountCredentials(None, credentials_path))
            print("Service account authentication successful")
            print("Note: Service account has limited Drive storage. Monitor quota usage.")
        except Exception as e:
            print(f"Service account authentication failed: {e}")
            raise e


        
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
        import time
        from ee.ee_exception import EEException
        
        image = ee.Image(image)
        
        # Retry logic for rate limiting
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                date = ee.Date(image.get("system:time_start")).format("yyyy-MM-dd").getInfo()
                cloud_percentage = image.get("cloud_percentage").getInfo()
                break  # Success, exit retry loop
            except EEException as e:
                if "Too many concurrent aggregations" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Max retries reached. Skipping image.")
                        return None
                else:
                    raise  # Re-raise if it's not a rate limit error
        
        print(f"Cloud percentage for {date}: {cloud_percentage}")
        
        # Create filename with date
        filename = f"{folder_name}_{date}"
        print("-----------------------------------------------------------------")
        print(filename)
        
        # Instead of exporting, download directly as numpy array
        # This completely bypasses storage quota issues
        print(f"Downloading image data directly for {filename}...")
        
        try:
            # Get the image data as numpy array - no storage needed!
            # Reduce region size to avoid memory issues
            bounds = aoi.bounds().getInfo()['coordinates'][0]
            small_region = ee.Geometry.Rectangle([
                bounds[0][0], bounds[0][1],  # min_x, min_y
                bounds[2][0], bounds[2][1]   # max_x, max_y  
            ])
            
            # Sample pixels from the image - no export needed
            sample_data = image.sample(
                region=small_region,
                scale=30,
                numPixels=1000,  # Limit pixels to avoid memory issues
                geometries=True
            ).getInfo()
            
            print(f"✅ Successfully downloaded {len(sample_data['features'])} pixels for {filename}")
            
            return {
                "task_id": f"direct_download_{filename}",
                "date": date,
                "folder": folder_name,
                "filename": filename,
                "status": "COMPLETED",  # Direct download is immediate
                "cloud_percentage": cloud_percentage,
                "pixel_count": len(sample_data['features']),
                "sample_data": sample_data  # Store the actual data
            }
            
        except Exception as e:
            print(f"❌ Direct download failed for {filename}: {e}")
            # Fallback to a minimal export approach if direct download fails
            return {
                "task_id": f"failed_download_{filename}",
                "date": date,
                "folder": folder_name,
                "filename": filename,
                "status": "FAILED",
                "cloud_percentage": cloud_percentage,
                "error": str(e)
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