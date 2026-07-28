from django.db import migrations


OLD_IMAGE = '/static/shop/img/products/la-margherita.jpg'
NEW_IMAGE = '/static/shop/img/products/la-margherita-3d.webp'


def use_3d_photo(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.filter(slug='la-margherita').update(external_image=NEW_IMAGE)


def restore_original_photo(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.filter(
        slug='la-margherita',
        external_image=NEW_IMAGE,
    ).update(external_image=OLD_IMAGE)


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_product_plate_photos'),
    ]

    operations = [
        migrations.RunPython(use_3d_photo, restore_original_photo),
    ]
