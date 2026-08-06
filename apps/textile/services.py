from django.utils import timezone

from .models import EmployeeReport


def set_employee_report_status(report, status_value):
    report.status = status_value
    report.save(update_fields=['status', 'updated_at'])
    return report


def bulk_set_employee_report_status(queryset, status_value):
    return queryset.filter(status=EmployeeReport.Status.PENDING).update(
        status=status_value,
        updated_at=timezone.now(),
    )
