# 🚀 Benchmark Guide - Using Real Database Models

## Quick Start

```bash
# 1. Download models from database (if not already done)
./download_models.sh

# 2. Run the benchmark
cd benchmark
python benchmark.py
```

That's it! 🎉

---

## What the Benchmark Does

The benchmark evaluates your parallel processing implementation by:

### 1. **Strong Scalability Test**
- **Fixed problem size** (1000 reservoirs)
- **Varying workers**: 1, 2, 4, 6, 8 threads
- **Goal**: Measure speedup as you add more workers
- **Ideal**: Linear speedup (2x workers = 2x faster)

### 2. **Weak Scalability Test**
- **Proportional scaling**: Each worker gets 125 reservoirs
- **Workers**: 1→125, 2→250, 4→500, 6→750, 8→1000
- **Goal**: Keep processing time constant as workload scales
- **Ideal**: Flat execution time (perfect efficiency)

---

## Understanding the Output

### Console Output
```
╔══════════════════════════════════════════════════╗
║     PARALLEL PROCESSING BENCHMARK SUITE         ║
╚══════════════════════════════════════════════════╝

📊 Strong Scalability Test (Fixed Problem Size: 1000 reservoirs)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Workers | Time (s) | Speedup | Efficiency
--------|----------|---------|------------
   1    |  45.23   |  1.00x  |  100.0%
   2    |  23.15   |  1.95x  |   97.6%
   4    |  12.08   |  3.74x  |   93.6%
   6    |   8.42   |  5.37x  |   89.5%
   8    |   6.91   |  6.55x  |   81.8%
```

**What to look for:**
- ✅ **Speedup increases** with more workers (good parallelization)
- ✅ **Efficiency > 80%** (minimal overhead)
- ⚠️ **Speedup plateaus** at high worker counts (normal - CPU bound)

### Generated Visualizations

The benchmark creates plots in `benchmark/results/`:

1. **`strong_scalability.png`**
   - Shows execution time vs number of workers
   - Ideal: Downward curve (more workers = faster)

2. **`weak_scalability.png`**
   - Shows execution time for proportional workloads
   - Ideal: Flat line (consistent performance)

3. **`speedup_efficiency.png`**
   - Combined speedup and efficiency metrics
   - Ideal: Speedup near linear, efficiency > 80%

---

## Advanced Usage

### Custom Test Parameters

Edit `benchmark.py` to customize:

```python
# At the bottom of the file, around line 400+

# Strong scalability test
strong_results = benchmark.run_strong_scalability_test(
    num_reservoirs=1000,    # ← Change problem size
    worker_counts=[1, 2, 4, 6, 8, 16]  # ← Add more worker counts
)

# Weak scalability test
weak_results = benchmark.run_weak_scalability_test(
    reservoirs_per_worker=125,  # ← Change workload per worker
    worker_counts=[1, 2, 4, 6, 8, 16]
)
```

### Run Specific Tests

Modify the `if __name__ == '__main__':` section:

```python
if __name__ == '__main__':
    # Only run strong scalability
    strong_results = benchmark.run_strong_scalability_test(
        num_reservoirs=2000,
        worker_counts=[1, 2, 4, 8]
    )
    benchmark.plot_strong_scalability(strong_results)
    
    # Skip weak scalability test
```

---

## Interpreting Results

### Good Parallelization Signs ✅
- **Speedup > 0.9 × number of workers** (for 2-4 workers)
- **Efficiency > 80%** across all tests
- **Weak scalability time** stays relatively flat

### Issues to Watch For ⚠️

#### 1. **Poor Speedup (< 2x with 4 workers)**
**Causes:**
- Model prediction is too fast (not enough work per thread)
- Thread overhead dominates
- GIL contention (Python global interpreter lock)

**Solutions:**
- Increase problem size (`num_reservoirs`)
- Use process-based parallelism instead of threads
- Profile code to find bottlenecks

#### 2. **Efficiency Drops Quickly (< 60% at 4 workers)**
**Causes:**
- Too much thread management overhead
- Resource contention (CPU, memory)
- Poor load balancing

**Solutions:**
- Adjust `CHUNK_SIZE` in your actual code
- Reduce `MAX_WORKERS` to optimal point
- Check system CPU usage during test

#### 3. **Weak Scalability Time Increases**
**Causes:**
- Memory pressure with large datasets
- Cache inefficiency
- System resource saturation

**Solutions:**
- Monitor RAM usage during benchmark
- Reduce `reservoirs_per_worker`
- Use data streaming instead of loading all at once

---

## Model Requirements

Your models must be:

### Structure
```
benchmark/models/
├── model.pkl    # Trained ML model (RandomForest, XGBoost, etc.)
└── scaler.pkl   # StandardScaler or similar preprocessor
```

### Compatibility
The models should support:
```python
# Loading
model = pickle.load(open('model.pkl', 'rb'))
scaler = pickle.load(open('scaler.pkl', 'rb'))

# Prediction
X_scaled = scaler.transform(features)  # Features: 15 columns
predictions = model.predict(X_scaled)   # Returns: single value
```

### Feature Format (15 features)
Your models expect this input shape:
1. **B2** - Blue band
2. **B3** - Green band
3. **B4** - Red band
4. **B8** - NIR band
5. **B11** - SWIR band
6. **B12** - SWIR2 band
7. **NDCI** - Normalized Difference Chlorophyll Index
8. **NDVI** - Normalized Difference Vegetation Index
9. **FAI** - Floating Algae Index
10. **MNDWI** - Modified NDWI
11. **NDTI** - Normalized Difference Turbidity Index
12. **KIVU** - KIVU index
13. **NDRE** - Normalized Difference Red Edge
14. **Day of Year** - Temporal feature (1-365)
15. **Days Since Last** - Days since previous observation

The benchmark generates mock data matching this format.

---

## Benchmark vs Production

### Differences

| Aspect | Benchmark | Production API |
|--------|-----------|----------------|
| **Data Source** | Mock generators | Real satellite images |
| **Models** | From `benchmark/models/` | From database BinaryFields |
| **Purpose** | Test parallelization | Process actual requests |
| **Output** | Performance metrics | Water quality predictions |

### Why Benchmark?

- ✅ **Test without real data**: No need for satellite imagery
- ✅ **Reproducible**: Same mock data every run
- ✅ **Fast**: No API calls or image processing
- ✅ **Isolated**: Tests only parallel processing logic

---

## Troubleshooting

### Models Not Found
```
Error: Model file not found: benchmark/models/model.pkl
```

**Solution:**
```bash
./download_models.sh  # Re-download from database
```

### Import Errors
```
ModuleNotFoundError: No module named 'sklearn'
```

**Solution:**
```bash
pip install scikit-learn numpy matplotlib
```

### Memory Issues
```
MemoryError: Unable to allocate array
```

**Solution:**
Reduce problem size in benchmark:
```python
strong_results = benchmark.run_strong_scalability_test(
    num_reservoirs=500,  # ← Reduce from 1000
    worker_counts=[1, 2, 4]
)
```

### Slow Execution
If the benchmark takes too long:

1. **Reduce problem size**:
   ```python
   num_reservoirs=500  # Instead of 1000
   ```

2. **Skip large worker counts**:
   ```python
   worker_counts=[1, 2, 4]  # Skip 6, 8
   ```

3. **Run only one test**:
   ```python
   # Comment out weak scalability test
   ```

---

## Next Steps

After running the benchmark:

1. **Analyze the plots** in `benchmark/results/`
2. **Compare with your production metrics**
3. **Tune `MAX_WORKERS`** in `processing/config.py` based on efficiency
4. **Adjust `CHUNK_SIZE`** if needed (currently 0 = always parallel)
5. **Run benchmark again** to verify improvements

---

## Quick Reference Commands

```bash
# Download models from database
./download_models.sh

# Run benchmark (from project root)
cd benchmark && python benchmark.py

# Run benchmark with virtual environment
source myenv/bin/activate
cd benchmark && python benchmark.py

# View results
ls -lh benchmark/results/
```

---

## Performance Expectations

Based on your system (8 CPU cores):

### Strong Scalability
- **1 worker**: Baseline time
- **2 workers**: 1.8-1.95x speedup
- **4 workers**: 3.5-3.9x speedup
- **8 workers**: 6.0-7.0x speedup

### Weak Scalability
- **Ideal**: ±10% time variation across all worker counts
- **Acceptable**: ±25% variation
- **Poor**: >50% increase with more workers

---

## Support

If you encounter issues:

1. Check model files exist: `ls -lh benchmark/models/`
2. Verify Python environment: `python --version` (should be 3.8+)
3. Check dependencies: `pip list | grep -E "scikit-learn|numpy|matplotlib"`
4. Review error messages in console output
5. Examine generated plots for anomalies

Good luck with your benchmarking! 🚀
