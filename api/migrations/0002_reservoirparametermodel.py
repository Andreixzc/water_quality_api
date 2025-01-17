# Generated by Django 5.1.4 on 2025-01-08 03:58

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservoirParameterModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_file', models.FileField(upload_to='reservoir_models/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pkl', 'joblib'])])),
                ('scaler_file', models.FileField(upload_to='reservoir_scalers/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pkl', 'joblib'])])),
                ('model_path', models.CharField(max_length=255)),
                ('scaler_path', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parameter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservoir_models', to='api.parameter')),
                ('reservoir', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parameter_models', to='api.reservoir')),
            ],
            options={
                'unique_together': {('reservoir', 'parameter')},
            },
        ),
    ]
