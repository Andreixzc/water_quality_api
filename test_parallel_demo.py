"""
Simple test script to demonstrate parallel vs sequential chunk processing
"""
import sys
import os

# Add the project root to the Python path
sys.path.append('/home/andrei/projects/water_quality_api')

from benchmark_parallel_processing import create_synthetic_image, load_test_models
from processing.services.ml_processor import WaterQualityPredictor
import time
from io import BytesIO

def quick_demo():
    """Quick demonstration of parallel vs sequential processing"""
    print("🚀 Quick Parallel Processing Demo")
    print("=" * 50)
    
    # Create a small test image
    print("📦 Creating test image (1000x1000)...")
    image_data = create_synthetic_image(width=1000, height=1000)
    
    # Load test models
    print("🧠 Loading test models...")
    model_data, scaler_data = load_test_models()
    
    # Test sequential processing
    print("\n⏳ Testing Sequential Processing...")
    start_time = time.time()
    
    sequential_predictor = WaterQualityPredictor(
        model_data, scaler_data, 
        use_parallel=False  # Force sequential
    )
    output_sequential = BytesIO()
    sequential_predictor.process_image(image_data, output_sequential)
    
    sequential_time = time.time() - start_time
    print(f"✅ Sequential completed in {sequential_time:.2f} seconds")
    
    # Test parallel processing
    print("\n🚀 Testing Parallel Processing...")
    start_time = time.time()
    
    parallel_predictor = WaterQualityPredictor(
        model_data, scaler_data, 
        use_parallel=True,    # Enable parallel
        max_workers=4         # Use 4 threads
    )
    output_parallel = BytesIO()
    parallel_predictor.process_image(image_data, output_parallel)
    
    parallel_time = time.time() - start_time
    speedup = sequential_time / parallel_time
    
    print(f"✅ Parallel completed in {parallel_time:.2f} seconds")
    print(f"🚀 Speedup: {speedup:.2f}x faster!")
    
    # Verify outputs are similar size (basic sanity check)
    seq_size = len(output_sequential.getvalue())
    par_size = len(output_parallel.getvalue())
    
    print(f"\n📊 Output file sizes:")
    print(f"   Sequential: {seq_size:,} bytes")
    print(f"   Parallel:   {par_size:,} bytes")
    
    if abs(seq_size - par_size) < 1000:  # Allow small differences
        print("✅ Output sizes match - processing successful!")
    else:
        print("⚠️  Output sizes differ significantly - check implementation")

if __name__ == "__main__":
    quick_demo()
