#!/usr/bin/env python
"""
Download ML models from database to local filesystem
No Docker needed - runs directly with Django
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_quality_project.settings')
django.setup()

from api.models.machine_learning_model import MachineLearningModel


def download_models(model_id=1, output_dir='./benchmark/models'):
    """Download model and scaler from database to local files"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get model from database
    try:
        ml_model = MachineLearningModel.objects.get(id=model_id)
    except MachineLearningModel.DoesNotExist:
        print(f"❌ Model with ID {model_id} not found in database")
        return False
    
    # Check if model files exist in database
    if not ml_model.model_file:
        print(f"❌ Model {model_id} has no model_file in database")
        return False
    
    if not ml_model.scaler_file:
        print(f"❌ Model {model_id} has no scaler_file in database")
        return False
    
    # Write model file
    model_path = os.path.join(output_dir, 'model.pkl')
    with open(model_path, 'wb') as f:
        f.write(ml_model.model_file)
    model_size = len(ml_model.model_file)
    
    # Write scaler file
    scaler_path = os.path.join(output_dir, 'scaler.pkl')
    with open(scaler_path, 'wb') as f:
        f.write(ml_model.scaler_file)
    scaler_size = len(ml_model.scaler_file)
    
    print(f"✅ Successfully downloaded models from database!")
    print(f"")
    print(f"Model ID: {model_id}")
    print(f"Reservoir: {ml_model.reservoir.name} (ID: {ml_model.reservoir.id})")
    print(f"Parameter: {ml_model.parameter.name}")
    print(f"")
    print(f"📁 Files created:")
    print(f"  - {model_path} ({model_size:,} bytes)")
    print(f"  - {scaler_path} ({scaler_size:,} bytes)")
    print(f"")
    print(f"🎯 Ready to use for benchmarking!")
    
    return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Download ML models from database')
    parser.add_argument('--model-id', type=int, default=1, help='Model ID to download (default: 1)')
    parser.add_argument('--output-dir', default='./benchmark/models', help='Output directory (default: ./benchmark/models)')
    
    args = parser.parse_args()
    
    success = download_models(args.model_id, args.output_dir)
    sys.exit(0 if success else 1)
