# Generated for Pizza Vitti order email notifications
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0006_order_table_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='confirmation_email_sent',
            field=models.BooleanField(default=False, verbose_name='Email de confirmation envoyé'),
        ),
        migrations.AddField(
            model_name='order',
            name='ready_email_sent',
            field=models.BooleanField(default=False, verbose_name='Email commande prête envoyé'),
        ),
    ]
