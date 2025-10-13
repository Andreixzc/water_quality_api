"""
Configuration settings for parallel processing
"""
import os

class ParallelProcessingConfig:
    """Configuration for parallel chunk processing"""
    
    # Enable/disable parallel processing
    ENABLE_PARALLEL_PROCESSING = os.getenv('ENABLE_PARALLEL_PROCESSING', 'True').lower() == 'true'
    
    # Maximum number of worker threads
    # Set to None for auto-detection (CPU count), or specify a number
    MAX_WORKERS = int(os.getenv('MAX_WORKERS')) if os.getenv('MAX_WORKERS') else None
    
    # Chunk size for processing (in pixels)
    # Set to 0 to always enable parallel processing regardless of dataset size
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '0'))
    
    # Progress reporting interval (every N chunks)
    PROGRESS_INTERVAL = int(os.getenv('PROGRESS_INTERVAL', '10'))
    
    @classmethod
    def get_max_workers(cls):
        """Get the optimal number of worker threads"""
        if cls.MAX_WORKERS is not None:
            return cls.MAX_WORKERS
        
        # Auto-detect based on CPU count
        cpu_count = os.cpu_count() or 4
        
        # Conservative approach: use 75% of CPU cores, max 8
        optimal = min(max(1, int(cpu_count * 0.75)), 8)
        
        return optimal
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print(f"Parallel Processing Configuration:")
        print(f"  Enabled: {cls.ENABLE_PARALLEL_PROCESSING}")
        print(f"  Max Workers: {cls.get_max_workers()}")
        print(f"  Chunk Size: {cls.CHUNK_SIZE}")
        print(f"  Progress Interval: {cls.PROGRESS_INTERVAL}")

# Environment variable examples for .env file:
# ENABLE_PARALLEL_PROCESSING=True
# MAX_WORKERS=4
# CHUNK_SIZE=500
# PROGRESS_INTERVAL=10
