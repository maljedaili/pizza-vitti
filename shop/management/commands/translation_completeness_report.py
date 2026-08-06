from django.core.management.base import BaseCommand

from shop.models import Category, CategoryTranslation, Product, ProductTranslation
from shop.translations import LANGUAGE_OPTIONS


class Command(BaseCommand):
    help = 'Report complete menu translations by language for SEO indexing decisions.'

    def handle(self, *args, **options):
        products = Product.objects.filter(professional_only=False).count()
        categories = Category.objects.filter(is_active=True).count()
        self.stdout.write(f'French source: {products} products, {categories} active categories')
        for code, _short, label, _href in LANGUAGE_OPTIONS:
            if code == 'fr':
                continue
            translated_products = ProductTranslation.objects.filter(
                language=code, product__professional_only=False,
            ).exclude(name='').exclude(description='').values('product_id').distinct().count()
            translated_categories = CategoryTranslation.objects.filter(
                language=code, category__is_active=True,
            ).exclude(name='').exclude(description='').values('category_id').distinct().count()
            self.stdout.write(
                f'{label} [{code}]: products {translated_products}/{products}; '
                f'categories {translated_categories}/{categories}'
            )
