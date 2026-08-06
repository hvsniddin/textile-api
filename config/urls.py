from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from config.swagger import openapi_schema, swagger_ui

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', swagger_ui, name='swagger-ui'),
    path('swagger.json', openapi_schema, name='openapi-schema'),
    path('auth/login/', TokenObtainPairView.as_view(), name="login"),
    path('auth/refresh/', TokenRefreshView.as_view(), name="refresh"),
    path('api/v1/textile/', include('apps.textile.urls')),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/telegram/', include('apps.telegram.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
