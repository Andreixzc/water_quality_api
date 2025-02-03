# Generated by Django 5.1.4 on 2025-02-03 02:58

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalysisGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier_code', models.UUIDField(unique=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'analysis_group',
            },
        ),
        migrations.CreateModel(
            name='AnalysisRequestStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('icon', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'analysis_request_status',
            },
        ),
        migrations.CreateModel(
            name='MachineLearningModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_file', models.BinaryField()),
                ('scaler_file', models.BinaryField()),
                ('model_file_hash', models.CharField(max_length=64)),
                ('scaler_file_hash', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'machine_learning_model',
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('company', models.CharField(blank=True, max_length=255)),
                ('phone', models.CharField(blank=True, max_length=15)),
                ('cpf', models.CharField(max_length=11, unique=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Analysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier_code', models.UUIDField(unique=True)),
                ('cloud_percentage', models.DecimalField(blank=True, decimal_places=5, max_digits=6, null=True)),
                ('analysis_date', models.DateField(blank=True, null=True)),
                ('analysis_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.analysisgroup')),
            ],
            options={
                'db_table': 'analysis',
            },
        ),
        migrations.CreateModel(
            name='AnalysisRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('properties', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('analysis_group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.analysisgroup')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('analysis_request_status', models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='api.analysisrequeststatus')),
            ],
            options={
                'db_table': 'analysis_request',
            },
        ),
        migrations.CreateModel(
            name='AnalysisMachineLearningModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raster_file', models.BinaryField()),
                ('intensity_map', models.TextField(blank=True, null=True)),
                ('static_map', models.BinaryField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('analysis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.analysis')),
                ('machine_learning_model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.machinelearningmodel')),
            ],
            options={
                'db_table': 'analysis_machine_learning_model',
            },
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'parameter',
            },
        ),
        migrations.AddField(
            model_name='machinelearningmodel',
            name='parameter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.parameter'),
        ),
        migrations.CreateModel(
            name='Reservoir',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('coordinates', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'reservoir',
            },
        ),
        migrations.AddField(
            model_name='machinelearningmodel',
            name='reservoir',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.reservoir'),
        ),
        migrations.AddField(
            model_name='analysisgroup',
            name='reservoir',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.reservoir'),
        ),
        migrations.CreateModel(
            name='ReservoirUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reservoir', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.reservoir')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'reservoir_user',
            },
        ),
        migrations.CreateModel(
            name='UnprocessedSatelliteImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_date', models.DateField()),
                ('image_file', models.BinaryField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reservoir', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.reservoir')),
            ],
        ),
        migrations.AddConstraint(
            model_name='machinelearningmodel',
            constraint=models.UniqueConstraint(fields=('model_file_hash',), name='unique_file_hashes'),
        ),
        migrations.AlterUniqueTogether(
            name='reservoiruser',
            unique_together={('user', 'reservoir')},
        ),
        migrations.AlterUniqueTogether(
            name='unprocessedsatelliteimage',
            unique_together={('reservoir', 'image_date')},
        ),
    ]
