#!/bin/bash

# Simple script to export model files from Docker to benchmark directory

echo "=========================================="
echo "Exporting ML Models for Benchmark"
echo "=========================================="
echo ""

cd "$(dirname "$0")/.."

# Create models directory
mkdir -p benchmark/models

echo "Checking for models in database..."

# Use Django management command to export
echo "Running export command..."
sudo docker-compose exec web python manage.py export_ml_models --output-dir=/app/benchmark/models

# Copy files from container to host
echo ""
echo "Copying files to host..."
sudo docker cp water_quality_api-web-1:/app/benchmark/models/model.pkl ./benchmark/models/ 2>/dev/null
sudo docker cp water_quality_api-web-1:/app/benchmark/models/scaler.pkl ./benchmark/models/ 2>/dev/null

# Check if successful
if [ -f "benchmark/models/model.pkl" ] && [ -f "benchmark/models/scaler.pkl" ]; then
    echo ""
    echo "=========================================="
    echo "SUCCESS!"
    echo "=========================================="
    echo ""
    ls -lh benchmark/models/
    echo ""
    echo "Ready to run benchmark:"
    echo "  cd benchmark"
    echo "  python benchmark.py"
else
    echo ""
    echo "=========================================="
    echo "ERROR: Model files are NULL in database!"
    echo "=========================================="
    echo ""
    echo "The model_file and scaler_file fields are NULL."
    echo "You need to upload the actual ML model files."
    echo ""
    echo "Options:"
    echo "  1. Use the API endpoint to upload model files"
    echo "  2. Use Django admin to upload files"
    echo "  3. Use a script to populate the database"
    echo ""
    echo "See: UPLOAD_MODELS_GUIDE.md for instructions"
fi
