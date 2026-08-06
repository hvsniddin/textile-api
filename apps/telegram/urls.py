from django.urls import path

from apps.telegram.views import TelegramEmployeeStatusView, TelegramEmployeeView, TelegramRegistrationView

urlpatterns = [
    path("employee/", TelegramEmployeeView.as_view(), name="telegram-employee"),
    path("register/", TelegramRegistrationView.as_view(), name="telegram-register"),
    path("employee-status/", TelegramEmployeeStatusView.as_view(), name="telegram-employee-status"),
]
