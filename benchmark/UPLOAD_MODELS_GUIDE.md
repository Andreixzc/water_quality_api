# How to Upload ML Model Files

## Problem

Your database record shows:
```
model_file: null
scaler_file: null
```

The model files need to be **uploaded as binary data** to the database.

## Solution Options

### Option 1: Upload via API (Recommended)

Use the API endpoint to upload your model files:

```bash
# Assuming you have model.pkl and scaler.pkl files somewhere
curl -X PATCH http://localhost:8000/api/machine-learning-models/1/ \
  -F "model_file=@/path/to/your/model.pkl" \
  -F "scaler_file=@/path/to/your/scaler.pkl"
```

Or using Python:

```python
import requests

url = "http://localhost:8000/api/machine-learning-models/1/"
files = {
    'model_file': open('/path/to/your/model.pkl', 'rb'),
    'scaler_file': open('/path/to/your/scaler.pkl', 'rb')
}

response = requests.patch(url, files=files)
print(response.json())
```

### Option 2: Django Management Command

Create a management command to load files from disk:

```python
# api/management/commands/upload_ml_models.py
from django.core.management.base import BaseCommand
from api.models.machine_learning_model import MachineLearningModel


class Command(BaseCommand):
    help = 'Upload ML model files from disk to database'

    def add_arguments(self, parser):
        parser.add_argument('--model-id', type=int, required=True)
        parser.add_argument('--model-file', type=str, required=True)
        parser.add_argument('--scaler-file', type=str, required=True)

    def handle(self, *args, **options):
        model = MachineLearningModel.objects.get(id=options['model_id'])
        
        with open(options['model_file'], 'rb') as f:
            model.model_file = f.read()
        
        with open(options['scaler_file'], 'rb') as f:
            model.scaler_file = f.read()
        
        model.save()
        self.stdout.write(self.style.SUCCESS('✓ Model files uploaded!'))
```

Then run:
```bash
sudo docker-compose exec web python manage.py upload_ml_models \
  --model-id=1 \
  --model-file=/path/to/model.pkl \
  --scaler-file=/path/to/scaler.pkl
```

### Option 3: Django Shell

Upload directly via Django shell:

```bash
sudo docker-compose exec web python manage.py shell
```

Then in the shell:

```python
from api.models.machine_learning_model import MachineLearningModel

# Get your model
model = MachineLearningModel.objects.get(id=1)

# Load model file
with open('/path/to/model.pkl', 'rb') as f:
    model.model_file = f.read()

# Load scaler file
with open('/path/to/scaler.pkl', 'rb') as f:
    model.scaler_file = f.read()

# Save
model.save()

print(f"Model file size: {len(model.model_file)} bytes")
print(f"Scaler file size: {len(model.scaler_file)} bytes")
```

### Option 4: Direct SQL (If files are in container)

If you have the .pkl files somewhere in your Docker container:

```bash
# Copy files to container first
sudo docker cp /local/path/model.pkl water_quality_api-web-1:/tmp/
sudo docker cp /local/path/scaler.pkl water_quality_api-web-1:/tmp/

# Then use Django shell as in Option 3
sudo docker-compose exec web python manage.py shell
```

```python
from api.models.machine_learning_model import MachineLearningModel

model = MachineLearningModel.objects.get(id=1)

with open('/tmp/model.pkl', 'rb') as f:
    model.model_file = f.read()

with open('/tmp/scaler.pkl', 'rb') as f:
    model.scaler_file = f.read()

model.save()
```

## Where to Get the Model Files?

If you don't have the `.pkl` files yet, you need to:

### 1. Train your model and save it

```python
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Train your model
model = RandomForestRegressor()
model.fit(X_train, y_train)

# Save model
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Save scaler
scaler = StandardScaler()
scaler.fit(X_train)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
```

### 2. Or use existing trained models

If you have trained models stored elsewhere:
- On your local machine
- In a cloud storage bucket
- In another database

## Verification

After uploading, verify the files are there:

```bash
sudo docker-compose exec web python manage.py shell
```

```python
from api.models.machine_learning_model import MachineLearningModel

model = MachineLearningModel.objects.get(id=1)

print(f"Model file: {'✓ Exists' if model.model_file else '✗ NULL'}")
print(f"Scaler file: {'✓ Exists' if model.scaler_file else '✗ NULL'}")

if model.model_file:
    print(f"Model size: {len(model.model_file):,} bytes")
if model.scaler_file:
    print(f"Scaler size: {len(model.scaler_file):,} bytes")
```

## For Benchmark

Once the files are uploaded to the database, you can export them:

```bash
./benchmark/export_models.sh
```

This will:
1. Export from database to `/app/benchmark/models/` in container
2. Copy to local `./benchmark/models/`
3. You can then run the benchmark standalone

## Quick Test with Mock Models

If you just want to test the benchmark with dummy models:

```python
# create_mock_models.py
import pickle
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Create mock training data (15 features)
X_mock = np.random.randn(100, 15)
y_mock = np.random.randn(100)

# Train simple model
model = RandomForestRegressor(n_estimators=10, random_state=42)
model.fit(X_mock, y_mock)

# Create scaler
scaler = StandardScaler()
scaler.fit(X_mock)

# Save
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

print("Mock models created!")
print(f"model.pkl: {os.path.getsize('model.pkl')} bytes")
print(f"scaler.pkl: {os.path.getsize('scaler.pkl')} bytes")
```

Then upload these to your database using any of the methods above.
