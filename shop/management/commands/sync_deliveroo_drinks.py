from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Category, Product


DELIVEROO_DRINKS = [
    ('Coca-Cola 33cl', 'Canette 33cl.', '4.00', '33cl'),
    ('Coca-Cola zéro 33cl', 'Canette 33cl.', '4.00', '33cl'),
    ('Coca-Cola Cherry 33cl', 'Canette 33cl.', '4.00', '33cl'),
    ('Limonade 33cl', 'Limonade 33cl.', '4.00', '33cl'),
    ('Ice Tea 33cl', 'Canette 33cl.', '4.00', '33cl'),
    ('Orangina 33cl', 'Canette 33cl.', '4.00', '33cl'),
    ("Jus d'orange 25cl", "Jus d'orange 25cl.", '4.00', '25cl'),
    ('Jus de pomme 25cl', 'Jus de pomme 25cl.', '4.00', '25cl'),
    ("Jus d'ananas 25cl", "Jus d'ananas 25cl.", '4.00', '25cl'),
    ("Jus d'abricot 25cl", "Jus d'abricot 25cl.", '4.00', '25cl'),
    ('Eau minérale Ogeu 50cl', 'Bouteille 50cl.', '3.50', '50cl'),
    ('Eau minérale Ogeu 1L', 'Bouteille 1L.', '4.50', '1L'),
    ('Sprite 33cl', 'Canette 33cl.', '4.00', '33cl'),
]


class Command(BaseCommand):
    help = 'Synchronize the soft-drink menu with the Pizza Vitti Deliveroo listing.'

    def handle(self, *args, **options):
        category, _ = Category.objects.get_or_create(
            slug='analcolici',
            defaults={'name': 'Boissons', 'order': 23, 'is_active': True},
        )
        Category.objects.filter(pk=category.pk).update(
            name='Boissons',
            is_active=True,
        )

        listed_names = []
        for order, (name, description, price, unit) in enumerate(DELIVEROO_DRINKS):
            listed_names.append(name)
            Product.objects.update_or_create(
                name=name,
                defaults={
                    'category': category,
                    'description': description,
                    'price': Decimal(price),
                    'unit': unit,
                    'badge': 'Boisson',
                    'stock': 100,
                    'is_available': True,
                    'is_featured': False,
                    'professional_only': False,
                    'meta_title': f'{name} | Pizza Vitti Bordeaux',
                    'meta_description': description,
                },
            )

        hidden = Product.objects.filter(category=category).exclude(
            name__in=listed_names,
        ).update(is_available=False)
        self.stdout.write(self.style.SUCCESS(
            f'Synchronized {len(listed_names)} Deliveroo drinks; hid {hidden} older item(s).'
        ))
