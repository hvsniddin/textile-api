from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import EmployeeProfile, User


class EmployeeProfileAPITests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin-user',
            password='pass12345',
            role=User.Role.ADMIN,
        )
        self.employee_user = User.objects.create_user(
            username='employee-1',
            password='pass12345',
            role=User.Role.EMPLOYEE,
        )
        self.employee_profile = EmployeeProfile.objects.create(
            user=self.employee_user,
            full_name='Employee One',
            phone_number='+998900000001',
            is_active=True,
        )
        self.inactive_user = User.objects.create_user(
            username='employee-2',
            password='pass12345',
            role=User.Role.EMPLOYEE,
        )
        self.inactive_profile = EmployeeProfile.objects.create(
            user=self.inactive_user,
            full_name='Tailor Two',
            phone_number='+998900000002',
            is_active=False,
        )
        EmployeeProfile.objects.filter(id=self.employee_profile.id).update(created_at='2026-01-01T00:00:00Z')
        self.client.force_authenticate(user=self.admin_user)

    def test_employee_profiles_support_search_filtering_and_default_ordering(self):
        list_url = reverse('employee-profile-list')

        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data['results'][0]['id'], str(self.inactive_profile.id))

        search_response = self.client.get(list_url, {'search': '+998900000002'})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in search_response.data['results']], [str(self.inactive_profile.id)])

        filter_response = self.client.get(list_url, {'is_active': 'false'})
        self.assertEqual(filter_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in filter_response.data['results']], [str(self.inactive_profile.id)])
