from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import EmployeeProfile, User


class TelegramIntegrationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='998901112233',
            role=User.Role.EMPLOYEE,
        )
        self.employee = EmployeeProfile.objects.create(
            user=self.user,
            full_name='Test Employee',
            phone_number='998901112233',
            is_active=False,
        )

    def test_authenticated_employee_can_get_own_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('telegram-employee'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.employee.id))

    @patch('apps.telegram.views.TelegramBotAuthentication.decode_assertion')
    def test_bot_can_register_employee(self, decode_assertion):
        decode_assertion.return_value = {'telegram_user_id': '777'}

        response = self.client.post(
            reverse('telegram-register'),
            {'phone_number': '+998 90 111 22 33'},
            format='json',
            HTTP_AUTHORIZATION='TelegramBot service-assertion',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.telegram_id, '777')
        self.assertTrue(self.employee.is_active)
        self.assertIsNotNone(self.employee.registered_at)

    @patch('apps.telegram.views.TelegramBotAuthentication.decode_assertion')
    def test_registration_requires_bot_assertion(self, decode_assertion):
        decode_assertion.return_value = None

        response = self.client.post(
            reverse('telegram-register'),
            {'phone_number': self.employee.phone_number},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_old_webhook_endpoint_is_removed(self):
        response = self.client.post('/api/v1/telegram/webhook/', {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
