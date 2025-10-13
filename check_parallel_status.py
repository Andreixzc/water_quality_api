"""
Quick test to check if parallel processing is currently enabled
"""
import sys
sys.path.append('/home/andrei/projects/water_quality_api')

from processing.config import ParallelProcessingConfig

def check_parallel_status():
    """Check if parallel processing is currently enabled"""
    print("🔍 Current Parallel Processing Status")
    print("=" * 50)
    
    # Check configuration
    ParallelProcessingConfig.print_config()
    
    print(f"\n📊 Details:")
    print(f"  Environment Variable ENABLE_PARALLEL_PROCESSING: {ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING}")
    print(f"  Auto-detected optimal workers: {ParallelProcessingConfig.get_max_workers()}")
    import os
    print(f"  CPU Count: {os.cpu_count()}")
    
    # Test what would happen when creating a predictor
    print(f"\n🧠 Predictor Configuration:")
    print(f"  When creating WaterQualityPredictor:")
    print(f"    use_parallel = {ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING}")
    print(f"    max_workers = {ParallelProcessingConfig.get_max_workers()}")
    
    if ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING:
        print(f"\n✅ PARALLEL PROCESSING IS ENABLED!")
        print(f"   🚀 Will use {ParallelProcessingConfig.get_max_workers()} worker threads")
        print(f"   ⚡ Expected 2-4x performance improvement")
    else:
        print(f"\n❌ PARALLEL PROCESSING IS DISABLED")
        print(f"   🐌 Will use sequential processing")
        print(f"   💡 To enable, set ENABLE_PARALLEL_PROCESSING=True in .env")

if __name__ == "__main__":
    check_parallel_status()
