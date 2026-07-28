from django.core.management.base import BaseCommand

from shop.models import Product


PRODUCT_PHOTOS = {
    'la-vegetariana': 'la-vegetariana.jpg',
    'la-pescatora': 'la-pescatora.jpg',
    'l-adriana': 'l-adriana.jpg',
    'la-fumee': 'la-fumee.jpg',
    'la-salmone': 'la-salmone.jpg',
    'la-vesuvio': 'la-vesuvio.jpg',
    'la-napoletana': 'la-napoletana.jpg',
    'la-tartuffo': 'la-tartuffo.jpg',
    'la-quattro-stagioni': 'la-quattro-stagioni.jpg',
    'la-regina': 'la-regina.jpg',
    'la-cabri': 'la-cabri.jpg',
    'la-parma-et-burrata': 'la-parma.jpg',
    'la-quattro-formaggi': 'la-quattro-formaggi.jpg',
    'la-quattro-fromaggi': 'la-quattro-formaggi.jpg',
    'la-calabrese': 'la-calabrese.jpg',
    'la-margherita': 'la-margherita-3d.webp',
    'bruschetta-burrata-pesto': 'bruschetta-burrata-pesto.jpg',
    'bruschetta-saumon-fume': 'bruschetta-saumon-fume.jpg',
    'mozzarella-caprese': 'mozzarella-caprese.jpg',
    'caponata-sicilienne-burrata': 'caponata-burrata.jpg',
    'panna-cotta-aux-fruits-rouges': 'panna-cotta-fruits-rouges.jpg',
    'panna-cotta-au-caramel-beurre-sale': 'panna-cotta-caramel.jpg',
    'tiramisu': 'tiramisu.jpg',
    'lasagnes-du-chef': 'lasagnes-du-chef.jpg',
    'gnocchi-al-pesto-verde': 'gnocchi-pesto-verde.jpg',
    'spaghetti-a-la-carbonara': 'spaghetti-carbonara.jpg',
    'spaghetti-a-la-bolognaise': 'spaghetti-bolognaise.jpg',
}


class Command(BaseCommand):
    help = 'Synchronize bundled Pizza Vitti plate photos with existing products.'

    def handle(self, *args, **options):
        updated = 0
        for product in Product.objects.all().only('id', 'slug', 'external_image'):
            filename = PRODUCT_PHOTOS.get(product.slug)
            if not filename:
                continue
            image_path = f'/static/shop/img/products/{filename}'
            if product.external_image == image_path:
                continue
            Product.objects.filter(pk=product.pk).update(external_image=image_path)
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Synchronized product photos for {updated} product(s).'
        ))
