from django.db import migrations, models


def copy_availability(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.filter(is_available=False).update(availability_status='sold_out')


class Migration(migrations.Migration):
    dependencies = [('shop', '0019_normalize_pizza_category_name')]
    operations = [
        migrations.AddField(model_name='product', name='availability_status', field=models.CharField(choices=[('available','Disponible'),('sold_out','Épuisé aujourd’hui'),('scheduled','Disponible plus tard')], default='available', max_length=20, verbose_name='Disponibilité')),
        migrations.AddField(model_name='product', name='available_again_at', field=models.DateTimeField(blank=True, null=True, verbose_name='Disponible à nouveau le')),
        migrations.RunPython(copy_availability, migrations.RunPython.noop),
    ]
