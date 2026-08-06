from django.contrib import admin

from .models import Category, EmployeeReport, ProcessStep, Product, ProductProcessStep
from .services import bulk_set_employee_report_status


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active', 'created_at', 'updated_at')
    list_filter = ('category', 'is_active')
    list_select_related = ('category',)
    search_fields = ('code', 'name', 'description', 'category__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ProductProcessStep)
class ProductProcessStepAdmin(admin.ModelAdmin):
    list_display = ('product', 'step', 'order', 'price', 'created_at', 'updated_at')
    list_filter = ('product', 'step')
    list_select_related = ('product', 'step')
    search_fields = ('product__code', 'product__name', 'step__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(EmployeeReport)
class EmployeeReportAdmin(admin.ModelAdmin):
    list_display = (
        'employee',
        'product',
        'process_step',
        'count',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'step__product', 'step__step')
    list_select_related = ('employee__user', 'step__product', 'step__step')
    search_fields = (
        'employee__full_name',
        'employee__phone_number',
        'step__product__code',
        'step__product__name',
        'step__step__name',
    )
    readonly_fields = ('created_at', 'updated_at')
    actions = ('approve_reports', 'reject_reports')

    @admin.display(description='Product')
    def product(self, obj):
        return obj.step.product

    @admin.display(description='Step')
    def process_step(self, obj):
        return obj.step.step

    @admin.action(description='Approve selected pending reports')
    def approve_reports(self, request, queryset):
        updated = bulk_set_employee_report_status(queryset, EmployeeReport.Status.APPROVED)
        self.message_user(request, f'{updated} pending report(s) approved.')

    @admin.action(description='Reject selected pending reports')
    def reject_reports(self, request, queryset):
        updated = bulk_set_employee_report_status(queryset, EmployeeReport.Status.REJECTED)
        self.message_user(request, f'{updated} pending report(s) rejected.')
