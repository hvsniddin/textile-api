import django_filters

from .models import Category, EmployeeReport, ProcessStep, Product


class CategoryFilter(django_filters.FilterSet):
    class Meta:
        model = Category
        fields = []


class ProductFilter(django_filters.FilterSet):

    class Meta:
        model = Product
        fields = ['category', 'is_active']


class ProcessStepFilter(django_filters.FilterSet):
    class Meta:
        model = ProcessStep
        fields = []


class EmployeeReportFilter(django_filters.FilterSet):
    product = django_filters.UUIDFilter(field_name='step__product')
    step = django_filters.UUIDFilter(field_name='step__step')
    product_process_step = django_filters.UUIDFilter(field_name='step')

    class Meta:
        model = EmployeeReport
        fields = ['status', 'employee', 'product', 'step', 'product_process_step']
