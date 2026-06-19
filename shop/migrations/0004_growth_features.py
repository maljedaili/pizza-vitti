# Generated manually for Pizza Vitti growth features
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0003_reservation_review_gallery_service_newsletter'),
    ]
    operations = [
        migrations.AddField(
            model_name='product',
            name='is_best_seller',
            field=models.BooleanField(default=False, verbose_name='Meilleure vente'),
        ),
        migrations.AddField(
            model_name='product',
            name='is_pizza_of_month',
            field=models.BooleanField(default=False, verbose_name='Pizza du mois'),
        ),
        migrations.AddField(
            model_name='order',
            name='order_type',
            field=models.CharField(choices=[('pickup', 'À emporter'), ('dine_in', 'Sur place'), ('uber_eats', 'Uber Eats'), ('deliveroo', 'Deliveroo'), ('just_eat', 'Just Eat')], default='pickup', max_length=20, verbose_name='Type de commande'),
        ),
        migrations.AddField(
            model_name='order',
            name='selected_reward',
            field=models.CharField(blank=True, max_length=80, verbose_name='Cadeau fidélité choisi'),
        ),
        migrations.AddField(
            model_name='order',
            name='promo_code',
            field=models.CharField(blank=True, max_length=40, verbose_name='Code promo'),
        ),
        migrations.CreateModel(
            name='LoyaltyReward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(default='Cadeau fidélité', max_length=120)),
                ('reward_type', models.CharField(choices=[('free_pizza', 'Pizza offerte'), ('free_pasta', 'Pasta offerte'), ('free_dessert', 'Dessert offert'), ('discount_10', '10% de réduction')], default='free_dessert', max_length=30)),
                ('pizzas_required', models.PositiveIntegerField(default=5)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['pizzas_required', 'name'], 'verbose_name': 'Récompense fidélité', 'verbose_name_plural': 'Récompenses fidélité'},
        ),
        migrations.CreateModel(
            name='PromoCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=40, unique=True)),
                ('description', models.CharField(blank=True, max_length=180)),
                ('discount_percent', models.PositiveIntegerField(default=10)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['code'], 'verbose_name': 'Code promo', 'verbose_name_plural': 'Codes promo'},
        ),
        migrations.CreateModel(
            name='GiftCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.CharField(max_length=40, unique=True)),
                ('initial_value', models.DecimalField(decimal_places=2, default=25, max_digits=8)),
                ('remaining_value', models.DecimalField(decimal_places=2, default=25, max_digits=8)),
                ('recipient_email', models.EmailField(blank=True, max_length=254)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Carte cadeau', 'verbose_name_plural': 'Cartes cadeaux'},
        ),
    ]
