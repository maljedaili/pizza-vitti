from django.core.management import call_command
from django.test import TestCase

from shop.models import Category, Product


class SyncDeliverooMenuCommandTests(TestCase):
    def test_matches_deliveroo_and_preserves_other_categories(self):
        pizza_category = Category.objects.create(name='Nos Pizza', slug='nos-pizza')
        Product.objects.create(
            category=pizza_category,
            name='La Margherita',
            slug='la-margherita',
            description='Ancienne recette',
            price='11.50',
        )
        other_category = Category.objects.create(name='Desserts', slug='desserts')
        dessert = Product.objects.create(
            category=other_category,
            name='Tiramisu',
            description='Recette maison',
            price='7.00',
        )

        call_command('sync_deliveroo_menu')

        dessert.refresh_from_db()
        margherita = Product.objects.get(slug='la-margherita')
        self.assertTrue(dessert.is_available)
        self.assertEqual(str(margherita.price), '12.50')
        self.assertEqual(margherita.unit, 'pizza 31cm')
        self.assertEqual(
            Product.objects.filter(category=pizza_category, is_available=True).count(),
            16,
        )
        self.assertEqual(
            Product.objects.filter(category__slug='analcolici', is_available=True).count(),
            13,
        )
        self.assertEqual(
            Product.objects.filter(category__slug__startswith='carte-des-vins-', is_available=True).count(),
            8,
        )
        self.assertEqual(
            Product.objects.filter(category__slug='birre', is_available=True).count(),
            2,
        )

    def test_assigns_authentic_and_category_photos(self):
        call_command('sync_deliveroo_menu')

        regina = Product.objects.get(slug='la-regina')
        coke = Product.objects.get(name='Coca-Cola 33cl')
        wine = Product.objects.get(name='Chianti', category__slug='carte-des-vins-rouges')
        white_wine = Product.objects.get(name='Sélection Pizza Vitti Blanc', category__slug='carte-des-vins-blancs')
        beer = Product.objects.get(name='Peroni 33cl')
        self.assertIn('deliveroo-la-regina.webp', regina.external_image)
        self.assertIn('deliveroo-soft-drinks.webp', coke.external_image)
        self.assertIn('vins-rouges.webp', wine.external_image)
        self.assertIn('vins-blancs.webp', white_wine.external_image)
        self.assertIn('deliveroo-beers.webp', beer.external_image)

    def test_is_safe_to_run_repeatedly(self):
        call_command('sync_deliveroo_menu')
        call_command('sync_deliveroo_menu')

        self.assertEqual(
            Product.objects.filter(category__slug='nos-pizza', is_available=True).count(),
            16,
        )

    def test_reuses_production_category_when_its_slug_was_already_normalized(self):
        existing = Category.objects.create(name='Nos Pizzas', slug='nos-pizzas')

        call_command('sync_deliveroo_menu')

        self.assertEqual(Category.objects.filter(name__iexact='Nos Pizzas').count(), 1)
        self.assertEqual(Product.objects.filter(category=existing, is_available=True).count(), 16)
