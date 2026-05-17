from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, BlogPost
from .translations import LANGUAGE_OPTIONS

class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'
    def items(self):
        base = ['shop:home','shop:boutique','shop:blog','shop:contact','shop:booking','shop:reviews','shop:gallery']
        localized = [href for code, label, name, href in LANGUAGE_OPTIONS]
        return base + localized
    def location(self, item):
        if isinstance(item, str) and item.startswith('/'):
            return item
        return reverse(item)
class ProductSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9
    def items(self): return Product.objects.filter(is_available=True)
class BlogSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.7
    def items(self): return BlogPost.objects.filter(is_published=True)
