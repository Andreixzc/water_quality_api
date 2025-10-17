"""
Django management command to export ML model and scaler files
"""
from django.core.management.base import BaseCommand
from api.models.machine_learning_model import MachineLearningModel
import os


class Command(BaseCommand):
    help = 'Export ML model and scaler files for benchmarking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-id',
            type=int,
            help='Specific model ID to export (default: first model)',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/app/benchmark/models',
            help='Output directory for exported files',
        )

    def handle(self, *args, **options):
        model_id = options['model_id']
        output_dir = options['output_dir']
        
        # Get model
        if model_id:
            try:
                model = MachineLearningModel.objects.get(id=model_id)
            except MachineLearningModel.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Model with ID {model_id} not found!'))
                return
        else:
            model = MachineLearningModel.objects.first()
            if not model:
                self.stdout.write(self.style.ERROR('No models found in database!'))
                return
        
        self.stdout.write(f'Found model: {model.parameter.name} (ID: {model.id})')
        
        # Check if model files exist
        if not model.model_file:
            self.stdout.write(self.style.ERROR('model_file is NULL! Please upload the model file.'))
            return
        
        if not model.scaler_file:
            self.stdout.write(self.style.ERROR('scaler_file is NULL! Please upload the scaler file.'))
            return
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Export model file
        model_path = os.path.join(output_dir, 'model.pkl')
        with open(model_path, 'wb') as f:
            f.write(bytes(model.model_file))
        self.stdout.write(self.style.SUCCESS(f'✓ Exported model to: {model_path}'))
        
        # Export scaler file
        scaler_path = os.path.join(output_dir, 'scaler.pkl')
        with open(scaler_path, 'wb') as f:
            f.write(bytes(model.scaler_file))
        self.stdout.write(self.style.SUCCESS(f'✓ Exported scaler to: {scaler_path}'))
        
        # Show file sizes
        model_size = os.path.getsize(model_path)
        scaler_size = os.path.getsize(scaler_path)
        
        self.stdout.write(f'\nFile sizes:')
        self.stdout.write(f'  model.pkl: {model_size:,} bytes')
        self.stdout.write(f'  scaler.pkl: {scaler_size:,} bytes')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Export complete!'))
