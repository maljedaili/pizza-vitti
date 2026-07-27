from django.core.management import call_command
from django.test import TestCase

from shop.models import Category, Product


class SyncProductPhotosCommandTests(TestCase):
    def test_updates_existing_products_after_the_menu_has_been_seeded(self):
        category = Category.objects.create(name='Nos Pizza', slug='nos-pizza')
        margherita = Product.objects.create(
            category=category,
            name='La Margherita',
            slug='la-margherita',
            description='Pizza',
            external_image='/static/shop/img/hero/menu-pizza-vitti.jpg',
        )
        fromaggi = Product.objects.create(
            category=category,
            name='La Quattro fromaggi',
            slug='la-quattro-fromaggi',
            description='Pizza',
            external_image='/static/shop/img/hero/menu-pizza-vitti.jpg',
        )

        call_command('sync_product_photos')

        margherita.refresh_from_db()
        fromaggi.refresh_from_db()
        self.assertEqual(
            margherita.external_image,
            '/static/shop/img/products/la-margherita.jpg',
        )
        self.assertEqual(
            fromaggi.external_image,
            '/static/shop/img/products/la-quattro-formaggi.jpg',
        )

    def test_is_safe_to_run_repeatedly(self):
        category = Category.objects.create(name='Nos Pizza', slug='nos-pizza')
        product = Product.objects.create(
            category=category,
            name='La Regina',
            slug='la-regina',
            description='Pizza',
            external_image='/static/shop/img/products/la-regina.jpg',
        )

        call_command('sync_product_photos')

        product.refresh_from_db()
        self.assertEqual(
            product.external_image,
            '/static/shop/img/products/la-regina.jpg',
        )
