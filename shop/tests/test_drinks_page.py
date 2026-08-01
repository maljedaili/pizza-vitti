from django.core.management import call_command
from django.test import TestCase

from shop.models import Category, Product, SiteConfiguration
from shop.translations import PAGE_SLUGS


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
        self.assertContains(response, 'class="footer-payment-card"')
        self.assertContains(response, 'class="payment-brands"')
        self.assertNotContains(response, 'payment-cards-visa-mastercard-cb.png')
        self.assertNotContains(response, 'data-drinks-nav')
        self.assertContains(response, '/static/shop/img/drinks/cafe-allonge.webp')
        self.assertContains(response, '/static/shop/img/drinks/vins-rouges.webp')
        self.assertContains(response, '/static/shop/img/drinks/vins-blancs.webp')
        self.assertContains(response, 'id="cat-carte-des-vins-rouges"')
        self.assertContains(response, 'id="cat-carte-des-vins-blancs"')
        self.assertContains(response, 'data-age-restricted')
        self.assertContains(response, 'Avez-vous 18 ans ou plus')
        self.assertContains(response, 'name="qty"')
        self.assertContains(response, '"@type": "Menu"')
        self.assertNotContains(response, 'id="cat-birre"')
        self.assertContains(response, 'Moretti 33cl')

    def test_alcohol_requires_server_side_age_confirmation(self):
        wine = Product.objects.get(name='Chianti')
        target = '/fr/menu/boissons/'

        rejected = self.client.post(
            f'/panier/ajouter/{wine.id}/',
            {'qty': 1, 'next': target},
        )
        self.assertRedirects(rejected, target)
        self.assertNotIn(str(wine.id), self.client.session.get('cart', {}))

        accepted = self.client.post(
            f'/panier/ajouter/{wine.id}/',
            {'qty': 1, 'next': target, 'age_confirmed': '1'},
        )
        self.assertRedirects(accepted, target)
        self.assertEqual(self.client.session['cart'][str(wine.id)], 1)
        self.assertTrue(self.client.session['alcohol_age_verified'])

    def test_age_error_uses_selected_language(self):
        wine = Product.objects.get(name='Chianti')
        response = self.client.post(
            f'/panier/ajouter/{wine.id}/',
            {'qty': 1, 'next': '/en/menu/boissons/'},
            follow=True,
        )

        self.assertContains(response, 'You must confirm that you are 18 or over to order alcohol.')

    def test_english_and_arabic_copy(self):
        english = self.client.get('/en/menu/boissons/')
        arabic = self.client.get('/ar/menu/boissons/')

        self.assertContains(english, '<h1>Drinks</h1>', html=True)
        self.assertContains(english, 'Soft drinks, beers, wines, aperitifs, digestifs, coffees and teas.')
        self.assertNotContains(english, '<h1>Boissons</h1>', html=True)
        self.assertContains(arabic, '<h1>المشروبات</h1>', html=True)
        self.assertContains(arabic, 'dir="rtl"')
        self.assertContains(english, 'Are you 18 or over?')
        self.assertContains(arabic, 'هل عمرك 18 عاماً أو أكثر؟')
        self.assertNotContains(english, 'Avez-vous 18 ans ou plus')

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

    def test_all_localized_public_pages_render(self):
        for language in ('fr', 'en', 'es', 'it', 'pt', 'nl', 'zh', 'ja', 'ar'):
            for page in ('home', 'menu', 'booking', 'reviews', 'gallery', 'contact', 'cart'):
                slug = PAGE_SLUGS[page][language]
                path = f'/{language}/{slug}/' if slug else f'/{language}/'
                with self.subTest(language=language, page=page):
                    self.assertEqual(self.client.get(path).status_code, 200)

    def test_shared_public_interface_is_translated(self):
        english_booking = self.client.get('/en/booking/')
        english_contact = self.client.get('/en/contact/')
        english_drinks = self.client.get('/en/menu/boissons/')

        self.assertContains(english_booking, 'Book · Pizza Vitti')
        self.assertContains(english_booking, '>Guests<')
        self.assertContains(english_contact, '<h1>Contact</h1>', html=True)
        self.assertContains(english_drinks, 'Quantity · Café')
        self.assertNotContains(english_booking, 'Votre demande')
        self.assertNotContains(english_contact, 'Nous contacter')
