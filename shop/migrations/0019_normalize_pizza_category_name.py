from django.db import migrations


def normalize_pizza_category_name(apps, schema_editor):
    Category = apps.get_model('shop', 'Category')
    Category.objects.filter(name__iexact='Nos Pizza').update(name='Nos Pizzas')


class Migration(migrations.Migration):
    dependencies = [('shop', '0018_reset_admin_credentials')]

    operations = [migrations.RunPython(normalize_pizza_category_name, migrations.RunPython.noop)]
