from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand

from shop.models import Category, Product


PIZZA_IMAGE_ROOT = '/static/shop/img/products/'
PIZZAS = [
    ('la-regina', (), 'La Regina', 'Sauce tomate / mozzarella fior di latte / jambon blanc cuit aux herbes / champignons / olives / origan', '14.90', 'deliveroo-la-regina.webp'),
    ('la-vesuvio', (), 'La Vesuvio', 'Sauce tomate / mozzarella di bufala / tomates cerises / origan / basilic / copeaux de parmesan / pesto verde', '15.50', 'deliveroo-la-vesuvio.webp'),
    ('ladriana', ('l-adriana',), "L'Adriana", 'Crème fraîche / mozzarella fior di latte / pancetta / tomates cerises / champignons / oignons', '14.90', 'deliveroo-l-adriana.webp'),
    ('la-napoletana', (), 'La Napoletana', 'Sauce tomate / mozzarella fior di latte / anchois marinés / câpres / olives noires', '14.90', 'deliveroo-la-napoletana.webp'),
    ('la-fumee', ('la-montazio-fumee',), 'La Montazio Fumée', 'Sauce tomate / mozzarella fior di latte / speck / scamorza fumée / éclats de noix', '16.80', 'la-fumee.jpg'),
    ('la-margherita', (), 'La Margherita', 'Sauce tomate / mozzarella fior di latte / tomates cerises / olives / basilic', '12.50', 'la-margherita-3d.webp'),
    ('la-quattro-stagioni', ('la-quattro-saisons',), 'La Quattro Saisons', 'Sauce tomate / mozzarella fior di latte / jambon blanc cuit aux herbes / artichauts / champignons / olives / origan', '15.90', 'la-quattro-stagioni.jpg'),
    ('la-quattro-fromaggi', ('la-quattro-formaggi',), 'La Quattro Formaggi', 'Mozzarella fior di latte / gorgonzola / scamorza / copeaux de parmesan / basilic / tomates cerises', '15.90', 'la-quattro-formaggi.jpg'),
    ('la-calabrese', (), 'La Calabrese', 'Sauce tomate / mozzarella fior di latte / oignons rouges / poivrons / spianata calabra / piments doux / olives noires', '15.90', 'la-calabrese.jpg'),
    ('la-calzone', (), 'La Calzone', 'Sauce tomate / mozzarella fior di latte / œuf / jambon cuit aux herbes / champignons / parmesan', '15.50', 'la-margherita.jpg'),
    ('la-tartuffo', ('la-tartufo',), 'La Tartufo', 'Jambon cuit aux herbes / crème de truffe / scamorza / roquette / tomates cerises / copeaux de parmesan', '18.50', 'la-tartuffo.jpg'),
    ('la-salmone', (), 'La Salmone', 'Crème fraîche / mozzarella fior di latte / saumon fumé / zestes de citron / tomates cerises / olives / pesto verde', '16.90', 'la-salmone.jpg'),
    ('la-parma-et-burrata', ('la-parma',), 'La Parma', 'Sauce tomate / mozzarella fior di latte / jambon de Parme (20 mois) / tomates cerises / roquette / copeaux de parmesan', '17.00', 'la-parma.jpg'),
    ('la-vegetariana', (), 'La Vegetariana', 'Sauce tomate / mozzarella fior di latte / artichaut alla romana / aubergines, courgettes et poivrons grillés / roquette / pesto verde', '15.90', 'la-vegetariana.jpg'),
    ('la-pescatora', (), 'La Pescatora', 'Sauce tomate / mozzarella fior di latte / thon / olives / oignons rouges / tomates cerises / câpres / roquette', '15.90', 'la-pescatora.jpg'),
    ('la-cabri', (), 'La Cabri', 'Crème fraîche / mozzarella fior di latte / jambon cuit aux herbes / fromage de chèvre / miel / olives / roquette / tomates cerises', '15.50', 'la-cabri.jpg'),
]

WINES = [
    ('Sélection Pizza Vitti rouge', 'Bouteille.', '22.00', 'bouteille'),
    ('Sélection Pizza Vitti Blanc', 'Bouteille.', '22.00', 'bouteille'),
    ('Sélection Pizza Vitti rosé', 'Bouteille.', '22.00', 'bouteille'),
    ('Chianti', 'Toscane / bouteille.', '28.00', 'bouteille'),
    ('Primitivo / Salento', 'Pouilles / bouteille.', '32.00', 'bouteille'),
    ('Lambrusco rouge', 'Bouteille.', '24.00', 'bouteille'),
    ('Lambrusco rosé', 'Bouteille.', '24.00', 'bouteille'),
    ("Moscato d'Asti", 'Bouteille.', '30.00', 'bouteille'),
]

WINE_GROUPS = [
    ('carte-des-vins-rouges', 'Carte des vins – rouges', 'vins-rouges.webp', WINES[0:1] + WINES[3:6]),
    ('carte-des-vins-blancs', 'Carte des vins – blancs', 'vins-blancs.webp', WINES[1:2]),
    ('carte-des-vins-roses', 'Carte des vins – rosés', 'vins-roses.webp', WINES[2:3] + WINES[6:7]),
    ('carte-des-vins-petillants', 'Carte des vins – pétillants', 'vins-petillants.webp', WINES[7:8]),
]

BEERS = [
    ('Peroni 33cl', 'Bière italienne 33cl.', '5.00', '33cl'),
    ('Moretti 33cl', 'Bière italienne 33cl.', '5.00', '33cl'),
]


def sync_named_products(category, products, badge, image_path):
    listed_names = []
    for name, description, price, unit in products:
        listed_names.append(name)
        product = Product.objects.filter(name=name).first()
        if product is None:
            product = Product(name=name)
        product.category = category
        product.name = name
        product.description = description
        product.price = Decimal(price)
        product.unit = unit
        product.external_image = image_path
        product.badge = badge
        product.stock = 100
        product.is_available = True
        product.availability_status = 'available'
        product.professional_only = False
        product.meta_title = f'{name} | Pizza Vitti Bordeaux'
        product.meta_description = description[:160]
        product.save()

    return Product.objects.filter(category=category).exclude(
        name__in=listed_names,
    ).update(is_available=False, availability_status='sold_out')


class Command(BaseCommand):
    help = 'Synchronize the public menu with the Pizza Vitti Deliveroo listing.'

    def handle(self, *args, **options):
        pizza_category = (
            Category.objects.filter(name__iexact='Nos Pizzas').first()
            or Category.objects.filter(name__iexact='Nos Pizza').first()
            or Category.objects.filter(slug='nos-pizza').first()
        )
        if pizza_category is None:
            pizza_category = Category.objects.create(
                name='Nos Pizzas', slug='nos-pizza', order=11, is_active=True,
            )
        pizza_category.name = 'Nos Pizzas'
        pizza_category.is_active = True
        pizza_category.save(update_fields=['name', 'is_active', 'updated_at'])

        pizza_ids = []
        for slug, aliases, name, description, price, filename in PIZZAS:
            product = Product.objects.filter(slug__in=(slug, *aliases)).first()
            if product is None:
                product = Product(slug=slug)
            product.category = pizza_category
            product.name = name
            product.description = description
            product.price = Decimal(price)
            product.unit = 'pizza 31cm'
            product.external_image = f'{PIZZA_IMAGE_ROOT}{filename}'
            product.badge = 'Pizza'
            product.stock = 100
            product.is_available = True
            product.availability_status = 'available'
            product.professional_only = False
            product.meta_title = f'{name} | Pizza Vitti Bordeaux'
            product.meta_description = description[:160]
            product.save()
            pizza_ids.append(product.pk)

        hidden_pizzas = Product.objects.filter(category=pizza_category).exclude(
            pk__in=pizza_ids,
        ).update(is_available=False, availability_status='sold_out')

        call_command('sync_deliveroo_drinks')
        drinks = Product.objects.filter(category__slug='analcolici', is_available=True)
        drinks.update(external_image=f'{PIZZA_IMAGE_ROOT}deliveroo-soft-drinks.webp')

        hidden_wines = 0
        for order, (slug, name, filename, wines) in enumerate(WINE_GROUPS, start=106):
            wine_category, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'order': order, 'is_active': True},
            )
            wine_category.name = name
            wine_category.order = order
            wine_category.is_active = True
            wine_category.static_image_path = f'/static/shop/img/drinks/{filename}'
            wine_category.save(update_fields=['name', 'order', 'is_active', 'static_image_path', 'updated_at'])
            hidden_wines += sync_named_products(
                wine_category,
                wines,
                'Vin · 18+',
                wine_category.static_image_path,
            )

        Product.objects.filter(category__slug='vins-deliveroo').update(
            is_available=False,
            availability_status='sold_out',
        )

        beer_category, _ = Category.objects.get_or_create(
            slug='birre',
            defaults={'name': 'Birre', 'order': 3, 'is_active': True},
        )
        beer_category.is_active = True
        beer_category.save(update_fields=['is_active', 'updated_at'])
        hidden_beers = sync_named_products(
            beer_category,
            BEERS,
            'Bière',
            f'{PIZZA_IMAGE_ROOT}deliveroo-beers.webp',
        )

        self.stdout.write(self.style.SUCCESS(
            'Synchronized Deliveroo menu: '
            f'{len(PIZZAS)} pizzas, {drinks.count()} drinks, '
            f'{len(WINES)} wines and {len(BEERS)} beers; '
            f'hid {hidden_pizzas + hidden_wines + hidden_beers} older item(s).'
        ))
