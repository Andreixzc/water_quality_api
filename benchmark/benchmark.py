"""
Standalone Parallel Processing Benchmark
=========================================

No Docker or Django required! This script:
1. Generates mock reservoir data (n×n matrices)
2. Uses your ML model directly from files
3. Tests strong and weak scalability
4. Produces detailed reports and visualizations

Requirements:
- numpy
- pandas
- matplotlib
- scikit-learn
- joblib
"""

import os
import numpy as np
import time
import json
import pickle
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import matplotlib.pyplot as plt
import pandas as pd
import warnings

warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names, but StandardScaler was fitted with feature names",
    category=UserWarning
)

# For loading ML models
try:
    import joblib
    from sklearn.preprocessing import StandardScaler
except ImportError:
    print("Error: Please install required packages:")
    print("  pip install numpy pandas matplotlib scikit-learn joblib")
    exit(1)


class MockReservoirGenerator:
    """Generate realistic mock reservoir data"""
    
    @staticmethod
    def generate_pixels(n_pixels):
        """
        Generate n_pixels of mock reservoir data with realistic band values.
        
        Returns array of shape (n_pixels, 15) with:
        - 6 spectral bands (B2, B3, B4, B5, B8, B11)
        - 7 spectral indices (NDCI, NDVI, FAI, MNDWI, B3/B2, B4/B3, B5/B4)
        - 2 temporal features (month, season)
        """
        # Generate realistic Sentinel-2 band values (reflectance: 0-10000)
        B2 = np.random.uniform(500, 3000, n_pixels)   # Blue (492 nm)
        B3 = np.random.uniform(600, 3500, n_pixels)   # Green (560 nm)
        B4 = np.random.uniform(400, 3000, n_pixels)   # Red (665 nm)
        B5 = np.random.uniform(1000, 5000, n_pixels)  # Red Edge (704 nm)
        B8 = np.random.uniform(2000, 8000, n_pixels)  # NIR (833 nm)
        B11 = np.random.uniform(500, 4000, n_pixels)  # SWIR (1614 nm)
        
        # Calculate spectral indices
        NDCI = (B5 - B4) / (B5 + B4 + 1e-8)
        NDVI = (B8 - B4) / (B8 + B4 + 1e-8)
        FAI = B8 - (B4 + (B11 - B4) * (865 - 665) / (1610 - 665))
        MNDWI = (B3 - B11) / (B3 + B11 + 1e-8)
        B3_B2_ratio = B3 / (B2 + 1e-8)
        B4_B3_ratio = B4 / (B3 + 1e-8)
        B5_B4_ratio = B5 / (B4 + 1e-8)
        
        # Temporal features
        month = datetime.now().month
        season = (month % 12 + 3) // 3
        
        # Stack all features: shape (n_pixels, 15)
        features = np.column_stack([
            B2, B3, B4, B5, B8, B11,  # 6 bands
            NDCI, NDVI, FAI, MNDWI, B3_B2_ratio, B4_B3_ratio, B5_B4_ratio,  # 7 indices
            np.full(n_pixels, month),   # month
            np.full(n_pixels, season)   # season
        ])
        
        return features


class SimpleMLPredictor:
    """Simple ML predictor that loads model and scaler from files"""
    
    def __init__(self, model_path, scaler_path):
        """Load model and scaler from files"""
        # Load model (try joblib first, fallback to pickle)
        try:
            self.model = joblib.load(model_path)
        except:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
        
        # Load scaler (try joblib first, fallback to pickle)
        try:
            self.scaler = joblib.load(scaler_path)
        except:
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
    
    def predict_single(self, feature_vector):
        """Predict for a single pixel"""
        # Reshape for sklearn (expects 2D array)
        X = np.array(feature_vector).reshape(1, -1)
        
        # Scale and predict
        X_scaled = self.scaler.transform(X)
        prediction = self.model.predict(X_scaled)[0]
        
        return prediction
    
    def predict_batch(self, features):
        """Predict for multiple pixels at once"""
        X_scaled = self.scaler.transform(features)
        predictions = self.model.predict(X_scaled)
        return predictions


# Global worker function for multiprocessing
def _worker_predict_chunk(args):
    """
    Worker function for parallel processing.
    Must be at module level for pickling.
    """
    model_path, scaler_path, features, indices = args
    
    # Each process loads its own model copy
    predictor = SimpleMLPredictor(model_path, scaler_path)
    
    # Process chunk
    results = []
    for idx in indices:
        pred = predictor.predict_single(features[idx])
        results.append((idx, pred))
    
    return results


class ParallelBenchmark:
    """Benchmark parallel vs sequential processing"""
    
    def __init__(self, model_path, scaler_path):
        self.model_path = model_path
        self.scaler_path = scaler_path
    
    def run_sequential(self, features):
        """Run predictions sequentially (baseline)"""
        predictor = SimpleMLPredictor(self.model_path, self.scaler_path)
        
        start_time = time.time()
        predictions = []
        
        for i in range(len(features)):
            prediction = predictor.predict_single(features[i])
            predictions.append(prediction)
        
        end_time = time.time()
        
        return {
            'predictions': predictions,
            'execution_time': end_time - start_time,
            'n_predictions': len(predictions)
        }
    
    def run_parallel(self, features, n_workers):
        """Run predictions in parallel using multiprocessing"""
        start_time = time.time()
        predictions = [None] * len(features)  # Preserve order
        
        # Split work into chunks
        chunk_size = max(1, len(features) // n_workers)
        chunks = []
        for i in range(0, len(features), chunk_size):
            indices = list(range(i, min(i + chunk_size, len(features))))
            chunks.append((self.model_path, self.scaler_path, features, indices))
        
        # Process in parallel using processes (not threads)
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            futures = [executor.submit(_worker_predict_chunk, chunk) for chunk in chunks]
            
            for future in as_completed(futures):
                results = future.result()
                for idx, pred in results:
                    predictions[idx] = pred
        
        end_time = time.time()
        
        return {
            'predictions': predictions,
            'execution_time': end_time - start_time,
            'n_predictions': len(predictions),
            'n_workers': n_workers
        }
    
    def strong_scalability_test(self, problem_sizes, worker_counts):
        """
        Strong Scalability: Fixed problem size, varying workers
        Ideal: Linear speedup with more workers
        """
        print("\n" + "="*80)
        print("STRONG SCALABILITY TEST")
        print("="*80)
        print("Fixed problem size with increasing number of workers")
        print("Ideal behavior: Speedup increases linearly (2x workers = 2x speedup)\n")
        
        results = []
        
        for problem_size in problem_sizes:
            print(f"\n--- Testing with {problem_size} pixels ---")
            
            # Generate mock data
            features = MockReservoirGenerator.generate_pixels(problem_size)
            
            # Sequential baseline
            print(f"  Sequential baseline...")
            seq_result = self.run_sequential(features)
            seq_time = seq_result['execution_time']
            print(f"    Time: {seq_time:.3f}s")
            
            # Test with different worker counts
            for n_workers in worker_counts:
                print(f"  {n_workers} workers...")
                par_result = self.run_parallel(features, n_workers)
                par_time = par_result['execution_time']
                speedup = seq_time / par_time
                efficiency = speedup / n_workers
                
                print(f"    Time: {par_time:.3f}s | Speedup: {speedup:.2f}x | Efficiency: {efficiency:.1%}")
                
                results.append({
                    'test_type': 'strong',
                    'problem_size': problem_size,
                    'n_workers': n_workers,
                    'sequential_time': seq_time,
                    'parallel_time': par_time,
                    'speedup': speedup,
                    'efficiency': efficiency
                })
        
        return results
    
    def weak_scalability_test(self, base_size, worker_counts):
        """
        Weak Scalability: Problem size scales with workers
        Ideal: Constant execution time
        """
        print("\n" + "="*80)
        print("WEAK SCALABILITY TEST")
        print("="*80)
        print("Problem size increases proportionally with workers")
        print("Ideal behavior: Execution time remains constant\n")
        
        results = []
        
        # Baseline with 1 worker
        print(f"\n--- Baseline: {base_size} pixels, 1 worker ---")
        features = MockReservoirGenerator.generate_pixels(base_size)
        
        print(f"  Sequential baseline...")
        seq_result = self.run_sequential(features)
        baseline_time = seq_result['execution_time']
        print(f"    Time: {baseline_time:.3f}s")
        
        results.append({
            'test_type': 'weak',
            'problem_size': base_size,
            'n_workers': 1,
            'sequential_time': baseline_time,
            'parallel_time': baseline_time,
            'speedup': 1.0,
            'efficiency': 1.0
        })
        
        # Scale problem with workers
        for n_workers in worker_counts[1:]:
            problem_size = base_size * n_workers
            print(f"\n--- Testing: {problem_size} pixels, {n_workers} workers ---")
            
            features = MockReservoirGenerator.generate_pixels(problem_size)
            
            par_result = self.run_parallel(features, n_workers)
            par_time = par_result['execution_time']
            speedup = baseline_time / par_time
            efficiency = speedup / n_workers
            
            print(f"    Time: {par_time:.3f}s | vs Baseline: {par_time/baseline_time:.2f}x | Efficiency: {efficiency:.1%}")
            
            results.append({
                'test_type': 'weak',
                'problem_size': problem_size,
                'n_workers': n_workers,
                'sequential_time': baseline_time,
                'parallel_time': par_time,
                'speedup': speedup,
                'efficiency': efficiency
            })
        
        return results


def plot_results(strong_results, weak_results, output_dir='results'):
    """Generate visualization plots"""
    os.makedirs(output_dir, exist_ok=True)
    
    df_strong = pd.DataFrame(strong_results)
    df_weak = pd.DataFrame(weak_results)
    
    # === STRONG SCALABILITY PLOTS ===
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Strong Scalability Analysis (Fixed Workload)', fontsize=16, fontweight='bold')
    
    # Execution Time
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[0, 0].plot(data['n_workers'], data['parallel_time'], 
                       marker='o', linewidth=2, label=f'{problem_size} pixels')
    axes[0, 0].set_xlabel('Number of Workers', fontsize=12)
    axes[0, 0].set_ylabel('Execution Time (seconds)', fontsize=12)
    axes[0, 0].set_title('Execution Time vs Workers', fontsize=14)
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Speedup
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[0, 1].plot(data['n_workers'], data['speedup'], 
                       marker='o', linewidth=2, label=f'{problem_size} pixels')
    max_workers = df_strong['n_workers'].max()
    axes[0, 1].plot([1, max_workers], [1, max_workers], 
                   'k--', linewidth=2, label='Ideal Linear', alpha=0.6)
    axes[0, 1].set_xlabel('Number of Workers', fontsize=12)
    axes[0, 1].set_ylabel('Speedup', fontsize=12)
    axes[0, 1].set_title('Speedup vs Workers', fontsize=14)
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Efficiency
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[1, 0].plot(data['n_workers'], data['efficiency'], 
                       marker='o', linewidth=2, label=f'{problem_size} pixels')
    axes[1, 0].axhline(y=1.0, color='k', linestyle='--', 
                      linewidth=2, label='Ideal (100%)', alpha=0.6)
    axes[1, 0].set_xlabel('Number of Workers', fontsize=12)
    axes[1, 0].set_ylabel('Efficiency', fontsize=12)
    axes[1, 0].set_title('Parallel Efficiency', fontsize=14)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Speedup Bar Chart (largest problem)
    largest = df_strong['problem_size'].max()
    data = df_strong[df_strong['problem_size'] == largest]
    x = np.arange(len(data))
    width = 0.35
    axes[1, 1].bar(x - width/2, data['speedup'], width, 
                  label='Actual', alpha=0.8, color='steelblue')
    axes[1, 1].bar(x + width/2, data['n_workers'], width, 
                  label='Ideal', alpha=0.8, color='coral')
    axes[1, 1].set_xlabel('Number of Workers', fontsize=12)
    axes[1, 1].set_ylabel('Speedup', fontsize=12)
    axes[1, 1].set_title(f'Speedup Comparison ({largest} pixels)', fontsize=14)
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(data['n_workers'])
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/strong_scalability.png', dpi=300, bbox_inches='tight')
    print(f"  ✓ {output_dir}/strong_scalability.png")
    plt.close()
    
    # === WEAK SCALABILITY PLOTS ===
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Weak Scalability Analysis (Scaled Workload)', fontsize=16, fontweight='bold')
    
    # Execution Time
    axes[0, 0].plot(df_weak['n_workers'], df_weak['parallel_time'], 
                   marker='o', linewidth=2, markersize=8, color='steelblue')
    axes[0, 0].axhline(y=df_weak['parallel_time'].iloc[0], color='r', 
                      linestyle='--', linewidth=2, label='Ideal (constant)', alpha=0.6)
    axes[0, 0].set_xlabel('Number of Workers', fontsize=12)
    axes[0, 0].set_ylabel('Execution Time (seconds)', fontsize=12)
    axes[0, 0].set_title('Execution Time (Scaled Problem)', fontsize=14)
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Problem Size Scaling
    axes[0, 1].plot(df_weak['n_workers'], df_weak['problem_size'], 
                   marker='s', linewidth=2, markersize=8, color='green')
    axes[0, 1].set_xlabel('Number of Workers', fontsize=12)
    axes[0, 1].set_ylabel('Problem Size (pixels)', fontsize=12)
    axes[0, 1].set_title('Problem Size Scaling', fontsize=14)
    axes[0, 1].grid(True, alpha=0.3)
    
    # Efficiency
    axes[1, 0].plot(df_weak['n_workers'], df_weak['efficiency'], 
                   marker='o', linewidth=2, markersize=8, color='steelblue')
    axes[1, 0].axhline(y=1.0, color='k', linestyle='--', 
                      linewidth=2, label='Ideal (100%)', alpha=0.6)
    axes[1, 0].set_xlabel('Number of Workers', fontsize=12)
    axes[1, 0].set_ylabel('Efficiency', fontsize=12)
    axes[1, 0].set_title('Parallel Efficiency', fontsize=14)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Relative Time
    baseline = df_weak['parallel_time'].iloc[0]
    relative = df_weak['parallel_time'] / baseline
    axes[1, 1].bar(range(len(df_weak)), relative, alpha=0.8, color='steelblue')
    axes[1, 1].axhline(y=1.0, color='r', linestyle='--', 
                      linewidth=2, label='Ideal (1.0x)', alpha=0.6)
    axes[1, 1].set_xticks(range(len(df_weak)))
    axes[1, 1].set_xticklabels(df_weak['n_workers'])
    axes[1, 1].set_xlabel('Number of Workers', fontsize=12)
    axes[1, 1].set_ylabel('Time Relative to Baseline', fontsize=12)
    axes[1, 1].set_title('Normalized Execution Time', fontsize=14)
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/weak_scalability.png', dpi=300, bbox_inches='tight')
    print(f"  ✓ {output_dir}/weak_scalability.png")
    plt.close()


def save_results(strong_results, weak_results, output_dir='results'):
    """Save results to files"""
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nSaving results:")
    
    # CSV files
    pd.DataFrame(strong_results).to_csv(f'{output_dir}/strong_scalability.csv', index=False)
    print(f"  ✓ {output_dir}/strong_scalability.csv")
    
    pd.DataFrame(weak_results).to_csv(f'{output_dir}/weak_scalability.csv', index=False)
    print(f"  ✓ {output_dir}/weak_scalability.csv")
    
    # JSON file
    with open(f'{output_dir}/benchmark_results.json', 'w') as f:
        json.dump({
            'strong_scalability': strong_results,
            'weak_scalability': weak_results,
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'cpu_count': os.cpu_count()
            }
        }, f, indent=2)
    print(f"  ✓ {output_dir}/benchmark_results.json")
    
    # Generate report
    generate_report(strong_results, weak_results, output_dir)


def generate_report(strong_results, weak_results, output_dir):
    """Generate markdown report"""
    df_strong = pd.DataFrame(strong_results)
    df_weak = pd.DataFrame(weak_results)
    
    with open(f'{output_dir}/BENCHMARK_REPORT.md', 'w') as f:
        f.write("# Parallel Processing Benchmark Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**CPU Cores:** {os.cpu_count()}\n\n")
        f.write(f"**Parallelization Method:** ProcessPoolExecutor (multiprocessing)\n\n")
        
        f.write("## Strong Scalability\n\n")
        f.write("Fixed problem size with varying workers.\n\n")
        
        for size in df_strong['problem_size'].unique():
            data = df_strong[df_strong['problem_size'] == size]
            f.write(f"### {size} Pixels\n\n")
            f.write("| Workers | Time (s) | Speedup | Efficiency |\n")
            f.write("|--------:|----------:|--------:|-----------:|\n")
            for _, row in data.iterrows():
                f.write(f"| {row['n_workers']} | {row['parallel_time']:.3f} | "
                       f"{row['speedup']:.2f}x | {row['efficiency']:.1%} |\n")
            f.write("\n")
        
        f.write("## Weak Scalability\n\n")
        f.write("Problem size scales with workers.\n\n")
        f.write("| Workers | Pixels | Time (s) | vs Baseline | Efficiency |\n")
        f.write("|--------:|--------:|----------:|------------:|-----------:|\n")
        
        baseline = df_weak['parallel_time'].iloc[0]
        for _, row in df_weak.iterrows():
            f.write(f"| {row['n_workers']} | {row['problem_size']} | "
                   f"{row['parallel_time']:.3f} | "
                   f"{row['parallel_time']/baseline:.2f}x | "
                   f"{row['efficiency']:.1%} |\n")
        
        f.write("\n## Summary\n\n")
        max_speedup = df_strong.groupby('problem_size')['speedup'].max().max()
        max_efficiency = df_strong['efficiency'].max()
        avg_weak_efficiency = df_weak['efficiency'].mean()
        
        f.write(f"- **Maximum Speedup:** {max_speedup:.2f}x\n")
        f.write(f"- **Best Efficiency:** {max_efficiency:.1%}\n")
        f.write(f"- **Avg Weak Scaling Efficiency:** {avg_weak_efficiency:.1%}\n")
        
        f.write("\n## Notes\n\n")
        f.write("- Uses `ProcessPoolExecutor` to bypass Python's GIL\n")
        f.write("- Each process loads its own copy of the ML model\n")
        f.write("- Ideal speedup = number of workers (linear scaling)\n")
        f.write("- Ideal efficiency = 100% (maintains full utilization)\n")
    
    print(f"  ✓ {output_dir}/BENCHMARK_REPORT.md")


def main():
    """Run the benchmark"""
    print("="*80)
    print("PARALLEL PROCESSING BENCHMARK")
    print("Water Quality Prediction - Scalability Analysis")
    print("="*80)
    
    # Configuration
    model_path = 'models/model.joblib'
    scaler_path = 'models/scaler.joblib'
    
    # Try .pkl fallback if .joblib doesn't exist
    if not os.path.exists(model_path):
        model_path = 'models/model.pkl'
    if not os.path.exists(scaler_path):
        scaler_path = 'models/scaler.pkl'
    
    # Check if model files exist
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        print("\nError: Model files not found!")
        print(f"Please download model files first:")
        print(f"  ./download_models.sh")
        print(f"\nExpected files:")
        print(f"  - models/model.joblib (or model.pkl)")
        print(f"  - models/scaler.joblib (or scaler.pkl)")
        return
    
    # Test configuration
    strong_problem_sizes = [100, 400, 900, 1600]  # 10x10, 20x20, 30x30, 40x40
    worker_counts = [1, 2, 4, 6, 8]
    weak_base_size = 100  # 100 pixels per worker
    
    print(f"\nConfiguration:")
    print(f"  CPU Cores: {os.cpu_count()}")
    print(f"  Parallelization: ProcessPoolExecutor (multiprocessing)")
    print(f"  Strong Scalability Sizes: {strong_problem_sizes} pixels")
    print(f"  Worker Counts: {worker_counts}")
    print(f"  Weak Scalability Base: {weak_base_size} pixels/worker")
    
    # Run benchmark
    benchmark = ParallelBenchmark(model_path, scaler_path)
    
    strong_results = benchmark.strong_scalability_test(strong_problem_sizes, worker_counts)
    weak_results = benchmark.weak_scalability_test(weak_base_size, worker_counts)
    
    # Save and visualize
    print("\nGenerating visualizations:")
    save_results(strong_results, weak_results)
    plot_results(strong_results, weak_results)
    
    print("\n" + "="*80)
    print("BENCHMARK COMPLETE!")
    print("="*80)
    print("\nResults saved to: ./results/")
    print("\nKey changes from original:")
    print("  ✓ Uses ProcessPoolExecutor instead of ThreadPoolExecutor")
    print("  ✓ Bypasses Python's GIL for true parallel CPU processing")
    print("  ✓ Each process loads its own model copy")


if __name__ == '__main__':
    main()