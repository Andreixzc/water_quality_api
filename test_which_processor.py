"""
Test to determine which processor is actually being used in the API
"""
import sys
sys.path.append('/home/andrei/projects/water_quality_api')

from processing.services.ml_processor import WaterQualityPredictor
from processing.config import ParallelProcessingConfig

def test_which_processor():
    """Test which processor implementation is actually being used"""
    print("🔍 Testing Which Processor Is Being Used in the API")
    print("=" * 60)
    
    print(f"📦 Import Path:")
    print(f"  from processing.services.ml_processor import WaterQualityPredictor")
    print(f"  Class: {WaterQualityPredictor}")
    print(f"  Module: {WaterQualityPredictor.__module__}")
    
    # Check the constructor signature
    import inspect
    sig = inspect.signature(WaterQualityPredictor.__init__)
    print(f"\n🔧 Constructor Parameters:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            default = param.default if param.default != param.empty else "No default"
            print(f"  {param_name}: {default}")
    
    # Test with dummy data to see what happens
    print(f"\n🧠 Testing Initialization:")
    try:
        # Create dummy model data
        import joblib
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        from io import BytesIO
        import numpy as np
        
        # Create dummy models
        dummy_model = RandomForestRegressor(n_estimators=5, random_state=42)
        dummy_scaler = StandardScaler()
        dummy_X = np.random.rand(100, 15)
        dummy_y = np.random.rand(100)
        
        dummy_model.fit(dummy_X, dummy_y)
        dummy_scaler.fit(dummy_X)
        
        # Serialize to bytes
        model_buffer = BytesIO()
        scaler_buffer = BytesIO()
        joblib.dump(dummy_model, model_buffer)
        joblib.dump(dummy_scaler, scaler_buffer)
        
        model_data = model_buffer.getvalue()
        scaler_data = scaler_buffer.getvalue()
        
        print(f"  Creating WaterQualityPredictor with configuration...")
        print(f"  use_parallel = {ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING}")
        print(f"  max_workers = {ParallelProcessingConfig.get_max_workers()}")
        
        # Test initialization as it would be called in tasks.py
        predictor = WaterQualityPredictor(
            model_data, 
            scaler_data,
            use_parallel=ParallelProcessingConfig.ENABLE_PARALLEL_PROCESSING,
            max_workers=ParallelProcessingConfig.get_max_workers()
        )
        
        print(f"\n✅ SUCCESS - Predictor created!")
        print(f"  Type: {type(predictor)}")
        print(f"  Has parallel mode: {hasattr(predictor, 'use_parallel')}")
        if hasattr(predictor, 'use_parallel'):
            print(f"  Parallel enabled: {predictor.use_parallel}")
            if hasattr(predictor, 'max_workers'):
                print(f"  Max workers: {predictor.max_workers}")
        
        # Check available methods
        methods = [method for method in dir(predictor) if not method.startswith('_') and callable(getattr(predictor, method))]
        print(f"  Available methods: {methods}")
        
        if 'process_image_parallel' in methods:
            print(f"  🚀 HAS PARALLEL PROCESSING METHOD!")
        if 'process_image_sequential' in methods:
            print(f"  🐌 HAS SEQUENTIAL PROCESSING METHOD!")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_which_processor()
