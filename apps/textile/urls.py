from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminDashboardView,
    CategoryViewSet,
    ProductViewSet,
    ProcessStepViewSet,
    ProductProcessStepViewSet,
    EmployeeReportViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'process-steps', ProcessStepViewSet, basename='process-step')
router.register(r'product-process-steps', ProductProcessStepViewSet, basename='product-process-step')
router.register(r'employee-reports', EmployeeReportViewSet, basename='employee-report')

urlpatterns = [
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('', include(router.urls)),
]
