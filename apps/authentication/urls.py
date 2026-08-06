from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import UserViewSet, EmployeeProfileViewSet, CreateEmployeeView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'employee-profiles', EmployeeProfileViewSet, basename='employee-profile')
router.register(r'employees', CreateEmployeeView, basename='create-employee')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
