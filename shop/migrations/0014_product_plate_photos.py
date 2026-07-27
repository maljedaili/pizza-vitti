from django.db import migrations


PRODUCT_PHOTOS = {
    'La Vegetariana': 'la-vegetariana.jpg',
    'La Pescatora': 'la-pescatora.jpg',
    'L’Adriana': 'l-adriana.jpg',
    'La fumée': 'la-fumee.jpg',
    'La Salmone': 'la-salmone.jpg',
    'La Vesuvio': 'la-vesuvio.jpg',
    'La Napoletana': 'la-napoletana.jpg',
    'La Tartuffo': 'la-tartuffo.jpg',
    'La Quattro stagioni': 'la-quattro-stagioni.jpg',
    'La Regina': 'la-regina.jpg',
    'La Cabri': 'la-cabri.jpg',
    'La Parma et Burrata': 'la-parma.jpg',
    'La Quattro Formaggi': 'la-quattro-formaggi.jpg',
    'La Calabrese': 'la-calabrese.jpg',
    'La Margherita': 'la-margherita.jpg',
    'Bruschetta burrata pesto': 'bruschetta-burrata-pesto.jpg',
    'Bruschetta saumon fumé': 'bruschetta-saumon-fume.jpg',
    'Mozzarella Caprese': 'mozzarella-caprese.jpg',
    'Caponata sicilienne & burrata': 'caponata-burrata.jpg',
    'Panna cotta aux fruits rouges': 'panna-cotta-fruits-rouges.jpg',
    'Panna cotta au caramel beurre salé': 'panna-cotta-caramel.jpg',
    'Tiramisu': 'tiramisu.jpg',
    'Lasagnes du chef': 'lasagnes-du-chef.jpg',
    'Gnocchi al Pesto Verde': 'gnocchi-pesto-verde.jpg',
    'Spaghetti à la Carbonara': 'spaghetti-carbonara.jpg',
    'Spaghetti à la Bolognaise': 'spaghetti-bolognaise.jpg',
}


def add_product_photos(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    for name, filename in PRODUCT_PHOTOS.items():
        Product.objects.filter(name=name).update(
            external_image=f'/static/shop/img/products/{filename}'
        )


def remove_product_photos(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    for filename in PRODUCT_PHOTOS.values():
        Product.objects.filter(
            external_image=f'/static/shop/img/products/{filename}'
        ).update(external_image='')


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0013_verified_reviews'),
    ]

    operations = [
        migrations.RunPython(add_product_photos, remove_product_photos),
    ]
