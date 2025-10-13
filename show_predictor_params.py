"""
Test to show exactly what parameters are being passed to WaterQualityPredictor
"""
import sys
sys.path.append('/home/andrei/projects/water_quality_api')

from processing.config import ParallelProcessingConfig

def show_predictor_params():
    """Show exactly what parameters would be passed to WaterQualityPredictor"""
    print("🔧 WaterQualityPredictor Parameters")
    print("=" * 50)
    
    # Print current config
    ParallelProcessingConfig.print_config()
    
    print(f"\n📋 Actual parameters that will be passed:")
    print(f"   use_parallel = {ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING}")
    print(f"   max_workers = {ParallelProcessingConfig.get_max_workers()}")
    
    print(f"\n🔍 This means:")
    if ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING:
        print(f"   ✅ Parallel processing WILL be used")
        print(f"   🧵 Number of threads: {ParallelProcessingConfig.get_max_workers()}")
        print(f"   🏗️  Architecture: ThreadPoolExecutor with thread-local models")
        print(f"   📈 Expected performance: 2-6x faster than sequential")
    else:
        print(f"   ❌ Sequential processing will be used")
        print(f"   🐌 Single-threaded chunk processing")
        print(f"   📉 No performance improvement")
    
    print(f"\n💻 System Info:")
    import os
    print(f"   CPU cores: {os.cpu_count()}")
    print(f"   Optimal workers (75% of cores, max 8): {ParallelProcessingConfig.get_max_workers()}")

if __name__ == "__main__":
    show_predictor_params()
