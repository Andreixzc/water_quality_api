# Generated by Django 5.1.4 on 2025-01-17 02:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_remove_waterqualityanalysis_analysis_end_date_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ReservoirParameterModel',
            new_name='ReservoirParameterModelScaler',
        ),
        migrations.RenameModel(
            old_name='ReservoirUsers',
            new_name='ReservoirUser',
        ),
        migrations.RenameModel(
            old_name='WaterQualityAnalysisParameters',
            new_name='WaterQualityAnalysisParameter',
        ),
        migrations.AlterModelOptions(
            name='user',
            options={},
        ),
        migrations.AlterModelTable(
            name='parameter',
            table='parameter',
        ),
        migrations.AlterModelTable(
            name='reservoir',
            table='reservoir',
        ),
        migrations.AlterModelTable(
            name='reservoirparametermodelscaler',
            table='reservoir_parameter_model_scaler',
        ),
        migrations.AlterModelTable(
            name='reservoiruser',
            table='reservoir_user',
        ),
        migrations.AlterModelTable(
            name='user',
            table='user',
        ),
        migrations.AlterModelTable(
            name='waterqualityanalysis',
            table='water_quality_analysis',
        ),
        migrations.AlterModelTable(
            name='waterqualityanalysisparameter',
            table='water_quality_analysis_parameter',
        ),
    ]