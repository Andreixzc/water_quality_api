"""
Performance comparison script for sequential vs parallel chunk processing
"""
import time
import numpy as np
import rasterio
from io import BytesIO
from processing.services.ml_processor import WaterQualityPredictor as SequentialPredictor
from processing.services.parallel_ml_processor import ParallelWaterQualityPredictor
import os

def create_synthetic_image(width=2000, height=2000, num_bands=6):
    """Create a synthetic satellite image for testing"""
    print(f"Creating synthetic image: {width}x{height} with {num_bands} bands")
    
    # Create synthetic data that mimics Sentinel-2 bands
    image_data = np.random.rand(num_bands, height, width).astype(np.float32)
    
    # Scale to realistic Sentinel-2 values (0-1 range after scaling by 10000)
    image_data = image_data * 0.3  # Keep values reasonable
    
    # Add some water-like areas (higher MNDWI values)
    water_areas = np.random.rand(height, width) > 0.7
    if num_bands >= 4:  # Ensure we have B3 and B11
        image_data[1][water_areas] = 0.15  # B3 higher
        image_data[5][water_areas] = 0.05  # B11 lower
    
    # Create in-memory GeoTIFF
    profile = {
        'driver': 'GTiff',
        'dtype': 'float32',
        'nodata': None,
        'width': width,
        'height': height,
        'count': num_bands,
        'crs': 'EPSG:4326',
        'transform': rasterio.transform.from_bounds(-1, -1, 1, 1, width, height),
        'tiled': True,
        'blockxsize': 512,
        'blockysize': 512
    }
    
    with rasterio.MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(image_data)
            # Add date metadata
            dst.update_tags(DATE_ACQUIRED='2024-06-15')
        
        return memfile.read()

def load_test_models():
    """Load or create test models for benchmarking"""
    # For testing, we'll create dummy models
    # In real usage, you'd load your actual trained models
    
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    
    # Create a simple model for testing
    model = RandomForestRegressor(n_estimators=10, random_state=42)  # Small for speed
    scaler = StandardScaler()
    
    # Create dummy training data
    n_features = 15  # 6 bands + 7 indices + 2 temporal
    dummy_X = np.random.rand(1000, n_features)
    dummy_y = np.random.rand(1000) * 100  # Random water quality values
    
    # Fit the models
    model.fit(dummy_X, dummy_y)
    scaler.fit(dummy_X)
    
    # Serialize to bytes
    model_buffer = BytesIO()
    scaler_buffer = BytesIO()
    
    joblib.dump(model, model_buffer)
    joblib.dump(scaler, scaler_buffer)
    
    return model_buffer.getvalue(), scaler_buffer.getvalue()

def benchmark_processing(image_data, model_data, scaler_data, 
                        image_size="2000x2000", max_workers_list=[1, 2, 4, 8]):
    """
    Benchmark both sequential and parallel processing
    
    Args:
        image_data: Synthetic image data
        model_data: Model binary data
        scaler_data: Scaler binary data
        image_size: Size description for logging
        max_workers_list: List of thread counts to test
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARKING CHUNK PROCESSING - {image_size}")
    print(f"{'='*60}")
    
    results = {}
    
    # Test original sequential processing
    print(f"\n1. Testing Sequential Processing...")
    start_time = time.time()
    
    try:
        sequential_predictor = SequentialPredictor(model_data, scaler_data)
        output_sequential = BytesIO()
        sequential_predictor.process_image(image_data, output_sequential)
        
        sequential_time = time.time() - start_time
        results['sequential'] = sequential_time
        
        print(f"   ✓ Sequential processing completed in {sequential_time:.2f} seconds")
        
    except Exception as e:
        print(f"   ✗ Sequential processing failed: {str(e)}")
        results['sequential'] = None
    
    # Test parallel processing with different thread counts
    for max_workers in max_workers_list:
        print(f"\n2. Testing Parallel Processing ({max_workers} threads)...")
        start_time = time.time()
        
        try:
            parallel_predictor = ParallelWaterQualityPredictor(
                model_data, scaler_data, max_workers=max_workers
            )
            output_parallel = BytesIO()
            parallel_predictor.process_image_parallel(image_data, output_parallel)
            
            parallel_time = time.time() - start_time
            results[f'parallel_{max_workers}'] = parallel_time
            
            # Calculate speedup
            if results['sequential']:
                speedup = results['sequential'] / parallel_time
                efficiency = speedup / max_workers * 100
                print(f"   ✓ Parallel processing ({max_workers} threads) completed in {parallel_time:.2f} seconds")
                print(f"   📈 Speedup: {speedup:.2f}x, Efficiency: {efficiency:.1f}%")
            else:
                print(f"   ✓ Parallel processing ({max_workers} threads) completed in {parallel_time:.2f} seconds")
                
        except Exception as e:
            print(f"   ✗ Parallel processing ({max_workers} threads) failed: {str(e)}")
            results[f'parallel_{max_workers}'] = None
    
    return results

def run_comprehensive_benchmark():
    """Run comprehensive benchmarks with different image sizes"""
    print("🚀 Starting Comprehensive Chunk Processing Benchmark")
    print(f"CPU Count: {os.cpu_count()}")
    
    # Load test models
    print("\n📦 Loading test models...")
    model_data, scaler_data = load_test_models()
    print(f"✓ Models loaded (Model: {len(model_data)} bytes, Scaler: {len(scaler_data)} bytes)")
    
    # Test different image sizes
    test_configs = [
        {'width': 1000, 'height': 1000, 'name': '1000x1000'},
        {'width': 2000, 'height': 2000, 'name': '2000x2000'},
        {'width': 3000, 'height': 3000, 'name': '3000x3000'},
    ]
    
    all_results = {}
    
    for config in test_configs:
        print(f"\n🖼️ Creating {config['name']} test image...")
        image_data = create_synthetic_image(
            width=config['width'], 
            height=config['height']
        )
        
        # Test with different thread counts
        max_workers_list = [1, 2, 4, 8] if os.cpu_count() >= 8 else [1, 2, 4]
        
        results = benchmark_processing(
            image_data, model_data, scaler_data, 
            config['name'], max_workers_list
        )
        
        all_results[config['name']] = results
    
    # Print summary
    print(f"\n{'='*80}")
    print("📊 BENCHMARK SUMMARY")
    print(f"{'='*80}")
    
    for size, results in all_results.items():
        print(f"\n🖼️ {size}:")
        if results.get('sequential'):
            print(f"   Sequential: {results['sequential']:.2f}s")
            
            for key, time_val in results.items():
                if key.startswith('parallel_') and time_val:
                    workers = key.split('_')[1]
                    speedup = results['sequential'] / time_val
                    print(f"   Parallel ({workers}): {time_val:.2f}s (🚀 {speedup:.2f}x speedup)")
        else:
            print("   Sequential: Failed")
            for key, time_val in results.items():
                if key.startswith('parallel_') and time_val:
                    workers = key.split('_')[1]
                    print(f"   Parallel ({workers}): {time_val:.2f}s")

if __name__ == "__main__":
    run_comprehensive_benchmark()
