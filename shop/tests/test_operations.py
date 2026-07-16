from datetime import timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shop.models import CameraLocation, SecurityCamera, StaffMember, StaffShift


@override_settings(OWNER_DASHBOARD_PASSWORD='1234', KITCHEN_PASSWORD='1234')
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
            'password': '1234',
        })
        self.assertRedirects(response, reverse('shop:owner_dashboard'))
        self.assertEqual(self.client.get(reverse('shop:owner_dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('shop:kitchen_app')).status_code, 200)
        self.client.get(reverse('shop:owner_logout'))
        self.assertEqual(self.client.get(reverse('shop:owner_dashboard')).status_code, 302)
        self.assertEqual(self.client.get(reverse('shop:kitchen_app')).status_code, 302)


@override_settings(OWNER_DASHBOARD_PASSWORD='1234', KITCHEN_PASSWORD='1234')
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

    @override_settings(OWNER_DASHBOARD_PASSWORD='1234')
    def test_owner_can_filter_and_print_staff_hours(self):
        StaffShift.objects.create(
            staff=self.staff,
            status='checked_out',
            check_in_at=timezone.now() - timedelta(hours=5),
            check_out_at=timezone.now() - timedelta(hours=1),
            break_seconds=15 * 60,
        )
        self.client.post(reverse('shop:app_login'), {'role': 'owner', 'password': '1234'})
        today = timezone.localdate().isoformat()
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
