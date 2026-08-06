from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from shop.models import Category, LocalSEOPage, Product, ProductTranslation
from shop.seo import absolute_public_url


class SEOUpgradeTests(TestCase):
    def test_public_url_removes_query_and_uses_primary_origin(self):
        self.assertEqual(
            absolute_public_url('/fr/menu/pizzas/?utm_source=test'),
            'https://pizza-vitti.kayen.fr/fr/menu/pizzas/',
        )

    def test_local_page_has_metadata_breadcrumb_and_schema(self):
        page = LocalSEOPage.objects.create(
            title='Pizzeria à Bordeaux', slug='pizzeria-bordeaux-test',
            introduction='Introduction locale.', body='Contenu original.',
            meta_title='Pizzeria Bordeaux | Pizza Vitti',
            meta_description='Une description locale unique pour Pizza Vitti à Bordeaux.',
            is_published=True,
        )
        response = self.client.get(f'/fr/{page.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, page.meta_title)
        self.assertContains(response, 'BreadcrumbList')
        self.assertContains(response, 'http://testserver/fr/pizzeria-bordeaux-test/')

    @override_settings(ENVIRONMENT='production', ALLOW_DEMO_DATA=False)
    def test_demo_seed_refuses_production(self):
        with self.assertRaises(CommandError):
            call_command('seed_if_empty')

    @override_settings(
        GOOGLE_SITE_VERIFICATION='google-code', BING_SITE_VERIFICATION='bing-code',
        GA4_MEASUREMENT_ID='G-TEST', GOOGLE_TAG_MANAGER_ID='', MICROSOFT_CLARITY_ID='',
    )
    def test_verification_and_analytics_are_conditional(self):
        response = self.client.get('/fr/')
        self.assertContains(response, 'name="google-site-verification" content="google-code"')
        self.assertContains(response, 'name="msvalidate.01" content="bing-code"')
        self.assertContains(response, 'googletagmanager.com/gtag/js?id=G-TEST')

    def test_robots_excludes_private_routes(self):
        response = self.client.get('/robots.txt')
        self.assertContains(response, 'Disallow: /mon-compte/')
        self.assertContains(response, 'Disallow: /facture/')
        self.assertContains(response, 'Sitemap: https://pizza-vitti.kayen.fr/sitemap.xml')

    def test_untranslated_product_is_noindex_and_not_advertised_in_hreflang(self):
        category = Category.objects.create(name='Nos Pizzas', slug='nos-pizzas-seo')
        product = Product.objects.create(
            category=category, name='Pizza test SEO', slug='pizza-test-seo',
            description='Description française unique.', price='12.00',
        )
        response = self.client.get(f'/en/product/{product.slug}/')
        self.assertContains(response, '<meta name="robots" content="noindex,follow">', html=True)
        self.assertContains(response, 'name="translation-status" content="incomplete"')
        self.assertNotContains(response, 'hreflang="en"')
        self.assertNotContains(response, '<link rel="canonical"')

    def test_complete_product_translation_is_indexable_and_reciprocal(self):
        category = Category.objects.create(name='Nos Pizzas', slug='nos-pizzas-translated')
        product = Product.objects.create(
            category=category, name='Pizza traduite', slug='pizza-traduite',
            description='Description française.', price='12.00',
        )
        ProductTranslation.objects.create(
            product=product, language='en', name='Translated pizza',
            description='A complete and useful English product description.',
        )
        response = self.client.get(f'/en/product/{product.slug}/')
        self.assertNotContains(response, 'name="translation-status"')
        self.assertNotContains(response, 'content="noindex,follow"')
        self.assertContains(response, f'hreflang="fr" href="http://testserver/fr/product/{product.slug}/"')
        self.assertContains(response, f'hreflang="en" href="http://testserver/en/product/{product.slug}/"')
