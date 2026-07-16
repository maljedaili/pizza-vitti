from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0010_camera_locations_and_security_cameras'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LoyaltyRedemption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('milestone', models.PositiveIntegerField(verbose_name='Palier de pizzas')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty_redemptions', to='shop.order')),
                ('reward', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='redemptions', to='shop.loyaltyreward')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pizza_vitti_loyalty_redemptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cadeau fidélité attribué',
                'verbose_name_plural': 'Cadeaux fidélité attribués',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='loyaltyredemption',
            constraint=models.UniqueConstraint(fields=('order', 'milestone'), name='unique_loyalty_milestone_per_order'),
        ),
    ]
