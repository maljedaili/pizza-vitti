from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shop.models import (
    Category,
    CustomerMessage,
    Favorite,
    LoyaltyRedemption,
    LoyaltyReward,
    NewsletterSubscriber,
    OpeningPeriod,
    Order,
    OrderItem,
    Product,
    Reservation,
    StaffMember,
    StaffShift,
)


class AndroidAppVerificationTests(TestCase):
    def test_manifest_opens_the_public_storefront(self):
        response = self.client.get(reverse('manifest_webmanifest'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['id'], '/fr/')
        self.assertEqual(response.json()['start_url'], '/fr/')

    def test_service_worker_refreshes_the_storefront_cache(self):
        response = self.client.get(reverse('service_worker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pizza-vitti-app-v8")
        self.assertEqual(
            response['Cache-Control'],
            'no-cache, no-store, must-revalidate',
        )

    @override_settings(
        ANDROID_APP_PACKAGE='kayen.fr',
        ANDROID_CERT_SHA256_FINGERPRINTS=['AA:BB:CC', '11:22:33'],
    )
    def test_asset_links_exposes_package_and_signing_fingerprints(self):
        response = self.client.get(reverse('android_asset_links'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.json(), [{
            'relation': ['delegate_permission/common.handle_all_urls'],
            'target': {
                'namespace': 'android_app',
                'package_name': 'kayen.fr',
                'sha256_cert_fingerprints': ['AA:BB:CC', '11:22:33'],
            },
        }])

    @override_settings(ANDROID_CERT_SHA256_FINGERPRINTS=[])
    def test_asset_links_is_empty_until_play_fingerprint_is_configured(self):
        response = self.client.get(reverse('android_asset_links'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


@override_settings(LOYALTY_ENABLED=True)
class CustomerLoyaltyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='cliente@example.com',
            email='cliente@example.com',
            password='SecurePass123',
            first_name='Camille',
            last_name='Martin',
        )
        self.category = Category.objects.create(name='Nos Pizza', slug='nos-pizza')
        self.product = Product.objects.create(
            category=self.category,
            name='Margherita fidélité',
            slug='margherita-fidelite',
            description='Pizza de test',
            price=Decimal('12.00'),
        )
        self.reward = LoyaltyReward.objects.create(
            name='Cadeau dessert',
            reward_type='free_dessert',
            pizzas_required=5,
            is_active=True,
        )

    def create_order(self, quantity, number):
        order = Order.objects.create(
            order_number=number,
            user=self.user,
            customer_name='Camille Martin',
            email=self.user.email,
            total=quantity * self.product.price,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            name=self.product.name,
            quantity=quantity,
            unit_price=self.product.price,
            line_total=quantity * self.product.price,
        )
        return order

    def test_signed_in_orders_accumulate_and_unlock_owner_selected_reward(self):
        self.create_order(2, 'PV-LOYALTY-1')
        self.client.force_login(self.user)
        session = self.client.session
        session['cart'] = {str(self.product.id): 3}
        session.save()
        checkout_page = self.client.get(reverse('shop:checkout'))
        checkout_token = self.client.session['checkout_token']
        slot = checkout_page.context['form'].fields['collection_slot'].choices[0][0]

        response = self.client.post(reverse('shop:checkout'), {
            'name': 'Camille Martin',
            'email': self.user.email,
            'phone': '0556421449',
            'collection_slot': slot,
            'payment_method': 'cash',
            'accepted_terms': 'on',
            'checkout_token': checkout_token,
        })

        order = Order.objects.exclude(order_number='PV-LOYALTY-1').get()
        self.assertRedirects(response, order.get_absolute_url())
        self.assertEqual(order.selected_reward, 'Dessert offert')
        redemption = LoyaltyRedemption.objects.get(order=order)
        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.milestone, 5)
        dashboard = self.client.get(reverse('shop:customer_dashboard'))
        self.assertContains(dashboard, '5 pizza(s) achetée(s)')
        self.assertContains(dashboard, '1 cadeau(x) déjà attribué(s)')

    def test_customer_signup_collects_name_for_faster_checkout(self):
        response = self.client.post(reverse('account_signup'), {
            'first_name': 'Nina',
            'last_name': 'Rossi',
            'email': 'nina@example.com',
            'password1': 'VittiSecure742!',
            'password2': 'VittiSecure742!',
        })
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email='nina@example.com')
        self.assertEqual(user.first_name, 'Nina')
        self.assertEqual(user.last_name, 'Rossi')

    def test_public_home_links_to_the_android_testing_application(self):
        response = self.client.get(reverse('shop:home'))
        self.assertNotContains(response, 'Google Play en préparation')
        self.assertContains(response, 'class="home-google-play"')
        self.assertContains(response, 'https://play.google.com/store/apps/details?id=kayen.fr')
        self.assertContains(response, 'Site créé par')
        self.assertContains(response, reverse('shop:account_deletion'))

    def test_android_promotion_follows_the_selected_language(self):
        english = self.client.get('/en/home/')
        arabic = self.client.get('/ar/')

        self.assertContains(english, 'The menu and your orders in one app.')
        self.assertContains(english, 'aria-label="Download Pizza Vitti on Google Play"')
        self.assertNotContains(english, 'Le menu et vos commandes dans l’application.')
        self.assertContains(arabic, 'القائمة وطلباتك في تطبيق واحد.')
        self.assertContains(arabic, 'aria-label="تنزيل Pizza Vitti من Google Play"')

    def test_home_and_menu_metadata_follow_the_selected_language(self):
        english_home = self.client.get('/en/home/')
        english_menu = self.client.get('/en/menu/')
        arabic_home = self.client.get('/ar/')

        self.assertContains(english_home, '<title>Italian pizza in Bordeaux | Pizza Vitti</title>', html=True)
        self.assertContains(english_home, 'content="Artisan Italian pizza in Bordeaux.')
        self.assertNotContains(english_home, '<title>Pizza italienne à Bordeaux | Pizza Vitti</title>', html=True)
        self.assertContains(english_menu, '<title>Pizza Vitti Bordeaux menu</title>', html=True)
        self.assertContains(arabic_home, '<title>بيتزا إيطالية في بوردو | Pizza Vitti</title>', html=True)

    def test_opening_hours_and_status_follow_the_selected_language(self):
        english = self.client.get('/en/home/')
        arabic = self.client.get('/ar/')

        self.assertContains(english, 'Monday')
        self.assertContains(english, 'Closed')
        self.assertContains(english, 'aria-label="Ordering information"')
        self.assertContains(english, 'title="Pizza Vitti location in Bordeaux"')
        self.assertNotContains(english, '>Lundi<')
        self.assertNotContains(english, '>Fermé<')
        self.assertContains(arabic, 'الاثنين')
        self.assertContains(arabic, 'مغلق')
        self.assertContains(arabic, 'aria-label="معلومات الطلب"')

    def test_menu_category_cards_follow_the_selected_language(self):
        english_home = self.client.get('/en/home/')
        english_pizzas = self.client.get('/en/menu/pizzas/')
        arabic_home = self.client.get('/ar/')

        self.assertContains(english_home, 'Our pizzas')
        self.assertContains(english_home, 'House-made pizzas with extras')
        self.assertNotContains(english_home, 'Nos pizzas')
        self.assertContains(english_pizzas, '<h1>Our pizzas</h1>', html=True)
        self.assertContains(arabic_home, 'البيتزا')

    def test_public_accessibility_labels_follow_the_selected_language(self):
        english = self.client.get('/en/home/')
        english_gallery = self.client.get('/en/gallery/')
        arabic = self.client.get('/ar/')

        self.assertContains(english, 'aria-label="Open menu"')
        self.assertContains(english, 'aria-label="Accepted payments: Visa, Mastercard and CB"')
        self.assertContains(english, 'aria-label="Follow Pizza Vitti on Instagram"')
        self.assertContains(english, 'aria-label="Pizza Vitti Italian pizza"')
        self.assertNotContains(english, 'aria-label="Ouvrir le menu"')
        self.assertContains(english_gallery, 'alt="Pizza Vitti photo"')
        self.assertContains(arabic, 'aria-label="فتح القائمة"')
        self.assertContains(arabic, 'aria-label="وسائل الدفع المقبولة: Visa وMastercard وCB"')

    def test_product_links_and_controls_preserve_the_selected_language(self):
        english_menu = self.client.get('/en/menu/pizzas/')
        self.assertContains(english_menu, f'/en/product/{self.product.slug}/')

        english_product = self.client.get(f'/en/product/{self.product.slug}/')
        arabic_product = self.client.get(f'/ar/product/{self.product.slug}/')
        self.assertEqual(english_product.status_code, 200)
        self.assertContains(english_product, 'Swipe to rotate')
        self.assertNotContains(english_product, 'Glissez pour tourner')
        self.assertContains(arabic_product, 'اسحب للتدوير')

        self.client.force_login(self.user)
        english_product = self.client.get(f'/en/product/{self.product.slug}/')
        self.assertContains(english_product, 'Add to favourites')

    def test_language_switcher_preserves_the_current_public_page(self):
        english_menu = self.client.get('/en/menu/')
        english_reviews = self.client.get('/en/reviews/')
        english_product = self.client.get(f'/en/product/{self.product.slug}/')

        self.assertContains(english_menu, 'href="/es/menu/"')
        self.assertContains(english_menu, 'href="/ar/menu/"')
        self.assertNotContains(english_menu, 'href="/es/inicio"')
        self.assertContains(english_reviews, 'href="/it/recensioni/"')
        self.assertContains(english_product, f'href="/ar/product/{self.product.slug}/"')

    def test_hreflang_links_match_the_current_page_and_include_default(self):
        menu = self.client.get('/en/menu/')
        product = self.client.get(f'/en/product/{self.product.slug}/')

        self.assertContains(menu, 'hreflang="es" href="http://testserver/es/menu/"')
        self.assertContains(menu, 'hreflang="x-default" href="http://testserver/fr/menu/"')
        self.assertContains(
            product,
            f'hreflang="ar" href="http://testserver/ar/product/{self.product.slug}/"',
        )
        self.assertContains(
            product,
            f'hreflang="x-default" href="http://testserver/fr/product/{self.product.slug}/"',
        )

    def test_product_page_exposes_localized_menu_item_structured_data(self):
        response = self.client.get(f'/en/product/{self.product.slug}/')

        self.assertContains(response, '"@type": "MenuItem"')
        self.assertContains(response, '"@type": "BreadcrumbList"')
        self.assertContains(response, '"price": "12.00"')
        self.assertContains(response, '"priceCurrency": "EUR"')
        self.assertContains(response, '"availability": "https://schema.org/InStock"')
        self.assertContains(response, f'http://testserver/en/product/{self.product.slug}/')

    def test_product_sharing_metadata_uses_the_product_photo(self):
        response = self.client.get(f'/en/product/{self.product.slug}/')
        expected_image = f'http://testserver{self.product.display_image}'

        self.assertContains(response, 'property="og:type" content="product"')
        self.assertContains(response, f'property="og:image" content="{expected_image}"')
        self.assertContains(response, f'name="twitter:image" content="{expected_image}"')
        self.assertContains(response, f'property="og:image:alt" content="{self.product.name}"')

    def test_sitemap_contains_localized_pages_groups_and_products(self):
        response = self.client.get('/sitemap.xml')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '/en/menu/</loc>')
        self.assertContains(response, '/ar/menu/boissons/</loc>')
        self.assertContains(response, f'/en/product/{self.product.slug}/</loc>')
        self.assertContains(response, f'/ja/product/{self.product.slug}/</loc>')
        self.assertNotContains(response, f'/produit/{self.product.slug}/</loc>')

    def test_customer_can_delete_account_and_associated_data(self):
        order = self.create_order(2, 'PV-DELETE-1')
        Favorite.objects.create(user=self.user, product=self.product)
        LoyaltyRedemption.objects.create(
            user=self.user,
            order=order,
            reward=self.reward,
            milestone=5,
        )
        NewsletterSubscriber.objects.create(email=self.user.email)
        Reservation.objects.create(
            name='Camille Martin',
            email=self.user.email,
            date=timezone.localdate() + timedelta(days=1),
            time=timezone.localtime().time(),
        )
        CustomerMessage.objects.create(
            name='Camille Martin',
            email=self.user.email,
            message='Message à supprimer',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('shop:account_deletion'), {
            'action': 'delete_now',
            'confirm': 'yes',
        })

        self.assertRedirects(response, reverse('shop:home'))
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(Favorite.objects.exists())
        self.assertFalse(LoyaltyRedemption.objects.exists())
        self.assertFalse(NewsletterSubscriber.objects.exists())
        self.assertFalse(Reservation.objects.exists())
        self.assertFalse(CustomerMessage.objects.exists())
        order.refresh_from_db()
        self.assertIsNone(order.user)
        self.assertEqual(order.customer_name, 'Compte supprimé')
        self.assertEqual(order.email, '')
        self.assertEqual(order.phone, '')

    def test_public_account_deletion_request_is_recorded(self):
        response = self.client.post(reverse('shop:account_deletion'), {
            'email': 'ancien-client@example.com',
        })
        self.assertRedirects(response, reverse('shop:account_deletion'))
        request_message = CustomerMessage.objects.get(email='ancien-client@example.com')
        self.assertEqual(request_message.subject, 'Suppression de compte Pizza Vitti')

    def test_public_navigation_is_reduced_and_home_prioritizes_ordering(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'Commander à emporter')
        self.assertContains(response, 'Qu’est-ce qui vous ferait plaisir')
        self.assertContains(response, 'pizza-vitti-hero.mp4')
        self.assertContains(response, 'pizza-vitti-hero-mobile.mp4')
        self.assertContains(response, 'class="home-hero hero-video-full reveal"')
        self.assertNotContains(response, 'restaurant-status-band')
        self.assertNotContains(response, 'Les favoris de nos clients')
        self.assertContains(response, 'Assistant Vitti')
        self.assertContains(response, 'Pizza Vitti')
        self.assertNotContains(response, f'<a href="{reverse("shop:home")}">Accueil</a>', html=True)
        self.assertNotContains(response, '>Fidélité</a>')
        self.assertNotContains(response, '>Application</a>')

    def test_mobile_css_keeps_chat_visible_on_menu_first_pages(self):
        from pathlib import Path
        from django.conf import settings

        css = (Path(settings.BASE_DIR) / 'shop/static/shop/dist/site.css').read_text()
        self.assertIn('body.public-site:has(.menu-first) .bot', css)
        self.assertIn('bottom:calc(76px + env(safe-area-inset-bottom))', css)
        self.assertIn('grid-template-columns:118px minmax(0,1fr)', css)

    def test_mobile_order_flow_shows_progress_status_and_total(self):
        session = self.client.session
        session['cart'] = {str(self.product.id): 1}
        session.save()

        cart = self.client.get(reverse('shop:cart'))
        self.assertContains(cart, 'class="checkout-steps"')
        self.assertContains(cart, 'order-status-note')
        self.assertContains(cart, 'Continuer le menu')
        self.assertContains(cart, 'Finaliser la commande · 12,00 €')

        checkout = self.client.get(reverse('shop:checkout'))
        self.assertContains(checkout, 'Coordonnées')
        self.assertContains(checkout, 'autocomplete="name"')
        self.assertContains(checkout, 'autocomplete="email"')
        self.assertContains(checkout, 'autocomplete="tel"')

    def test_order_controls_follow_the_selected_language(self):
        session = self.client.session
        session['cart'] = {str(self.product.id): 1}
        session.save()

        english_menu = self.client.get('/en/menu/')
        self.assertContains(english_menu, 'Full menu')
        self.assertContains(english_menu, 'My order')
        self.assertContains(english_menu, 'aria-label="Close"')
        self.assertNotContains(english_menu, 'Ma commande')

        english_cart = self.client.get('/en/cart/')
        self.assertContains(english_cart, 'Pizza Vitti loyalty')
        self.assertContains(english_cart, 'Create my loyalty card')
        self.assertNotContains(english_cart, 'Créer ma carte fidélité')

        arabic_cart = self.client.get('/ar/cart/')
        self.assertContains(arabic_cart, 'طلبي')
        self.assertContains(arabic_cart, 'الكمية')
        self.assertContains(arabic_cart, '>حذف</button>')
        self.assertContains(arabic_cart, 'برنامج ولاء Pizza Vitti')

    def test_sold_out_product_stays_visible_but_cannot_be_ordered(self):
        self.product.availability_status = 'sold_out'
        self.product.save()

        menu = self.client.get('/fr/menu/pizzas/')
        self.assertContains(menu, self.product.name)
        self.assertContains(menu, 'Épuisé aujourd’hui')
        self.assertNotContains(menu, f'action="{reverse("shop:add_to_cart", args=[self.product.id])}"')

        response = self.client.post(reverse('shop:add_to_cart', args=[self.product.id]), {'qty': 1})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(str(self.product.id), self.client.session.get('cart', {}))

    def test_owner_can_schedule_product_and_tracking_requires_email(self):
        owner = get_user_model().objects.create_superuser('owner-test', 'owner@example.com', 'SecurePass123!')
        self.client.force_login(owner)
        available_again = timezone.localtime() + timedelta(hours=2)
        response = self.client.post(reverse('shop:owner_dashboard'), {
            'action': 'update_product_availability',
            'product_id': self.product.id,
            'availability_status': 'scheduled',
            'available_again_at': available_again.strftime('%Y-%m-%dT%H:%M'),
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.availability_status, 'scheduled')
        self.assertFalse(self.product.is_available)

        order = self.create_order(1, 'PV-TRACK-1')
        wrong = self.client.post(reverse('shop:track_order'), {'order_number': order.order_number, 'email': 'wrong@example.com'})
        self.assertNotContains(wrong, 'order-tracking-result')
        correct = self.client.post(reverse('shop:track_order'), {'order_number': order.order_number, 'email': order.email})
        self.assertContains(correct, 'order-tracking-result')
        self.assertContains(correct, 'order-progress')


class StorefrontProductionRulesTests(TestCase):
    def test_camera_section_is_not_routed(self):
        self.assertEqual(self.client.get('/owner/cameras/').status_code, 404)
        self.assertEqual(self.client.get('/owner/cameras/setup/').status_code, 404)

    def test_localized_menu_group_accepts_language_parameter(self):
        response = self.client.get(
            reverse('shop:localized_menu_group', args=['fr', 'pizzas'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nos pizzas')

    def test_legacy_menu_urls_redirect_permanently_to_canonical_menu(self):
        response = self.client.get(reverse('shop:boutique'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/fr/menu/')

        response = self.client.get(reverse('shop:menu_group', args=['pizzas']))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/fr/menu/pizzas/')

    def test_reservation_rejects_closed_day(self):
        day = timezone.localdate() + timedelta(days=1)
        while OpeningPeriod.objects.filter(weekday=day.weekday(), is_active=True).exists():
            day += timedelta(days=1)
        response = self.client.post(reverse('shop:booking'), {
            'name': 'Nina Rossi',
            'email': 'nina@example.com',
            'phone': '0556421449',
            'guests': 2,
            'date': day.isoformat(),
            'time': '12:00',
            'message': '',
            'website': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'en dehors des horaires')
        self.assertFalse(Reservation.objects.filter(email='nina@example.com').exists())

    def test_payment_success_url_does_not_mark_order_paid_without_verification(self):
        order = Order.objects.create(
            order_number='PV-PENDING',
            customer_name='Client test',
            email='client@example.com',
            total=Decimal('12.00'),
            payment_status='pending',
        )
        response = self.client.get(reverse('shop:payment_success', args=[order.order_number]))
        self.assertRedirects(response, order.get_absolute_url())
        order.refresh_from_db()
        self.assertEqual(order.payment_status, 'pending')

    def test_private_customer_pages_are_noindex(self):
        response = self.client.get(reverse('shop:cart'))
        self.assertContains(response, 'name="robots" content="noindex,nofollow"')

    def test_loyalty_program_is_hidden_while_personal_play_account_is_used(self):
        home = self.client.get('/fr/')
        self.assertNotContains(home, 'Carte fidélité digitale')

        cart = self.client.get(reverse('shop:cart'))
        self.assertNotContains(cart, 'Offre fidélité')


@override_settings(
    OWNER_DASHBOARD_USERNAME='admin',
    OWNER_DASHBOARD_PASSWORD='Rootvitti',
    OWNER_DASHBOARD_PASSWORD_HASH='',
    KITCHEN_PASSWORD='123',
)
class DefaultAppCredentialsTests(TestCase):
    def test_owner_uses_admin_username_and_rootvitti_password(self):
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': 'Rootvitti',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        self.assertTrue(self.client.session['owner_access'])

    def test_kitchen_uses_password_only(self):
        login_page = self.client.get(reverse('shop:app_login'), {'role': 'kitchen'})
        self.assertContains(login_page, 'data-username-fields hidden')
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'kitchen',
            'password': '123',
        })
        self.assertRedirects(response, reverse('shop:kitchen_app'))
        self.assertTrue(self.client.session['kitchen_access'])
        self.assertNotIn('owner_access', self.client.session)

    def test_django_superuser_can_use_the_owner_app_login(self):
        get_user_model().objects.create_superuser(
            username='site-admin',
            email='admin@example.com',
            password='AnotherSecurePassword123!',
        )
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'site-admin',
            'password': 'AnotherSecurePassword123!',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        self.assertTrue(self.client.session['owner_access'])


@override_settings(
    OWNER_DASHBOARD_USERNAME='admin',
    OWNER_DASHBOARD_PASSWORD='1234',
    OWNER_DASHBOARD_PASSWORD_HASH='',
    KITCHEN_PASSWORD='1234',
)
class OperationsAccessTests(TestCase):
    def test_kitchen_session_cannot_open_owner_dashboard(self):
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'kitchen',
            'password': '1234',
        })
        self.assertRedirects(response, reverse('shop:kitchen_app'))
        self.assertEqual(self.client.get(reverse('shop:kitchen_app')).status_code, 200)
        owner_response = self.client.get(reverse('shop:owner_dashboard'))
        self.assertEqual(owner_response.status_code, 302)
        self.assertIn(reverse('shop:owner_login'), owner_response.url)

    def test_owner_session_can_open_owner_and_kitchen_pages(self):
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': '1234',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        self.assertEqual(self.client.get(reverse('shop:owner_dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('shop:kitchen_app')).status_code, 200)
        self.client.get(reverse('shop:owner_logout'))
        self.assertEqual(self.client.get(reverse('shop:owner_dashboard')).status_code, 302)
        self.assertEqual(self.client.get(reverse('shop:kitchen_app')).status_code, 302)

    def test_kitchen_session_hides_owner_navigation_and_app_card(self):
        self.client.post(reverse('shop:app_login'), {
            'role': 'kitchen',
            'password': '1234',
        })
        kitchen_response = self.client.get(reverse('shop:kitchen_app'))
        self.assertNotContains(kitchen_response, reverse('shop:owner_dashboard'))
        app_response = self.client.get(reverse('shop:app_home'))
        self.assertNotContains(app_response, 'Propriétaire (admin)')
        self.assertNotContains(app_response, reverse('shop:app_role', args=['proprietaire']))

    def test_owner_navigation_keeps_owner_and_kitchen_access(self):
        self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': '1234',
        })
        response = self.client.get(reverse('shop:kitchen_app'))
        self.assertContains(response, reverse('shop:owner_dashboard'))
        app_response = self.client.get(reverse('shop:app_home'))
        self.assertContains(app_response, 'Dashboard propriétaire')
        self.assertContains(app_response, 'Cuisine (commandes)')

    @override_settings(
        OWNER_DASHBOARD_PASSWORD='SecureOwnerPass',
        OWNER_DASHBOARD_PASSWORD_HASH='',
    )
    def test_new_owner_password_is_case_sensitive(self):
        rejected = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': 'secureownerpass',
        })
        self.assertEqual(rejected.status_code, 200)
        self.assertNotIn('owner_access', self.client.session)
        accepted = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': 'SecureOwnerPass',
        })
        self.assertRedirects(accepted, reverse('shop:owner_dashboard'))
        self.assertTrue(self.client.session['owner_access'])

    def test_owner_username_is_required_and_case_sensitive(self):
        for username in ['', 'Admin']:
            response = self.client.post(reverse('shop:app_login'), {
                'role': 'owner',
                'username': username,
                'password': '1234',
            })
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('owner_access', self.client.session)

    def test_kitchen_session_cannot_switch_directly_to_owner_role(self):
        self.client.post(reverse('shop:app_login'), {
            'role': 'kitchen',
            'password': '1234',
        })
        response = self.client.get(reverse('shop:app_login'), {'role': 'owner'})
        self.assertRedirects(response, reverse('shop:kitchen_app'))
        self.assertNotIn('owner_access', self.client.session)

    @override_settings(LOYALTY_ENABLED=True)
    def test_owner_can_choose_the_loyalty_gift_from_dashboard(self):
        self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': '1234',
        })
        response = self.client.post(reverse('shop:owner_dashboard'), {
            'action': 'update_loyalty_reward',
            'reward_type': 'free_pizza',
            'pizzas_required': '7',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        reward = LoyaltyReward.objects.get(is_active=True)
        self.assertEqual(reward.reward_type, 'free_pizza')
        self.assertEqual(reward.pizzas_required, 7)


class StaffPointageTests(TestCase):
    def setUp(self):
        self.staff = StaffMember(
            name='Camille Test',
            username='camille',
            role='kitchen',
            temporary_password='secret',
        )
        self.staff.save()

    def login_staff(self):
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'staff',
            'username': 'camille',
            'password': 'secret',
        })
        self.assertRedirects(response, reverse('shop:staff_portal'))

    def test_worked_hours_subtract_accumulated_breaks(self):
        start = timezone.now() - timedelta(hours=8, minutes=30)
        shift = StaffShift(
            staff=self.staff,
            status='checked_out',
            check_in_at=start,
            check_out_at=start + timedelta(hours=8, minutes=30),
            break_seconds=30 * 60,
        )
        self.assertEqual(shift.worked_seconds(), 8 * 60 * 60)
        self.assertEqual(shift.worked_duration_display, '8 h 00')

    def test_staff_portal_has_clock_totals_and_history(self):
        StaffShift.objects.create(
            staff=self.staff,
            status='checked_out',
            check_in_at=timezone.now() - timedelta(hours=4),
            check_out_at=timezone.now() - timedelta(hours=1),
        )
        self.login_staff()
        response = self.client.get(reverse('shop:staff_portal'))
        self.assertContains(response, 'data-live-clock')
        self.assertContains(response, 'Mes heures récentes')
        self.assertContains(response, '3 h 00')

    def test_staff_session_hides_owner_and_kitchen_navigation(self):
        self.login_staff()
        portal_response = self.client.get(reverse('shop:staff_portal'))
        self.assertNotContains(portal_response, reverse('shop:owner_dashboard'))
        self.assertNotContains(portal_response, reverse('shop:kitchen_app'))
        app_response = self.client.get(reverse('shop:app_home'))
        self.assertNotContains(app_response, 'Propriétaire (admin)')
        self.assertNotContains(app_response, 'Cuisine (commandes)')
        self.assertContains(app_response, 'Staff (pointage)')

    def test_multiple_breaks_are_accumulated_through_pointage_actions(self):
        self.login_staff()
        start = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        action_url = reverse('shop:staff_action')
        with patch('shop.views.timezone.now', return_value=start):
            self.client.post(action_url, {'action': 'check_in'})
        with patch('shop.views.timezone.now', return_value=start + timedelta(hours=2)):
            self.client.post(action_url, {'action': 'break'})
        with patch('shop.views.timezone.now', return_value=start + timedelta(hours=2, minutes=30)):
            self.client.post(action_url, {'action': 'back'})
        with patch('shop.views.timezone.now', return_value=start + timedelta(hours=5)):
            self.client.post(action_url, {'action': 'break'})
        with patch('shop.views.timezone.now', return_value=start + timedelta(hours=5, minutes=15)):
            self.client.post(action_url, {'action': 'check_out'})
        shift = StaffShift.objects.get(staff=self.staff)
        self.assertEqual(shift.break_seconds, 45 * 60)
        self.assertEqual(shift.worked_seconds(), 4 * 60 * 60 + 30 * 60)

    @override_settings(OWNER_DASHBOARD_USERNAME='admin', OWNER_DASHBOARD_PASSWORD='1234', OWNER_DASHBOARD_PASSWORD_HASH='')
    def test_owner_can_filter_and_print_staff_hours(self):
        report_day = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        StaffShift.objects.create(
            staff=self.staff,
            status='checked_out',
            check_in_at=report_day - timedelta(hours=5),
            check_out_at=report_day - timedelta(hours=1),
            break_seconds=15 * 60,
        )
        self.client.post(reverse('shop:app_login'), {'role': 'owner', 'username': 'admin', 'password': '1234'})
        today = report_day.date().isoformat()
        response = self.client.get(reverse('shop:reports_dashboard'), {
            'date_from': today,
            'date_to': today,
            'staff_id': self.staff.id,
        })
        self.assertContains(response, 'Imprimer les heures')
        self.assertContains(response, 'Camille Test')
        self.assertContains(response, '3 h 45')
        self.assertContains(response, 'Cuisine')

    def test_staff_role_is_selected_from_french_job_choices(self):
        self.assertEqual(self.staff.get_role_display(), 'Cuisine')
        self.assertIn(('server', 'Serveur / Serveuse'), StaffMember.ROLE_CHOICES)
        self.assertIn(('cleaner', 'Entretien'), StaffMember.ROLE_CHOICES)
