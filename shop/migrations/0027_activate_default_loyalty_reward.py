from django.db import migrations


def create_default_loyalty_reward(apps, schema_editor):
    LoyaltyReward = apps.get_model('shop', 'LoyaltyReward')
    if not LoyaltyReward.objects.filter(is_active=True).exists():
        LoyaltyReward.objects.create(
            name='Cadeau fidélité - Dessert offert',
            reward_type='free_dessert',
            pizzas_required=5,
            is_active=True,
        )


def remove_default_loyalty_reward(apps, schema_editor):
    LoyaltyReward = apps.get_model('shop', 'LoyaltyReward')
    LoyaltyReward.objects.filter(
        name='Cadeau fidélité - Dessert offert',
        reward_type='free_dessert',
        pizzas_required=5,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('shop', '0026_remove_demo_google_reviews')]

    operations = [
        migrations.RunPython(create_default_loyalty_reward, remove_default_loyalty_reward),
    ]
