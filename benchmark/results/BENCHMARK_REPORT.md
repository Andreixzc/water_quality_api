# Parallel Processing Benchmark Report

**Date:** 2025-10-16 23:54:59

**CPU Cores:** 12

**Parallelization Method:** ProcessPoolExecutor (multiprocessing)

## Strong Scalability

Fixed problem size with varying workers.

### 100 Pixels

| Workers | Time (s) | Speedup | Efficiency |
|--------:|----------:|--------:|-----------:|
| 1 | 0.366 | 0.97x | 97.1% |
| 2 | 0.222 | 1.60x | 80.2% |
| 4 | 0.166 | 2.14x | 53.5% |
| 6 | 0.144 | 2.47x | 41.1% |
| 8 | 0.164 | 2.17x | 27.2% |

### 400 Pixels

| Workers | Time (s) | Speedup | Efficiency |
|--------:|----------:|--------:|-----------:|
| 1 | 1.459 | 0.99x | 98.8% |
| 2 | 0.872 | 1.65x | 82.6% |
| 4 | 0.482 | 2.99x | 74.7% |
| 6 | 0.369 | 3.91x | 65.2% |
| 8 | 0.365 | 3.95x | 49.4% |

### 900 Pixels

| Workers | Time (s) | Speedup | Efficiency |
|--------:|----------:|--------:|-----------:|
| 1 | 3.424 | 0.89x | 89.1% |
| 2 | 1.601 | 1.90x | 95.2% |
| 4 | 0.932 | 3.27x | 81.8% |
| 6 | 0.704 | 4.33x | 72.2% |
| 8 | 0.781 | 3.91x | 48.8% |

### 1600 Pixels

| Workers | Time (s) | Speedup | Efficiency |
|--------:|----------:|--------:|-----------:|
| 1 | 6.690 | 0.82x | 81.8% |
| 2 | 2.964 | 1.85x | 92.3% |
| 4 | 1.678 | 3.26x | 81.5% |
| 6 | 1.445 | 3.78x | 63.1% |
| 8 | 1.374 | 3.98x | 49.8% |

## Weak Scalability

Problem size scales with workers.

| Workers | Pixels | Time (s) | vs Baseline | Efficiency |
|--------:|--------:|----------:|------------:|-----------:|
| 1 | 100 | 0.507 | 1.00x | 100.0% |
| 2 | 200 | 0.439 | 0.87x | 57.8% |
| 4 | 400 | 0.548 | 1.08x | 23.1% |
| 6 | 600 | 0.651 | 1.28x | 13.0% |
| 8 | 800 | 0.667 | 1.32x | 9.5% |

## Summary

- **Maximum Speedup:** 4.33x
- **Best Efficiency:** 98.8%
- **Avg Weak Scaling Efficiency:** 40.7%

## Notes

- Uses `ProcessPoolExecutor` to bypass Python's GIL
- Each process loads its own copy of the ML model
- Ideal speedup = number of workers (linear scaling)
- Ideal efficiency = 100% (maintains full utilization)
