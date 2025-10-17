"""
Django management command to upload ML model files to database
"""
from django.core.management.base import BaseCommand
from api.models.machine_learning_model import MachineLearningModel
import os


class Command(BaseCommand):
    help = 'Upload ML model and scaler files to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-id',
            type=int,
            required=True,
            help='Model ID to update',
        )
        parser.add_argument(
            '--model-file',
            type=str,
            required=True,
            help='Path to model.pkl file',
        )
        parser.add_argument(
            '--scaler-file',
            type=str,
            required=True,
            help='Path to scaler.pkl file',
        )

    def handle(self, *args, **options):
        model_id = options['model_id']
        model_file_path = options['model_file']
        scaler_file_path = options['scaler_file']
        
        # Get model
        try:
            model = MachineLearningModel.objects.get(id=model_id)
        except MachineLearningModel.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Model with ID {model_id} not found!'))
            return
        
        self.stdout.write(f'Found model: {model.parameter.name} (ID: {model.id})')
        
        # Check if files exist
        if not os.path.exists(model_file_path):
            self.stdout.write(self.style.ERROR(f'Model file not found: {model_file_path}'))
            return
        
        if not os.path.exists(scaler_file_path):
            self.stdout.write(self.style.ERROR(f'Scaler file not found: {scaler_file_path}'))
            return
        
        # Read and upload model file
        with open(model_file_path, 'rb') as f:
            model.model_file = f.read()
        
        model_size = len(model.model_file)
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded model file ({model_size:,} bytes)'))
        
        # Read and upload scaler file
        with open(scaler_file_path, 'rb') as f:
            model.scaler_file = f.read()
        
        scaler_size = len(model.scaler_file)
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded scaler file ({scaler_size:,} bytes)'))
        
        # Save to database
        model.save()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Files uploaded to database successfully!'))
