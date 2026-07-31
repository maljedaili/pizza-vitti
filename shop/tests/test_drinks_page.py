from django.core.management import call_command
from django.test import TestCase

from shop.models import Category, Product, SiteConfiguration


class DrinksPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Category.objects.create(name='Caffè - Thé', slug='caffe-the', order=24)
        for name in ('Café', 'Café allongé', 'Café double', 'Cappuccino', 'Chocolat chaud', 'Thés et Infusions'):
            Product.objects.create(
                category=Category.objects.get(slug='caffe-the'),
                name=name,
                description='Boisson chaude.',
                price='3.50',
            )
        call_command('sync_deliveroo_menu')
        call_command('sync_drinks_page')

    def test_french_page_reuses_the_standard_menu_design_and_local_images(self):
        response = self.client.get('/fr/menu/boissons/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="shop-hero menu-hero reveal"')
        self.assertContains(response, '/static/shop/img/drinks/shirley-temple-cosmopolitan.jpg')
        self.assertNotContains(response, 'drinks-menu-hero')
        self.assertContains(response, 'class="toolbar menu-toolbar"')
        self.assertContains(response, 'class="menu-category grouped-menu-section drinks-menu-grid"')
        self.assertContains(response, 'class="product-card reveal"', count=29)
        self.assertContains(response, 'payment-cards-visa-mastercard-cb.png')
        self.assertNotContains(response, 'data-drinks-nav')
        self.assertContains(response, '/static/shop/img/drinks/cafe-allonge.webp')
        self.assertContains(response, 'name="qty"')
        self.assertContains(response, '"@type": "Menu"')
        self.assertNotContains(response, 'id="cat-birre"')
        self.assertContains(response, 'Moretti 33cl')

    def test_english_and_arabic_copy(self):
        english = self.client.get('/en/menu/boissons/')
        arabic = self.client.get('/ar/menu/boissons/')

        self.assertContains(english, '<h1>Drinks</h1>', html=True)
        self.assertContains(english, 'Soft drinks, beers, wines, aperitifs, digestifs, coffees and teas.')
        self.assertNotContains(english, '<h1>Boissons</h1>', html=True)
        self.assertContains(arabic, '<h1>المشروبات</h1>', html=True)
        self.assertContains(arabic, 'dir="rtl"')

    def test_language_switch_keeps_the_visitor_on_the_drinks_page(self):
        response = self.client.get('/fr/menu/boissons/')

        self.assertContains(response, 'href="/en/menu/boissons/"')
        self.assertContains(response, 'href="/es/menu/boissons/"')
        self.assertContains(response, 'href="/ar/menu/boissons/"')

    def test_arabic_home_translates_shared_public_content(self):
        response = self.client.get('/ar/')

        self.assertContains(response, 'مطعم إيطالي في بوردو')
        self.assertContains(response, 'حسابي')
        self.assertContains(response, 'الاثنين')
        self.assertContains(response, 'تم إنشاء الموقع بواسطة')
        self.assertNotContains(response, 'Restaurant italien à Bordeaux')
        self.assertNotContains(response, 'Mon compte')

    def test_admin_drinks_photo_is_used_on_home_and_menu_banner(self):
        site = SiteConfiguration.load()
        site.drinks_banner_image = 'banners/admin-drinks.jpg'
        site.save(update_fields=['drinks_banner_image'])

        home = self.client.get('/fr/')
        drinks = self.client.get('/fr/menu/boissons/')

        self.assertContains(home, '/media/banners/admin-drinks.jpg')
        self.assertContains(drinks, "url('/media/banners/admin-drinks.jpg')")

    def test_command_is_idempotent_and_keeps_requested_order(self):
        call_command('sync_drinks_page')
        call_command('sync_drinks_page')

        categories = list(Category.objects.filter(
            slug__in=('caffe-the', 'cafe-allonge', 'digestifs'),
        ).order_by('order').values_list('slug', flat=True))
        self.assertEqual(categories, ['caffe-the', 'cafe-allonge', 'digestifs'])
