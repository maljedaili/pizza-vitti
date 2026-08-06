from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, ProductTranslation, BlogPost, LocalSEOPage
from .translations import LANGUAGE_OPTIONS, localized_url
from .translation_quality import is_complete_product_translation

PUBLIC_PAGE_KEYS = ('home', 'menu', 'booking', 'reviews', 'gallery', 'blog', 'contact')
MENU_GROUP_SLUGS = ('pizzas', 'pastas', 'antipasti', 'bambino', 'douceurs', 'boissons')

class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    def items(self):
        items = []
        for code, _label, _name, _href in LANGUAGE_OPTIONS:
            items.extend(('page', code, page) for page in PUBLIC_PAGE_KEYS)
            items.extend(('group', code, group) for group in MENU_GROUP_SLUGS)
        return items
    def location(self, item):
        kind, language, value = item
        if kind == 'group':
            return reverse('shop:localized_menu_group', args=[language, value])
        return localized_url(value, language)

class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9
    def items(self):
        products = Product.objects.filter(
            is_available=True,
            professional_only=False,
        ).only('id', 'slug', 'updated_at')
        complete_by_product = {}
        for translation in ProductTranslation.objects.filter(
            product__in=products,
        ).select_related('product'):
            if is_complete_product_translation(translation):
                complete_by_product.setdefault(translation.product_id, set()).add(translation.language)
        return [
            (product, code)
            for product in products
            for code, _label, _name, _href in LANGUAGE_OPTIONS
            if code == 'fr' or code in complete_by_product.get(product.id, set())
        ]
    def location(self, item):
        product, language = item
        return reverse('shop:localized_product_detail', args=[language, product.slug])
    def lastmod(self, item):
        product, _language = item
        return product.updated_at

class BlogSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7
    def items(self): return BlogPost.objects.filter(is_published=True)
    def lastmod(self, item): return item.updated_at


class LocalSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return LocalSEOPage.objects.filter(is_published=True)

    def location(self, item):
        return reverse('shop:local_seo_page', args=[item.slug])

    def lastmod(self, item):
        return item.updated_at
