import time
import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
import joblib
from processing.services.ml_processor import WaterQualityPredictor
from processing.config import ParallelProcessingConfig
import pandas as pd

def create_synthetic_image(width, height, bands=12):
    """Create a synthetic multi-band image in memory"""
    # Create random data for bands
    data = np.random.rand(bands, height, width).astype(np.float32)
    
    # Create a transform
    transform = from_origin(0, 0, 10, 10)
    
    # Create a memory file
    memfile = rasterio.MemoryFile()
    with memfile.open(
        driver='GTiff',
        height=height,
        width=width,
        count=bands,
        dtype='float32',
        crs='EPSG:4326',
        transform=transform,
    ) as dataset:
        dataset.write(data)
        
    return memfile

def run_test(predictor, image_data, description):
    """Run a single test and return execution time"""
    start_time = time.time()
    
    # We need to reset the file pointer of the image data for each read
    image_data.seek(0)
    
    # Use a dummy output file
    from io import BytesIO
    output_file = BytesIO()
    
    predictor.process_image(image_data.read(), output_file)
    
    end_time = time.time()
    return end_time - start_time

def main():
    # Load models
    model_path = 'benchmark/models/model.joblib'
    scaler_path = 'benchmark/models/scaler.joblib'
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        print("Error: Model files not found in benchmark/models/")
        return

    with open(model_path, 'rb') as f:
        model_bytes = f.read()
    with open(scaler_path, 'rb') as f:
        scaler_bytes = f.read()

    workers_list = [1, 2, 4, 8]
    
    print("\n=== Strong Scalability Test ===")
    print("Fixed Problem Size: 2000x2000 pixels")
    print("| Workers | Time (s) | Speedup | Efficiency |")
    print("|---------|----------|---------|------------|")
    
    base_time = None
    strong_results = []
    
    # Create fixed image for strong scalability
    fixed_image = create_synthetic_image(2000, 2000)
    
    for workers in workers_list:
        predictor = WaterQualityPredictor(
            model_bytes, 
            scaler_bytes, 
            use_parallel=True, 
            max_workers=workers
        )
        
        duration = run_test(predictor, fixed_image, f"Strong Scaling ({workers} workers)")
        
        if workers == 1:
            base_time = duration
            speedup = 1.0
        else:
            speedup = base_time / duration
            
        efficiency = speedup / workers
        
        print(f"| {workers} | {duration:.2f} | {speedup:.2f} | {efficiency:.2f} |")
        strong_results.append({
            'workers': workers,
            'time': duration,
            'speedup': speedup,
            'efficiency': efficiency
        })

    # ... (previous code) ...
    
    # Collect all results
    all_results = {
        "strong_scaling": strong_results,
        "weak_scaling": []
    }

    print("\n=== Weak Scalability Test ===")
    print("Base Problem Size: 1000x1000 pixels per worker (approx)")
    print("| Workers | Image Size | Time (s) | Efficiency |")
    print("|---------|------------|----------|------------|")
    
    base_weak_time = None
    
    for workers in workers_list:
        # Calculate dimension to keep work per processor roughly constant
        # Area = Base_Area * Workers
        # Side = sqrt(Base_Area * Workers) = Base_Side * sqrt(Workers)
        side = int(1000 * np.sqrt(workers))
        
        image = create_synthetic_image(side, side)
        
        predictor = WaterQualityPredictor(
            model_bytes, 
            scaler_bytes, 
            use_parallel=True, 
            max_workers=workers
        )
        
        duration = run_test(predictor, image, f"Weak Scaling ({workers} workers, {side}x{side})")
        
        if workers == 1:
            base_weak_time = duration
            efficiency = 1.0
        else:
            efficiency = base_weak_time / duration
            
        print(f"| {workers} | {side}x{side} | {duration:.2f} | {efficiency:.2f} |")
        
        all_results["weak_scaling"].append({
            "workers": workers,
            "image_size": f"{side}x{side}",
            "time": duration,
            "efficiency": efficiency
        })

    # Save results to JSON
    import json
    with open('benchmark_results.json', 'w') as f:
        json.dump(all_results, f, indent=4)
    
    print("\nResults saved to benchmark_results.json")

if __name__ == "__main__":
    main()
