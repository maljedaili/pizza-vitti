from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shop.models import (
    CameraLocation,
    Category,
    CustomerMessage,
    Favorite,
    LoyaltyRedemption,
    LoyaltyReward,
    NewsletterSubscriber,
    Order,
    OrderItem,
    Product,
    Reservation,
    SecurityCamera,
    StaffMember,
    StaffShift,
)


class AndroidAppVerificationTests(TestCase):
    @override_settings(
        ANDROID_APP_PACKAGE='fr.kayen.pizzavitti',
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
                'package_name': 'fr.kayen.pizzavitti',
                'sha256_cert_fingerprints': ['AA:BB:CC', '11:22:33'],
            },
        }])

    @override_settings(ANDROID_CERT_SHA256_FINGERPRINTS=[])
    def test_asset_links_is_empty_until_play_fingerprint_is_configured(self):
        response = self.client.get(reverse('android_asset_links'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


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

        response = self.client.post(reverse('shop:checkout'), {
            'name': 'Camille Martin',
            'email': self.user.email,
            'payment_method': 'cash',
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

    def test_public_footer_promotes_android_application(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'google-play-badge-fr.png')
        self.assertContains(response, 'Le menu, vos commandes et votre fidélité dans l’application.')
        self.assertContains(response, reverse('shop:account_deletion'))

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

    def test_public_navigation_is_reduced_and_home_uses_category_slider(self):
        response = self.client.get(reverse('shop:home'))
        self.assertContains(response, 'data-hero-slider')
        self.assertContains(response, 'menu-bambino-pizza.jpg')
        self.assertContains(response, 'menu-tiramisu.jpg')
        self.assertContains(response, 'bot-toggle-photo')
        self.assertContains(response, 'L’Italie à Bordeaux')
        self.assertNotContains(response, f'<a href="{reverse("shop:home")}">Accueil</a>', html=True)
        self.assertNotContains(response, '>Fidélité</a>')
        self.assertNotContains(response, '>Application</a>')


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


@override_settings(
    OWNER_DASHBOARD_USERNAME='admin',
    OWNER_DASHBOARD_PASSWORD='1234',
    OWNER_DASHBOARD_PASSWORD_HASH='',
    KITCHEN_PASSWORD='1234',
)
class CameraCenterTests(TestCase):
    def setUp(self):
        self.location = CameraLocation.objects.create(
            name='Restaurant Centre',
            kind='restaurant',
            gateway_url='https://camera-centre.example-tailnet.ts.net',
        )
        self.camera = SecurityCamera.objects.create(
            location=self.location,
            name='Cuisine principale',
            stream_name='cuisine-principale',
            brand='Reolink',
            supports_audio=True,
            supports_talk=True,
        )

    def login_owner(self):
        response = self.client.post(reverse('shop:app_login'), {
            'role': 'owner',
            'username': 'admin',
            'password': '1234',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))

    def test_owner_can_open_camera_pages_and_microphone_view(self):
        self.login_owner()
        self.assertEqual(self.client.get(reverse('shop:camera_center')).status_code, 200)
        self.assertEqual(self.client.get(reverse('shop:camera_setup')).status_code, 200)
        self.assertEqual(self.client.get(reverse('shop:camera_gateway_guide')).status_code, 200)
        response = self.client.get(reverse('shop:camera_detail', args=[self.camera.id]))
        self.assertContains(response, 'allow="microphone; autoplay; fullscreen"')
        self.assertContains(response, 'data-camera-talk')

    def test_kitchen_session_cannot_open_camera_pages(self):
        self.client.post(reverse('shop:app_login'), {
            'role': 'kitchen',
            'password': '1234',
        })
        for url in [
            reverse('shop:camera_center'),
            reverse('shop:camera_setup'),
            reverse('shop:camera_gateway_guide'),
            reverse('shop:camera_detail', args=[self.camera.id]),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('shop:owner_login'), response.url)

    def test_staff_session_cannot_open_camera_center(self):
        staff = StaffMember(
            name='Alex Test',
            username='alex',
            role='server',
            temporary_password='secret',
        )
        staff.save()
        self.client.post(reverse('shop:app_login'), {
            'role': 'staff',
            'username': 'alex',
            'password': 'secret',
        })
        response = self.client.get(reverse('shop:camera_center'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('shop:owner_login'), response.url)

    def test_gateway_urls_require_https_and_cannot_contain_credentials(self):
        for gateway_url in [
            'http://camera.example.com',
            'https://camera-user:camera-password@camera.example.com',
        ]:
            location = CameraLocation(name='Unsafe', gateway_url=gateway_url)
            with self.assertRaises(ValidationError):
                location.full_clean()

    def test_camera_urls_are_built_without_camera_credentials(self):
        self.assertEqual(
            self.camera.viewer_url,
            'https://camera-centre.example-tailnet.ts.net/stream.html'
            '?src=cuisine-principale&mode=webrtc&media=video+audio',
        )
        self.assertEqual(
            self.camera.talk_url,
            'https://camera-centre.example-tailnet.ts.net/webrtc.html'
            '?src=cuisine-principale&media=video+audio+microphone',
        )

    def test_owner_can_add_and_update_camera_configuration(self):
        self.login_owner()
        response = self.client.post(reverse('shop:camera_setup'), {
            'action': 'add_camera',
            'location_id': self.location.id,
            'name': 'Salle',
            'stream_name': 'salle',
            'supports_audio': 'on',
            'sort_order': '2',
        })
        self.assertRedirects(response, reverse('shop:camera_setup'))
        camera = SecurityCamera.objects.get(stream_name='salle')
        response = self.client.post(reverse('shop:camera_setup'), {
            'action': 'update_camera',
            'camera_id': camera.id,
            'name': 'Salle principale',
            'stream_name': 'salle-principale',
            'supports_audio': 'on',
            'supports_talk': 'on',
            'sort_order': '1',
        })
        self.assertRedirects(response, reverse('shop:camera_setup'))
        camera.refresh_from_db()
        self.assertEqual(camera.name, 'Salle principale')
        self.assertEqual(camera.stream_name, 'salle-principale')
        self.assertTrue(camera.supports_talk)

    def test_missing_location_shows_validation_message(self):
        self.login_owner()
        response = self.client.post(reverse('shop:camera_setup'), {
            'action': 'add_camera',
            'location_id': '',
            'name': 'Salle',
            'stream_name': 'salle',
        }, follow=True)
        self.assertContains(response, 'Choisissez un lieu valide.')
        self.assertEqual(SecurityCamera.objects.count(), 1)


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
