"""
Setup script to copy ML models from Docker container to benchmark directory
"""

import os
import subprocess
import sys

def main():
    print("="*60)
    print("Model Setup for Benchmark")
    print("="*60)
    
    # Create models directory
    os.makedirs('models', exist_ok=True)
    
    print("\nCopying model files from Docker container...")
    
    # Get the first ML model from database
    cmd = """
    sudo docker-compose exec -T web python -c "
from api.models.machine_learning_model import MachineLearningModel
import sys

model = MachineLearningModel.objects.first()
if model:
    print(model.id)
else:
    sys.exit(1)
"
    """
    
    try:
        # Go to parent directory to run docker-compose
        os.chdir('..')
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error: Could not find ML model in database")
            print("Make sure your Docker containers are running!")
            return
        
        model_id = result.stdout.strip()
        print(f"Found model ID: {model_id}")
        
        # Copy model file
        print("Copying model.pkl...")
        subprocess.run(
            f"sudo docker-compose exec -T db psql -U yd -d water_quality_db -t -c "
            f"\"SELECT encode(model_file, 'base64') FROM api_machinelearningmodel WHERE id={model_id};\" "
            f"| base64 -d > benchmark/models/model.pkl",
            shell=True
        )
        
        # Copy scaler file
        print("Copying scaler.pkl...")
        subprocess.run(
            f"sudo docker-compose exec -T db psql -U yd -d water_quality_db -t -c "
            f"\"SELECT encode(scaler_file, 'base64') FROM api_machinelearningmodel WHERE id={model_id};\" "
            f"| base64 -d > benchmark/models/scaler.pkl",
            shell=True
        )
        
        # Verify files exist
        if os.path.exists('benchmark/models/model.pkl') and os.path.exists('benchmark/models/scaler.pkl'):
            model_size = os.path.getsize('benchmark/models/model.pkl')
            scaler_size = os.path.getsize('benchmark/models/scaler.pkl')
            
            print("\n" + "="*60)
            print("SUCCESS!")
            print("="*60)
            print(f"Model file: benchmark/models/model.pkl ({model_size} bytes)")
            print(f"Scaler file: benchmark/models/scaler.pkl ({scaler_size} bytes)")
            print("\nYou can now run the benchmark:")
            print("  cd benchmark")
            print("  python benchmark.py")
        else:
            print("\nError: Failed to copy model files")
            print("Please copy them manually:")
            print("  1. Export from Docker container")
            print("  2. Place in benchmark/models/ directory")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nAlternative: Copy files manually")
        print("Run these commands from the project root:")
        print("")
        print("  # Find model ID")
        print("  sudo docker-compose exec web python manage.py shell -c \"from api.models.machine_learning_model import MachineLearningModel; print(MachineLearningModel.objects.first().id)\"")
        print("")
        print("  # Then copy the files manually from the database or container")

if __name__ == '__main__':
    main()
