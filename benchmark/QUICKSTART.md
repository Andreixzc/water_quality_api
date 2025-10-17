# 🚀 Quick Start - Run Benchmark

## Step 1: Download Models

```bash
./download_models.sh
```

## Step 2: Run Benchmark

```bash
cd benchmark
python benchmark.py
```

## That's It! 🎉

Models used:
- **model.joblib** - RandomForestRegressor from your database
- **scaler.joblib** - StandardScaler from your database

Results saved to: `benchmark/results/`

For full guide see: `RUN_BENCHMARK_GUIDE.md`
