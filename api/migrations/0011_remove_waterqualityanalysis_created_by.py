# Generated by Django 5.1.4 on 2025-01-17 05:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_remove_waterqualityanalysisparameter_analysis_date_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='waterqualityanalysis',
            name='created_by',
        ),
    ]