import ee
import os

# Initialize Earth Engine using the environment variable
credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if credentials_path and os.path.exists(credentials_path):
    # Use basic service account authentication
    ee.Initialize(ee.ServiceAccountCredentials(None, credentials_path))
    print("Earth Engine initialized successfully")
else:
    print("Error: Could not find credentials file")
    exit(1)

try:
    # List all operations (tasks)
    operations = ee.data.listOperations()
    print(f"Found {len(operations)} operations")
    
    # Cancel running or pending tasks
    cancelled_count = 0
    for operation in operations:
        if 'done' not in operation or not operation['done']:
            try:
                ee.data.cancelOperation(operation['name'])
                print(f"Cancelled task: {operation['name']}")
                cancelled_count += 1
            except Exception as e:
                print(f"Failed to cancel {operation['name']}: {e}")
    
    print(f"Successfully cancelled {cancelled_count} tasks")
    
except Exception as e:
    print(f"Error accessing Earth Engine: {e}")
