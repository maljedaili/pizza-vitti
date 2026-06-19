# Generated for Pizza Vitti customer area and 9-language menu translations
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shop', '0004_growth_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('language', models.CharField(choices=[('fr', 'Français'), ('en', 'English'), ('es', 'Español'), ('it', 'Italiano'), ('pt', 'Português'), ('nl', 'Nederlands'), ('zh', '中文'), ('ja', '日本語'), ('ar', 'العربية')], max_length=5)),
                ('name', models.CharField(max_length=180)),
                ('description', models.TextField(blank=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='shop.product')),
            ],
            options={'verbose_name': 'Traduction produit', 'verbose_name_plural': 'Traductions produits', 'ordering': ['product__name', 'language'], 'unique_together': {('product', 'language')}},
        ),
        migrations.CreateModel(
            name='CategoryTranslation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('language', models.CharField(choices=[('fr', 'Français'), ('en', 'English'), ('es', 'Español'), ('it', 'Italiano'), ('pt', 'Português'), ('nl', 'Nederlands'), ('zh', '中文'), ('ja', '日本語'), ('ar', 'العربية')], max_length=5)),
                ('name', models.CharField(max_length=140)),
                ('description', models.TextField(blank=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='shop.category')),
            ],
            options={'verbose_name': 'Traduction catégorie', 'verbose_name_plural': 'Traductions catégories', 'ordering': ['category__order', 'language'], 'unique_together': {('category', 'language')}},
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='shop.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pizza_vitti_favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Favori client', 'verbose_name_plural': 'Favoris clients', 'ordering': ['-created_at'], 'unique_together': {('user', 'product')}},
        ),
    ]
