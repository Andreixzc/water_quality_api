"""
Create mock ML models for testing the benchmark

This creates simple RandomForest models trained on random data.
Use this if you don't have real trained models yet.
"""

import pickle
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import os

def create_mock_models(output_dir='models'):
    """Create mock model and scaler files"""
    
    print("Creating mock ML models for testing...")
    print("")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate mock training data
    # 15 features (same as real reservoir data)
    n_samples = 1000
    n_features = 15
    
    print(f"Generating mock training data: {n_samples} samples × {n_features} features")
    X_train = np.random.randn(n_samples, n_features)
    y_train = np.random.randn(n_samples)  # Mock chlorophyll values
    
    # Create and train model
    print("Training RandomForest model...")
    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Create and fit scaler
    print("Creating StandardScaler...")
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    # Save model
    model_path = os.path.join(output_dir, 'model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    model_size = os.path.getsize(model_path)
    print(f"✓ Saved model to: {model_path} ({model_size:,} bytes)")
    
    # Save scaler
    scaler_path = os.path.join(output_dir, 'scaler.pkl')
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    scaler_size = os.path.getsize(scaler_path)
    print(f"✓ Saved scaler to: {scaler_path} ({scaler_size:,} bytes)")
    
    print("")
    print("="*60)
    print("Mock models created successfully!")
    print("="*60)
    print("")
    print("You can now:")
    print("  1. Run benchmark directly:")
    print("     cd benchmark")
    print("     python benchmark.py")
    print("")
    print("  2. Or upload to database first:")
    print("     sudo docker-compose exec web python manage.py upload_ml_models \\")
    print("       --model-id=1 \\")
    print(f"       --model-file=/app/{model_path} \\")
    print(f"       --scaler-file=/app/{scaler_path}")
    
    return model_path, scaler_path


if __name__ == '__main__':
    create_mock_models()
