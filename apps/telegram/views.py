from django.utils import timezone
from rest_framework import views
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.authentication.models import EmployeeProfile
from apps.authentication.serializers import EmployeeProfileSerializer
from apps.authentication.utils import normalize_phone
from apps.telegram.authentication import TelegramBotAuthentication


class TelegramEmployeeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = getattr(request.user, 'profile', None)
        if employee is None:
            return Response({'detail': 'Employee profile not found.'}, status=404)
        return Response(EmployeeProfileSerializer(employee).data)


class TelegramRegistrationView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        claims = TelegramBotAuthentication.decode_assertion(
            request.headers.get('Authorization', '')
        )
        if claims is None:
            return Response({'detail': 'Bot assertion is required.'}, status=401)

        phone_number = normalize_phone(request.data.get('phone_number', ''))
        if not phone_number:
            return Response({'phone_number': 'This field is required.'}, status=400)
        try:
            employee = EmployeeProfile.objects.select_related('user').get(
                phone_number=phone_number, user__role='employee'
            )
        except EmployeeProfile.DoesNotExist:
            return Response({'detail': 'Employee profile not found.'}, status=404)

        telegram_id = str(claims['telegram_user_id'])
        if EmployeeProfile.objects.filter(telegram_id=telegram_id).exclude(
            pk=employee.pk
        ).exists():
            return Response({'detail': 'Telegram user is already linked.'}, status=409)

        employee.telegram_id = telegram_id
        employee.is_active = True
        if employee.registered_at is None:
            employee.registered_at = timezone.now()
        employee.save(
            update_fields=['telegram_id', 'is_active', 'registered_at', 'updated_at']
        )
        return Response(EmployeeProfileSerializer(employee).data)


class TelegramEmployeeStatusView(views.APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def _employee(self, request):
        claims = TelegramBotAuthentication.decode_assertion(
            request.headers.get('Authorization', '')
        )
        if claims is None:
            return None
        return EmployeeProfile.objects.select_related('user').filter(
            telegram_id=str(claims['telegram_user_id']), user__role='employee'
        ).first()

    def get(self, request):
        employee = self._employee(request)
        if employee is None:
            return Response({'detail': 'Employee profile not found.'}, status=404)
        return Response(EmployeeProfileSerializer(employee).data)

    def post(self, request):
        employee = self._employee(request)
        if employee is None:
            return Response({'detail': 'Employee profile not found.'}, status=404)
        activated_now = not employee.is_active
        if activated_now:
            employee.is_active = True
            if employee.registered_at is None:
                employee.registered_at = timezone.now()
            employee.save(update_fields=['is_active', 'registered_at', 'updated_at'])
        data = EmployeeProfileSerializer(employee).data
        data['activated_now'] = activated_now
        return Response(data)
