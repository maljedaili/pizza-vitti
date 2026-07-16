from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shop.models import StaffMember, StaffShift


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
