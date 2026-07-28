from django.core.management import call_command
from django.test import TestCase

from shop.models import Category, Product


class SyncDeliverooDrinksCommandTests(TestCase):
    def test_matches_the_deliveroo_soft_drink_listing(self):
        category = Category.objects.create(
            name='Analcolici',
            slug='analcolici',
            order=23,
        )
        old_drink = Product.objects.create(
            category=category,
            name='Diabolo',
            description='Ancienne boisson',
            price='4.50',
        )

        call_command('sync_deliveroo_drinks')

        category.refresh_from_db()
        old_drink.refresh_from_db()
        self.assertEqual(category.name, 'Boissons')
        self.assertFalse(old_drink.is_available)
        self.assertEqual(
            Product.objects.filter(category=category, is_available=True).count(),
            13,
        )
        ogeu = Product.objects.get(name='Eau minérale Ogeu 1L')
        self.assertEqual(str(ogeu.price), '4.50')
        self.assertEqual(ogeu.unit, '1L')

    def test_is_safe_to_run_repeatedly(self):
        call_command('sync_deliveroo_drinks')
        call_command('sync_deliveroo_drinks')

        self.assertEqual(
            Product.objects.filter(
                category__slug='analcolici',
                is_available=True,
            ).count(),
            13,
        )
