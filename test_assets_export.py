#!/usr/bin/env python3
"""
Test script to verify Earth Engine Assets export works
This should avoid the storage quota issue completely
"""

import ee
import os
from google.oauth2 import service_account

def test_assets_export():
    # Initialize Earth Engine
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    ee.Initialize(ee.ServiceAccountCredentials(None, credentials_path))
    print("✅ Earth Engine initialized successfully")
    
    # Create a simple test image
    test_image = ee.Image("COPERNICUS/S2_SR/20200101T095041_20200101T095939_T33TWG")
    
    # Define a small test region
    test_region = ee.Geometry.Rectangle([-8.7, 39.9, -8.6, 40.0])  # Small area in Portugal
    
    # Test asset export
    asset_id = f"projects/ee-inferno/assets/test_export_no_quota"
    
    export_params = {
        "image": test_image.select(['B2', 'B3', 'B4']), 
        "description": "test_export_no_quota",
        "assetId": asset_id,
        "scale": 100,  # Large scale for small file
        "region": test_region,
        "maxPixels": 1e6  # Small number of pixels
    }
    
    print("🚀 Starting test export to Earth Engine Assets...")
    task = ee.batch.Export.image.toAsset(**export_params)
    task.start()
    
    print(f"✅ Task started successfully!")
    print(f"Task ID: {task.id}")
    print(f"Asset ID: {asset_id}")
    print(f"Status: {task.status()}")
    
    return task.id

if __name__ == "__main__":
    try:
        task_id = test_assets_export()
        print(f"\n🎉 SUCCESS! Assets export test task created: {task_id}")
        print("This approach should avoid the 'Service accounts do not have storage quota' error!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
