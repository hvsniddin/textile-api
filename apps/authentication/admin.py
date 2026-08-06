from django.contrib import admin

from apps.authentication.models import EmployeeProfile, User

# Register your models here.
admin.site.register(User)


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'phone_number',
        'user',
        'telegram_id',
        'is_active',
        'registered_at',
        'created_at',
        'updated_at',
    )
    list_filter = ('is_active', 'registered_at')
    list_select_related = ('user',)
    search_fields = ('full_name', 'phone_number', 'telegram_id', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
