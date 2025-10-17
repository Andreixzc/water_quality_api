# Complete Guide: From No Models → Running Benchmark

## Current Situation

Your database shows:
```
model_file: null  ← Need to upload!
scaler_file: null ← Need to upload!
```

## Three Paths Forward

### Path 1: Use Mock Models (Quickest - For Testing)

**Perfect if you just want to test the benchmark**

```bash
cd /home/andrei/projects/water_quality_api/benchmark

# Create mock models
python create_mock_models.py

# This creates:
# - benchmark/models/model.pkl
# - benchmark/models/scaler.pkl

# Run benchmark immediately!
python benchmark.py
```

**Done!** No Docker, no database needed.

---

### Path 2: Upload Existing Models to Database

**If you have real trained models somewhere**

#### Step 1: Get your model files

Make sure you have:
- `model.pkl` - Your trained scikit-learn model
- `scaler.pkl` - Your fitted StandardScaler

#### Step 2: Copy to Docker container

```bash
# Copy files into container
sudo docker cp /path/to/your/model.pkl water_quality_api-web-1:/tmp/
sudo docker cp /path/to/your/scaler.pkl water_quality_api-web-1:/tmp/
```

#### Step 3: Upload to database

```bash
sudo docker-compose exec web python manage.py upload_ml_models \
  --model-id=1 \
  --model-file=/tmp/model.pkl \
  --scaler-file=/tmp/scaler.pkl
```

#### Step 4: Export for benchmark

```bash
./benchmark/export_models.sh
```

#### Step 5: Run benchmark

```bash
cd benchmark
python benchmark.py
```

---

### Path 3: Train New Models

**If you need to train from scratch**

#### Step 1: Prepare training data

You need a CSV with these 15 columns:
- **Bands:** B2, B3, B4, B5, B8, B11
- **Indices:** NDCI, NDVI, FAI, MNDWI, B3_B2_ratio, B4_B3_ratio, B5_B4_ratio
- **Temporal:** month, season
- **Target:** chlorophyll (or your water quality parameter)

#### Step 2: Train model

```python
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Load your training data
df = pd.read_csv('training_data.csv')

# Features (15 columns)
feature_cols = [
    'B2', 'B3', 'B4', 'B5', 'B8', 'B11',  # Bands
    'NDCI', 'NDVI', 'FAI', 'MNDWI',      # Indices
    'B3_B2_ratio', 'B4_B3_ratio', 'B5_B4_ratio',  # Ratios
    'month', 'season'  # Temporal
]
X = df[feature_cols]
y = df['chlorophyll']  # Target

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train scaler
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Train model
model = RandomForestRegressor(
    n_estimators=100,
    max_depth=20,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)

# Evaluate
score = model.score(X_test_scaled, y_test)
print(f"Model R² score: {score:.3f}")

# Save models
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

print("Models saved!")
```

#### Step 3: Upload to database

Follow Path 2, Step 2-5 above.

---

## Verification Checklist

### ✓ Check 1: Files exist locally

```bash
ls -lh benchmark/models/
# Should show:
# model.pkl
# scaler.pkl
```

### ✓ Check 2: Files can be loaded

```bash
cd benchmark
python -c "
import pickle
with open('models/model.pkl', 'rb') as f:
    model = pickle.load(f)
with open('models/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)
print('✓ Models loaded successfully!')
print(f'Model type: {type(model)}')
print(f'Scaler type: {type(scaler)}')
"
```

### ✓ Check 3: Files in database (if uploaded)

```bash
sudo docker-compose exec web python manage.py shell
```

```python
from api.models.machine_learning_model import MachineLearningModel

model = MachineLearningModel.objects.get(id=1)
print(f"Model file: {'✓' if model.model_file else '✗ NULL'}")
print(f"Scaler file: {'✓' if model.scaler_file else '✗ NULL'}")

if model.model_file:
    print(f"Size: {len(model.model_file):,} bytes")
```

---

## Quick Decision Tree

```
Do you have trained models?
├─ NO → Use Path 1 (Mock models)
│       Fastest way to test benchmark
│
└─ YES → Are they already in database?
         ├─ NO → Use Path 2 (Upload to DB)
         │       Get them from disk
         │
         └─ YES but showing NULL → Check model registration
                 Your model record exists but files weren't uploaded
                 Use Path 2 to upload the actual files
```

---

## Common Issues

### Issue: "model_file is NULL"

**Cause:** Model record exists but binary data wasn't uploaded

**Solution:** Use Path 2 to upload the actual .pkl files

### Issue: "No module named 'sklearn'"

**Cause:** Missing dependencies for benchmark

**Solution:**
```bash
cd benchmark
pip install numpy pandas matplotlib scikit-learn joblib
```

### Issue: "Cannot import model"

**Cause:** Model was trained with different sklearn version

**Solution:** Use same sklearn version or retrain model

### Issue: "Model has 10 features but got 15"

**Cause:** Model trained on different feature set

**Solution:** Ensure model expects 15 features (6 bands + 7 indices + 2 temporal)

---

## Recommended Workflow

**For Quick Testing:**
```bash
cd benchmark
python create_mock_models.py
python benchmark.py
```
**Time:** 2 minutes

**For Production/Real Data:**
```bash
# 1. Train or get real models (Path 3 or have them ready)
# 2. Upload to database (Path 2)
# 3. Export for benchmark
./benchmark/export_models.sh
# 4. Run benchmark
cd benchmark
python benchmark.py
```
**Time:** 10-30 minutes (depending on training)

---

## Next Steps

Once you have models ready:

1. ✓ Models exist in `benchmark/models/`
2. ✓ Run benchmark: `python benchmark.py`
3. ✓ Wait 10-30 minutes for completion
4. ✓ Check results in `benchmark/results/`
5. ✓ View plots and reports
6. ✓ Analyze scalability metrics

---

## Support Files Created

- `create_mock_models.py` - Generate test models
- `upload_ml_models.py` - Django command to upload
- `export_ml_models.py` - Django command to export
- `export_models.sh` - Shell script to export
- `UPLOAD_MODELS_GUIDE.md` - Detailed upload instructions
- This file - Complete workflow guide
