"""
Parallel Processing Benchmark for Water Quality Prediction
===========================================================

This script evaluates the parallel computing implementation by testing:
1. Strong Scalability: Fixed problem size, varying number of workers
2. Weak Scalability: Proportional problem size increase with workers

Metrics:
- Execution Time (seconds)
- Speedup (Sequential Time / Parallel Time)
- Efficiency (Speedup / Number of Workers)
"""

import os
import sys
import django
import numpy as np
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import pandas as pd

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_quality_project.settings')
django.setup()

from processing.services.ml_processor import WaterQualityPredictor
from api.models.machine_learning_model import MachineLearningModel


class ReservoirDataGenerator:
    """Generate mock reservoir data for benchmarking"""
    
    @staticmethod
    def generate_reservoir_matrix(n_rows, n_cols):
        """
        Generate an n×n matrix simulating a reservoir with realistic band values.
        
        Each pixel contains:
        - 6 spectral bands (B2, B3, B4, B5, B8, B11)
        - 7 spectral indices (NDCI, NDVI, FAI, MNDWI, B3/B2, B4/B3, B5/B4)
        - 2 temporal features (month, season)
        
        Total: 15 features per pixel
        """
        n_pixels = n_rows * n_cols
        
        # Generate realistic band values (reflectance values typically 0-10000)
        B2 = np.random.uniform(500, 3000, n_pixels)   # Blue
        B3 = np.random.uniform(600, 3500, n_pixels)   # Green
        B4 = np.random.uniform(400, 3000, n_pixels)   # Red
        B5 = np.random.uniform(1000, 5000, n_pixels)  # Red Edge
        B8 = np.random.uniform(2000, 8000, n_pixels)  # NIR
        B11 = np.random.uniform(500, 4000, n_pixels)  # SWIR
        
        # Calculate spectral indices
        NDCI = (B5 - B4) / (B5 + B4 + 1e-8)
        NDVI = (B8 - B4) / (B8 + B4 + 1e-8)
        FAI = B8 - (B4 + (B11 - B4) * (865 - 665) / (1610 - 665))
        MNDWI = (B3 - B11) / (B3 + B11 + 1e-8)
        B3_B2_ratio = B3 / (B2 + 1e-8)
        B4_B3_ratio = B4 / (B3 + 1e-8)
        B5_B4_ratio = B5 / (B4 + 1e-8)
        
        # Temporal features (use current month/season)
        month = datetime.now().month
        season = (month % 12 + 3) // 3
        
        # Combine all features into matrix
        features = np.column_stack([
            B2, B3, B4, B5, B8, B11,  # Bands
            NDCI, NDVI, FAI, MNDWI, B3_B2_ratio, B4_B3_ratio, B5_B4_ratio,  # Indices
            np.full(n_pixels, month),  # Month
            np.full(n_pixels, season)  # Season
        ])
        
        return features
    
    @staticmethod
    def features_to_geojson_format(features):
        """Convert feature matrix to GeoJSON-like format for compatibility"""
        geojson_features = []
        for i, row in enumerate(features):
            feature = {
                'properties': {
                    'B2': float(row[0]),
                    'B3': float(row[1]),
                    'B4': float(row[2]),
                    'B5': float(row[3]),
                    'B8': float(row[4]),
                    'B11': float(row[5]),
                    'NDCI': float(row[6]),
                    'NDVI': float(row[7]),
                    'FAI': float(row[8]),
                    'MNDWI': float(row[9]),
                    'B3_B2_ratio': float(row[10]),
                    'B4_B3_ratio': float(row[11]),
                    'B5_B4_ratio': float(row[12]),
                },
                'geometry': {
                    'coordinates': [i % 100, i // 100]  # Mock lat/lon
                }
            }
            geojson_features.append(feature)
        return {'features': geojson_features}


class ParallelBenchmark:
    """Benchmark parallel processing performance"""
    
    def __init__(self):
        # Load the first available ML model
        self.model = MachineLearningModel.objects.first()
        if not self.model:
            raise Exception("No ML model found in database!")
        
        print(f"Using model: {self.model.parameter.name} (ID: {self.model.id})")
    
    def process_feature_sequential(self, predictor, feature):
        """Process a single feature (for sequential baseline)"""
        feature_vector = [
            feature['properties']['B2'],
            feature['properties']['B3'],
            feature['properties']['B4'],
            feature['properties']['B5'],
            feature['properties']['B8'],
            feature['properties']['B11'],
            feature['properties']['NDCI'],
            feature['properties']['NDVI'],
            feature['properties']['FAI'],
            feature['properties']['MNDWI'],
            feature['properties']['B3_B2_ratio'],
            feature['properties']['B4_B3_ratio'],
            feature['properties']['B5_B4_ratio'],
            datetime.now().month,
            (datetime.now().month % 12 + 3) // 3
        ]
        return predictor.predict_single_pixel(feature_vector)
    
    def run_sequential(self, features):
        """Run predictions sequentially (baseline)"""
        predictor = WaterQualityPredictor(
            self.model.model_file,
            self.model.scaler_file,
            use_parallel=False,
            max_workers=1
        )
        
        start_time = time.time()
        predictions = []
        
        for feature in features['features']:
            prediction = self.process_feature_sequential(predictor, feature)
            predictions.append(prediction)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            'predictions': predictions,
            'execution_time': execution_time,
            'n_predictions': len(predictions)
        }
    
    def run_parallel(self, features, n_workers):
        """Run predictions in parallel with specified number of workers"""
        predictor = WaterQualityPredictor(
            self.model.model_file,
            self.model.scaler_file,
            use_parallel=True,
            max_workers=n_workers
        )
        
        start_time = time.time()
        predictions = []
        
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            future_to_feature = {
                executor.submit(self.process_feature_sequential, predictor, feature): feature
                for feature in features['features']
            }
            
            for future in as_completed(future_to_feature):
                try:
                    prediction = future.result()
                    predictions.append(prediction)
                except Exception as exc:
                    print(f"Feature generated exception: {exc}")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        return {
            'predictions': predictions,
            'execution_time': execution_time,
            'n_predictions': len(predictions),
            'n_workers': n_workers
        }
    
    def strong_scalability_test(self, problem_sizes, worker_counts):
        """
        Strong Scalability Test: Fixed problem size, varying workers
        
        Tests how well the system scales when adding more workers to the same problem.
        Ideal: Linear speedup (2x workers = 2x speedup)
        """
        print("\n" + "="*80)
        print("STRONG SCALABILITY TEST")
        print("="*80)
        print("Testing: Fixed problem size with varying number of workers")
        print("Ideal behavior: Speedup increases linearly with workers\n")
        
        results = []
        
        for problem_size in problem_sizes:
            print(f"\n--- Problem Size: {problem_size} pixels ---")
            
            # Generate data
            n = int(np.sqrt(problem_size))
            features_matrix = ReservoirDataGenerator.generate_reservoir_matrix(n, n)
            features = ReservoirDataGenerator.features_to_geojson_format(features_matrix)
            
            # Sequential baseline
            print(f"  Running sequential baseline...")
            seq_result = self.run_sequential(features)
            seq_time = seq_result['execution_time']
            print(f"  Sequential time: {seq_time:.3f}s")
            
            # Test with different worker counts
            for n_workers in worker_counts:
                print(f"  Testing with {n_workers} workers...")
                par_result = self.run_parallel(features, n_workers)
                par_time = par_result['execution_time']
                speedup = seq_time / par_time
                efficiency = speedup / n_workers
                
                print(f"    Parallel time: {par_time:.3f}s | Speedup: {speedup:.2f}x | Efficiency: {efficiency:.2%}")
                
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
        Weak Scalability Test: Problem size increases proportionally with workers
        
        Tests how well the system maintains performance when both workload and resources scale.
        Ideal: Constant execution time (more workers handle proportionally more work)
        """
        print("\n" + "="*80)
        print("WEAK SCALABILITY TEST")
        print("="*80)
        print("Testing: Problem size increases proportionally with workers")
        print("Ideal behavior: Execution time remains constant\n")
        
        results = []
        
        # Sequential baseline with base size
        print(f"\n--- Baseline: {base_size} pixels with 1 worker ---")
        n = int(np.sqrt(base_size))
        features_matrix = ReservoirDataGenerator.generate_reservoir_matrix(n, n)
        features = ReservoirDataGenerator.features_to_geojson_format(features_matrix)
        
        print(f"  Running sequential baseline...")
        seq_result = self.run_sequential(features)
        baseline_time = seq_result['execution_time']
        print(f"  Baseline time: {baseline_time:.3f}s")
        
        results.append({
            'test_type': 'weak',
            'problem_size': base_size,
            'n_workers': 1,
            'sequential_time': baseline_time,
            'parallel_time': baseline_time,
            'speedup': 1.0,
            'efficiency': 1.0
        })
        
        # Test with proportionally larger problems
        for n_workers in worker_counts[1:]:  # Skip 1 worker (already tested)
            problem_size = base_size * n_workers
            print(f"\n--- Testing: {problem_size} pixels with {n_workers} workers ---")
            
            n = int(np.sqrt(problem_size))
            features_matrix = ReservoirDataGenerator.generate_reservoir_matrix(n, n)
            features = ReservoirDataGenerator.features_to_geojson_format(features_matrix)
            
            par_result = self.run_parallel(features, n_workers)
            par_time = par_result['execution_time']
            speedup = baseline_time / par_time
            efficiency = speedup / n_workers
            
            print(f"  Parallel time: {par_time:.3f}s | vs Baseline: {par_time/baseline_time:.2f}x | Efficiency: {efficiency:.2%}")
            
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


def plot_results(strong_results, weak_results, output_dir='benchmark_results'):
    """Generate visualization plots for benchmark results"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert to DataFrames
    df_strong = pd.DataFrame(strong_results)
    df_weak = pd.DataFrame(weak_results)
    
    # Strong Scalability Plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Strong Scalability Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Execution Time vs Workers
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[0, 0].plot(data['n_workers'], data['parallel_time'], marker='o', label=f'{problem_size} pixels')
    axes[0, 0].set_xlabel('Number of Workers')
    axes[0, 0].set_ylabel('Execution Time (seconds)')
    axes[0, 0].set_title('Execution Time vs Number of Workers')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Speedup vs Workers
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[0, 1].plot(data['n_workers'], data['speedup'], marker='o', label=f'{problem_size} pixels')
    # Add ideal linear speedup
    max_workers = df_strong['n_workers'].max()
    axes[0, 1].plot([1, max_workers], [1, max_workers], 'k--', label='Ideal Linear', alpha=0.5)
    axes[0, 1].set_xlabel('Number of Workers')
    axes[0, 1].set_ylabel('Speedup')
    axes[0, 1].set_title('Speedup vs Number of Workers')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Efficiency vs Workers
    for problem_size in df_strong['problem_size'].unique():
        data = df_strong[df_strong['problem_size'] == problem_size]
        axes[1, 0].plot(data['n_workers'], data['efficiency'], marker='o', label=f'{problem_size} pixels')
    axes[1, 0].axhline(y=1.0, color='k', linestyle='--', label='Ideal (100%)', alpha=0.5)
    axes[1, 0].set_xlabel('Number of Workers')
    axes[1, 0].set_ylabel('Efficiency')
    axes[1, 0].set_title('Parallel Efficiency vs Number of Workers')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Speedup comparison for largest problem
    largest_problem = df_strong['problem_size'].max()
    data = df_strong[df_strong['problem_size'] == largest_problem]
    x = range(len(data))
    axes[1, 1].bar(x, data['speedup'], alpha=0.7, label='Actual Speedup')
    axes[1, 1].plot(x, data['n_workers'], 'r--', marker='o', label='Ideal Speedup')
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(data['n_workers'])
    axes[1, 1].set_xlabel('Number of Workers')
    axes[1, 1].set_ylabel('Speedup')
    axes[1, 1].set_title(f'Speedup Comparison ({largest_problem} pixels)')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/strong_scalability.png', dpi=300, bbox_inches='tight')
    print(f"\nStrong scalability plot saved to: {output_dir}/strong_scalability.png")
    
    # Weak Scalability Plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Weak Scalability Analysis', fontsize=16, fontweight='bold')
    
    # Plot 1: Execution Time vs Workers (with problem size)
    axes[0, 0].plot(df_weak['n_workers'], df_weak['parallel_time'], marker='o', linewidth=2)
    axes[0, 0].axhline(y=df_weak['parallel_time'].iloc[0], color='r', linestyle='--', 
                       label='Ideal (constant time)', alpha=0.5)
    axes[0, 0].set_xlabel('Number of Workers')
    axes[0, 0].set_ylabel('Execution Time (seconds)')
    axes[0, 0].set_title('Execution Time vs Workers (Proportional Problem Size)')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Plot 2: Problem Size vs Workers
    axes[0, 1].plot(df_weak['n_workers'], df_weak['problem_size'], marker='s', linewidth=2, color='green')
    axes[0, 1].set_xlabel('Number of Workers')
    axes[0, 1].set_ylabel('Problem Size (pixels)')
    axes[0, 1].set_title('Problem Size Scaling')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Plot 3: Efficiency vs Workers
    axes[1, 0].plot(df_weak['n_workers'], df_weak['efficiency'], marker='o', linewidth=2)
    axes[1, 0].axhline(y=1.0, color='k', linestyle='--', label='Ideal (100%)', alpha=0.5)
    axes[1, 0].set_xlabel('Number of Workers')
    axes[1, 0].set_ylabel('Efficiency')
    axes[1, 0].set_title('Parallel Efficiency (Weak Scaling)')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Time relative to baseline
    baseline = df_weak['parallel_time'].iloc[0]
    relative_time = df_weak['parallel_time'] / baseline
    axes[1, 1].bar(range(len(df_weak)), relative_time, alpha=0.7)
    axes[1, 1].axhline(y=1.0, color='r', linestyle='--', label='Ideal (1.0x)', alpha=0.5)
    axes[1, 1].set_xticks(range(len(df_weak)))
    axes[1, 1].set_xticklabels(df_weak['n_workers'])
    axes[1, 1].set_xlabel('Number of Workers')
    axes[1, 1].set_ylabel('Time Relative to Baseline')
    axes[1, 1].set_title('Execution Time Relative to Baseline')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/weak_scalability.png', dpi=300, bbox_inches='tight')
    print(f"Weak scalability plot saved to: {output_dir}/weak_scalability.png")


def save_results(strong_results, weak_results, output_dir='benchmark_results'):
    """Save benchmark results to CSV and JSON files"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as CSV
    df_strong = pd.DataFrame(strong_results)
    df_weak = pd.DataFrame(weak_results)
    
    df_strong.to_csv(f'{output_dir}/strong_scalability_results.csv', index=False)
    df_weak.to_csv(f'{output_dir}/weak_scalability_results.csv', index=False)
    
    print(f"\nResults saved to:")
    print(f"  - {output_dir}/strong_scalability_results.csv")
    print(f"  - {output_dir}/weak_scalability_results.csv")
    
    # Save as JSON
    with open(f'{output_dir}/benchmark_results.json', 'w') as f:
        json.dump({
            'strong_scalability': strong_results,
            'weak_scalability': weak_results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"  - {output_dir}/benchmark_results.json")
    
    # Generate summary report
    generate_summary_report(df_strong, df_weak, output_dir)


def generate_summary_report(df_strong, df_weak, output_dir):
    """Generate a text summary report"""
    with open(f'{output_dir}/BENCHMARK_REPORT.md', 'w') as f:
        f.write("# Parallel Processing Benchmark Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Strong Scalability Results\n\n")
        f.write("Fixed problem size with varying number of workers.\n\n")
        
        for problem_size in df_strong['problem_size'].unique():
            data = df_strong[df_strong['problem_size'] == problem_size]
            f.write(f"### Problem Size: {problem_size} pixels\n\n")
            f.write("| Workers | Time (s) | Speedup | Efficiency |\n")
            f.write("|---------|----------|---------|------------|\n")
            
            for _, row in data.iterrows():
                f.write(f"| {row['n_workers']} | {row['parallel_time']:.3f} | "
                       f"{row['speedup']:.2f}x | {row['efficiency']:.1%} |\n")
            f.write("\n")
        
        f.write("## Weak Scalability Results\n\n")
        f.write("Problem size increases proportionally with workers.\n\n")
        f.write("| Workers | Problem Size | Time (s) | vs Baseline | Efficiency |\n")
        f.write("|---------|--------------|----------|-------------|------------|\n")
        
        baseline_time = df_weak['parallel_time'].iloc[0]
        for _, row in df_weak.iterrows():
            f.write(f"| {row['n_workers']} | {row['problem_size']} | "
                   f"{row['parallel_time']:.3f} | "
                   f"{row['parallel_time']/baseline_time:.2f}x | "
                   f"{row['efficiency']:.1%} |\n")
        
        f.write("\n## Key Findings\n\n")
        
        # Strong scalability findings
        max_speedup = df_strong.groupby('problem_size')['speedup'].max()
        f.write(f"### Strong Scalability\n")
        f.write(f"- Maximum speedup achieved: {max_speedup.max():.2f}x\n")
        f.write(f"- Best efficiency: {df_strong['efficiency'].max():.1%}\n\n")
        
        # Weak scalability findings
        f.write(f"### Weak Scalability\n")
        time_variation = df_weak['parallel_time'].std() / df_weak['parallel_time'].mean()
        f.write(f"- Time variation coefficient: {time_variation:.2%}\n")
        f.write(f"- Average efficiency: {df_weak['efficiency'].mean():.1%}\n")
    
    print(f"  - {output_dir}/BENCHMARK_REPORT.md")


def main():
    """Run comprehensive benchmark suite"""
    print("="*80)
    print("PARALLEL PROCESSING BENCHMARK SUITE")
    print("Water Quality Prediction - ML Model Performance")
    print("="*80)
    
    benchmark = ParallelBenchmark()
    
    # Test configurations
    # Strong scalability: Test with different problem sizes and worker counts
    strong_problem_sizes = [100, 400, 900]  # 10x10, 20x20, 30x30 matrices
    worker_counts = [1, 2, 4, 6, 8]
    
    # Weak scalability: Base size that scales with workers
    weak_base_size = 100  # 10x10 matrix per worker
    
    print(f"\nTest Configuration:")
    print(f"  Strong Scalability Problem Sizes: {strong_problem_sizes} pixels")
    print(f"  Worker Counts: {worker_counts}")
    print(f"  Weak Scalability Base Size: {weak_base_size} pixels/worker")
    
    # Run benchmarks
    strong_results = benchmark.strong_scalability_test(strong_problem_sizes, worker_counts)
    weak_results = benchmark.weak_scalability_test(weak_base_size, worker_counts)
    
    # Save and visualize results
    save_results(strong_results, weak_results)
    plot_results(strong_results, weak_results)
    
    print("\n" + "="*80)
    print("BENCHMARK COMPLETE!")
    print("="*80)
    print("\nCheck the 'benchmark_results' directory for:")
    print("  - CSV files with raw data")
    print("  - PNG plots visualizing scalability")
    print("  - Markdown report with summary")


if __name__ == '__main__':
    main()
