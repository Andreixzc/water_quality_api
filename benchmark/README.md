# Parallel Processing Benchmark

Simple, standalone benchmark for testing parallel processing scalability.

## Setup

### 1. Install Dependencies

```bash
cd benchmark
pip install numpy pandas matplotlib scikit-learn joblib
```

### 2. Copy Model Files

Run the helper script to copy your ML model and scaler:

```bash
python setup_models.py
```

This will copy the model files from the Docker container to `benchmark/models/`.

### 3. Run Benchmark

```bash
python benchmark.py
```

## What It Tests

### Strong Scalability
- **Fixed problem size**, varying number of workers
- Tests: 100, 400, 900, 1600 pixels
- Workers: 1, 2, 4, 6, 8
- **Ideal:** Linear speedup (2x workers = 2x speedup)

### Weak Scalability
- **Problem size scales with workers**
- Base: 100 pixels per worker
- **Ideal:** Constant execution time

## Results

Results are saved to `benchmark/results/`:

- `strong_scalability.csv` - Raw data for strong scaling
- `weak_scalability.csv` - Raw data for weak scaling
- `strong_scalability.png` - Visualization plots
- `weak_scalability.png` - Visualization plots
- `BENCHMARK_REPORT.md` - Summary report
- `benchmark_results.json` - Complete results in JSON

## Metrics

- **Execution Time:** Time to process all pixels
- **Speedup:** Sequential time / Parallel time
- **Efficiency:** Speedup / Number of workers

## Example Output

```
=============================================================================
PARALLEL PROCESSING BENCHMARK
Water Quality Prediction - Scalability Analysis
=============================================================================

Configuration:
  CPU Cores: 8
  Strong Scalability Sizes: [100, 400, 900, 1600] pixels
  Worker Counts: [1, 2, 4, 6, 8]
  Weak Scalability Base: 100 pixels/worker

=============================================================================
STRONG SCALABILITY TEST
=============================================================================
Fixed problem size with increasing number of workers
Ideal behavior: Speedup increases linearly (2x workers = 2x speedup)

--- Testing with 100 pixels ---
  Sequential baseline...
    Time: 2.345s
  2 workers...
    Time: 1.234s | Speedup: 1.90x | Efficiency: 95.0%
  4 workers...
    Time: 0.678s | Speedup: 3.46x | Efficiency: 86.5%
  ...
```

## Customization

Edit `benchmark.py` to change:

```python
# Test different problem sizes
strong_problem_sizes = [100, 400, 900, 1600]

# Test different worker counts
worker_counts = [1, 2, 4, 6, 8]

# Change weak scaling base size
weak_base_size = 100
```

## No Docker Required!

This benchmark runs standalone:
- ✅ No Docker needed
- ✅ No Django needed
- ✅ Just Python + your model files
- ✅ Generates mock reservoir data
- ✅ Clean, simple, fast
