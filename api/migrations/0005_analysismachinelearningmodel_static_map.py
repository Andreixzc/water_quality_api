# Generated by Django 5.1.4 on 2025-01-29 21:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_alter_analysismachinelearningmodel_raster_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysismachinelearningmodel',
            name='static_map',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]
