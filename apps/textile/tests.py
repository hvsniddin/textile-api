from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import EmployeeProfile, User
from .models import Category, Product, ProcessStep, ProductProcessStep, EmployeeReport


class EmployeeReportAPITests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Shirts', description='Shirt category')
        self.product = Product.objects.create(
            category=self.category,
            code='P-001',
            name='T-Shirt',
            description='Basic t-shirt',
        )
        self.step = ProcessStep.objects.create(name='Sewing', description='Sewing step')
        self.product_step = ProductProcessStep.objects.create(
            step=self.step,
            product=self.product,
            price=1000,
            order=1,
        )

        self.employee_user = User.objects.create_user(username='employee-1', password='pass12345', role=User.Role.EMPLOYEE)
        self.employee_profile = EmployeeProfile.objects.create(
            user=self.employee_user,
            full_name='Employee One',
            phone_number='+998900000001',
        )

        self.other_employee_user = User.objects.create_user(username='employee-2', password='pass12345', role=User.Role.EMPLOYEE)
        self.other_employee_profile = EmployeeProfile.objects.create(
            user=self.other_employee_user,
            full_name='Employee Two',
            phone_number='+998900000002',
        )

        self.admin_user = User.objects.create_user(username='admin-user', password='pass12345', role=User.Role.ADMIN)
        self.report_list_url = reverse('employee-report-list')

    def _create_report(self, employee=None, status_value=EmployeeReport.Status.PENDING):
        employee = employee or self.employee_profile
        return EmployeeReport.objects.create(
            employee=employee,
            step=self.product_step,
            count=10,
            status=status_value,
        )

    def test_employee_can_create_own_report(self):
        self.client.force_authenticate(user=self.employee_user)

        response = self.client.post(
            self.report_list_url,
            {'step': self.product_step.id, 'count': 12},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['employee']), str(self.employee_profile.id))
        self.assertEqual(response.data['status'], EmployeeReport.Status.PENDING)

    def test_employee_cannot_set_status_on_create_or_update(self):
        report = self._create_report()
        self.client.force_authenticate(user=self.employee_user)

        create_response = self.client.post(
            self.report_list_url,
            {'step': self.product_step.id, 'count': 12, 'status': EmployeeReport.Status.APPROVED},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)

        update_response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'status': EmployeeReport.Status.APPROVED},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_cannot_access_another_employees_report(self):
        report = self._create_report(employee=self.employee_profile)
        self.client.force_authenticate(user=self.other_employee_user)

        response = self.client.get(reverse('employee-report-detail', args=[report.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_employee_can_update_and_delete_own_pending_report(self):
        report = self._create_report()
        self.client.force_authenticate(user=self.employee_user)

        update_response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'count': 25},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['count'], 25)

        delete_response = self.client.delete(reverse('employee-report-detail', args=[report.id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        retrieve_response = self.client.get(reverse('employee-report-detail', args=[report.id]))
        self.assertEqual(retrieve_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_only_approve_or_reject(self):
        report = self._create_report()
        self.client.force_authenticate(user=self.admin_user)

        approve_response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'status': EmployeeReport.Status.APPROVED},
            format='json',
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], EmployeeReport.Status.APPROVED)

        edit_response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'count': 99},
            format='json',
        )
        self.assertEqual(edit_response.status_code, status.HTTP_400_BAD_REQUEST)

        create_response = self.client.post(
            self.report_list_url,
            {'step': self.product_step.id, 'count': 12},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

        delete_response = self.client.delete(reverse('employee-report-detail', args=[report.id]))
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_returns_summary_and_report_queues(self):
        self._create_report(status_value=EmployeeReport.Status.PENDING)
        self._create_report(status_value=EmployeeReport.Status.APPROVED)
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.get(reverse('admin-dashboard'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['reports']['total'], 2)
        self.assertEqual(response.data['summary']['reports']['pending'], 1)
        self.assertEqual(response.data['summary']['reports']['approved'], 1)
        self.assertEqual(response.data['summary']['categories'], 1)
        self.assertEqual(response.data['summary']['products'], 1)
        self.assertEqual(len(response.data['pending_reports']), 1)
        self.assertEqual(len(response.data['recent_reports']), 2)

    def test_employee_cannot_access_admin_dashboard(self):
        self.client.force_authenticate(user=self.employee_user)

        response = self.client.get(reverse('admin-dashboard'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_and_reject_with_actions(self):
        approve_report = self._create_report()
        reject_report = self._create_report()
        self.client.force_authenticate(user=self.admin_user)

        approve_response = self.client.post(reverse('employee-report-approve', args=[approve_report.id]))
        reject_response = self.client.post(reverse('employee-report-reject', args=[reject_report.id]))

        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], EmployeeReport.Status.APPROVED)
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.data['status'], EmployeeReport.Status.REJECTED)

    def test_admin_action_updates_report_without_bot_notification(self):
        report = self._create_report()
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(reverse('employee-report-approve', args=[report.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, EmployeeReport.Status.APPROVED)

    def test_admin_patch_updates_report_without_bot_notification(self):
        report = self._create_report()
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'status': EmployeeReport.Status.REJECTED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, EmployeeReport.Status.REJECTED)

    def test_admin_action_cannot_change_terminal_report(self):
        report = self._create_report(status_value=EmployeeReport.Status.APPROVED)
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(reverse('employee-report-reject', args=[report.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_terminal_report_cannot_be_changed_or_deleted(self):
        report = self._create_report(status_value=EmployeeReport.Status.APPROVED)
        self.client.force_authenticate(user=self.employee_user)

        update_response = self.client.patch(
            reverse('employee-report-detail', args=[report.id]),
            {'count': 25},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)

        delete_response = self.client.delete(reverse('employee-report-detail', args=[report.id]))
        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_management_endpoints_support_search_filtering_and_default_ordering(self):
        older_category = self.category
        newer_category = Category.objects.create(name='Jackets', description='Outerwear category')
        Category.objects.filter(id=older_category.id).update(created_at='2026-01-01T00:00:00Z')

        inactive_product = Product.objects.create(
            category=newer_category,
            code='P-002',
            name='Linen Jacket',
            description='Premium linen jacket',
            is_active=False,
        )
        Product.objects.filter(id=self.product.id).update(created_at='2026-01-01T00:00:00Z')

        newer_step = ProcessStep.objects.create(name='Packing', description='Final packing')
        ProcessStep.objects.filter(id=self.step.id).update(created_at='2026-01-01T00:00:00Z')

        self.client.force_authenticate(user=self.admin_user)

        categories_response = self.client.get(reverse('category-list'))
        self.assertEqual(categories_response.status_code, status.HTTP_200_OK)
        self.assertEqual(categories_response.data['results'][0]['id'], str(newer_category.id))

        category_search_response = self.client.get(reverse('category-list'), {'search': 'outerwear'})
        self.assertEqual(category_search_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in category_search_response.data['results']], [str(newer_category.id)])

        products_response = self.client.get(
            reverse('product-list'),
            {
                'category': str(newer_category.id),
                'description': 'linen',
                'is_active': 'false',
            },
        )
        self.assertEqual(products_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in products_response.data['results']], [str(inactive_product.id)])

        product_search_response = self.client.get(reverse('product-list'), {'search': 'P-002'})
        self.assertEqual(product_search_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in product_search_response.data['results']], [str(inactive_product.id)])

        steps_response = self.client.get(reverse('process-step-list'))
        self.assertEqual(steps_response.status_code, status.HTTP_200_OK)
        self.assertEqual(steps_response.data['results'][0]['id'], str(newer_step.id))

        step_search_response = self.client.get(reverse('process-step-list'), {'search': 'final'})
        self.assertEqual(step_search_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in step_search_response.data['results']], [str(newer_step.id)])

    def test_list_endpoints_are_paginated_with_default_size_of_50(self):
        Category.objects.bulk_create(
            Category(name=f'Category {index}', description=f'Category {index}')
            for index in range(55)
        )
        self.client.force_authenticate(user=self.admin_user)

        first_page_response = self.client.get(reverse('category-list'))
        self.assertEqual(first_page_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page_response.data['count'], 56)
        self.assertEqual(len(first_page_response.data['results']), 50)
        self.assertIsNotNone(first_page_response.data['next'])
        self.assertIsNone(first_page_response.data['previous'])

        second_page_response = self.client.get(reverse('category-list'), {'page': 2})
        self.assertEqual(second_page_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page_response.data['results']), 6)
        self.assertIsNotNone(second_page_response.data['previous'])

    def test_employee_reports_support_filters_and_default_ordering(self):
        older_report = self._create_report(status_value=EmployeeReport.Status.PENDING)
        newer_report = self._create_report(
            employee=self.other_employee_profile,
            status_value=EmployeeReport.Status.APPROVED,
        )
        EmployeeReport.objects.filter(id=older_report.id).update(created_at='2026-01-01T00:00:00Z')

        self.client.force_authenticate(user=self.admin_user)

        reports_response = self.client.get(reverse('employee-report-list'))
        self.assertEqual(reports_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reports_response.data['results'][0]['id'], str(newer_report.id))

        status_response = self.client.get(
            reverse('employee-report-list'),
            {'status': EmployeeReport.Status.APPROVED},
        )
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in status_response.data['results']], [str(newer_report.id)])

        employee_response = self.client.get(
            reverse('employee-report-list'),
            {'employee': str(self.other_employee_profile.id)},
        )
        self.assertEqual(employee_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in employee_response.data['results']], [str(newer_report.id)])

        product_response = self.client.get(
            reverse('employee-report-list'),
            {'product': str(self.product.id)},
        )
        self.assertEqual(product_response.status_code, status.HTTP_200_OK)
        self.assertEqual({item['id'] for item in product_response.data['results']}, {str(older_report.id), str(newer_report.id)})

        step_response = self.client.get(
            reverse('employee-report-list'),
            {'step': str(self.step.id)},
        )
        self.assertEqual(step_response.status_code, status.HTTP_200_OK)
        self.assertEqual({item['id'] for item in step_response.data['results']}, {str(older_report.id), str(newer_report.id)})

        product_process_step_response = self.client.get(
            reverse('employee-report-list'),
            {'product_process_step': str(self.product_step.id)},
        )
        self.assertEqual(product_process_step_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in product_process_step_response.data['results']},
            {str(older_report.id), str(newer_report.id)},
        )
