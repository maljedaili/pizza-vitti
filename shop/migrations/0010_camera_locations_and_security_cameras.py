import django.core.validators
import django.db.models.deletion
import shop.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0009_staff_roles_and_break_seconds'),
    ]

    operations = [
        migrations.CreateModel(
            name='CameraLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=140, verbose_name='Nom du lieu')),
                ('kind', models.CharField(choices=[('restaurant', 'Restaurant'), ('shop', 'Boutique'), ('office', 'Bureau'), ('project', 'Projet'), ('other', 'Autre')], default='restaurant', max_length=20, verbose_name='Type de lieu')),
                ('address', models.CharField(blank=True, max_length=240, verbose_name='Adresse')),
                ('gateway_url', models.URLField(help_text='Adresse HTTPS privée du gateway, sans identifiant caméra.', max_length=500, validators=[shop.models._validate_secure_camera_url])),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Lieu caméras',
                'verbose_name_plural': 'Lieux caméras',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SecurityCamera',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=140, verbose_name='Nom caméra')),
                ('stream_name', models.CharField(max_length=120, validators=[django.core.validators.RegexValidator(message='Utilisez uniquement lettres, chiffres, tiret, point ou underscore.', regex='^[A-Za-z0-9_.-]+$')], verbose_name='Nom du flux gateway')),
                ('brand', models.CharField(blank=True, max_length=100, verbose_name='Marque')),
                ('model_name', models.CharField(blank=True, max_length=100, verbose_name='Modèle')),
                ('custom_view_url', models.URLField(blank=True, help_text='Optionnel : page HTTPS fournie par le fabricant ou le NVR.', max_length=700, validators=[shop.models._validate_secure_camera_url])),
                ('supports_audio', models.BooleanField(default=True, verbose_name='Écoute audio')),
                ('supports_talk', models.BooleanField(default=False, verbose_name='Micro / parler')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Ordre')),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cameras', to='shop.cameralocation')),
            ],
            options={
                'verbose_name': 'Caméra',
                'verbose_name_plural': 'Caméras',
                'ordering': ['location__name', 'sort_order', 'name'],
                'unique_together': {('location', 'stream_name')},
            },
        ),
    ]
