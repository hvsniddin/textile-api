import django_filters

from .models import EmployeeProfile


class EmployeeProfileFilter(django_filters.FilterSet):
    class Meta:
        model = EmployeeProfile
        fields = ['is_active']
