# Generated for Pizza Vitti table ordering
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0005_customer_area_translations'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='table_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Numéro de table'),
        ),
    ]
