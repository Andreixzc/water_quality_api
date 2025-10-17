#!/bin/bash
# Download models from database to local filesystem

MODEL_ID=${1:-1}
OUTPUT_DIR=${2:-"./benchmark/models"}

echo "🔽 Downloading models from database..."
echo "   Model ID: $MODEL_ID"
echo "   Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Download model file
DOCKER_WARNINGS=$(sudo docker-compose exec -T web python -c "
import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_quality_project.settings')
django.setup()

from api.models.machine_learning_model import MachineLearningModel

try:
    ml_model = MachineLearningModel.objects.get(id=$MODEL_ID)
    
    if not ml_model.model_file or not ml_model.scaler_file:
        print('❌ Model files not found in database', file=sys.stderr)
        sys.exit(1)
    
    # Write model file to stdout as binary
    sys.stdout.buffer.write(ml_model.model_file)
    
except Exception as e:
    print(f'❌ Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>&1 > "$OUTPUT_DIR/model.joblib.tmp")

# Check for errors
if [ $? -ne 0 ]; then
    echo "$DOCKER_WARNINGS" >&2
    rm -f "$OUTPUT_DIR/model.joblib.tmp"
    exit 1
fi

# Move temp file to final location
mv "$OUTPUT_DIR/model.joblib.tmp" "$OUTPUT_DIR/model.joblib"

# Check if model was downloaded
if [ ! -s "$OUTPUT_DIR/model.joblib" ]; then
    echo "❌ Failed to download model"
    rm -f "$OUTPUT_DIR/model.joblib"
    exit 1
fi

MODEL_SIZE=$(stat -f%z "$OUTPUT_DIR/model.joblib" 2>/dev/null || stat -c%s "$OUTPUT_DIR/model.joblib")

# Download scaler file
DOCKER_WARNINGS=$(sudo docker-compose exec -T web python -c "
import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'water_quality_project.settings')
django.setup()

from api.models.machine_learning_model import MachineLearningModel

ml_model = MachineLearningModel.objects.get(id=$MODEL_ID)
sys.stdout.buffer.write(ml_model.scaler_file)
" 2>&1 > "$OUTPUT_DIR/scaler.joblib.tmp")

# Check for errors
if [ $? -ne 0 ]; then
    echo "$DOCKER_WARNINGS" >&2
    rm -f "$OUTPUT_DIR/scaler.joblib.tmp"
    exit 1
fi

# Move temp file to final location
mv "$OUTPUT_DIR/scaler.joblib.tmp" "$OUTPUT_DIR/scaler.joblib"

# Check if scaler was downloaded
if [ ! -s "$OUTPUT_DIR/scaler.joblib" ]; then
    echo "❌ Failed to download scaler"
    rm -f "$OUTPUT_DIR/scaler.joblib"
    exit 1
fi

SCALER_SIZE=$(stat -f%z "$OUTPUT_DIR/scaler.joblib" 2>/dev/null || stat -c%s "$OUTPUT_DIR/scaler.joblib")

echo "✅ Successfully downloaded models!"
echo ""
echo "📁 Files created:"
echo "   - $OUTPUT_DIR/model.joblib ($MODEL_SIZE bytes)"
echo "   - $OUTPUT_DIR/scaler.joblib ($SCALER_SIZE bytes)"
echo ""
echo "🎯 Ready to use!"
