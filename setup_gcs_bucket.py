#!/usr/bin/env python3
"""
Script to create Google Cloud Storage bucket for water quality exports
This avoids the service account Drive storage quota issue
"""

import os
from google.cloud import storage
from google.oauth2 import service_account

def create_bucket():
    # Get credentials
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    # Create credentials
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    
    # Create storage client
    client = storage.Client(credentials=credentials, project=credentials.project_id)
    
    bucket_name = "water-quality-exports"
    
    try:
        # Try to get the bucket first
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            print(f"Bucket '{bucket_name}' already exists!")
            return bucket_name
    except Exception as e:
        print(f"Bucket doesn't exist, creating it: {e}")
    
    try:
        # Create the bucket
        bucket = client.create_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' created successfully!")
        
        # Make it publicly readable (optional)
        bucket.make_public()
        print(f"Bucket '{bucket_name}' made publicly readable")
        
        return bucket_name
        
    except Exception as e:
        print(f"Error creating bucket: {e}")
        print("This might be because:")
        print("1. The bucket name is already taken globally")
        print("2. Your service account doesn't have Storage Admin permissions")
        print("3. Billing is not enabled on your project")
        
        # Try with a more unique name
        import uuid
        unique_bucket_name = f"water-quality-exports-{str(uuid.uuid4())[:8]}"
        print(f"Trying with unique name: {unique_bucket_name}")
        
        try:
            bucket = client.create_bucket(unique_bucket_name)
            print(f"Bucket '{unique_bucket_name}' created successfully!")
            return unique_bucket_name
        except Exception as e2:
            print(f"Failed to create bucket with unique name: {e2}")
            raise e2

if __name__ == "__main__":
    try:
        bucket_name = create_bucket()
        print(f"\n✅ Success! Bucket ready: {bucket_name}")
        print("Now update the satellite.py file to use this bucket name if different from 'water-quality-exports'")
    except Exception as e:
        print(f"\n❌ Failed to create bucket: {e}")
        print("\nNext steps:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Cloud Storage API")
        print("3. Grant Storage Admin role to your service account")
        print("4. Enable billing on your project")
