import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError

from apps.authentication.models import EmployeeProfile


class TelegramMiniAppAuthentication(BaseAuthentication):
    max_age_seconds = 60 * 60 * 24

    def authenticate(self, request):
        init_data = request.headers.get("X-Telegram-Init-Data")
        if not init_data:
            return None

        data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data.pop("hash", None)
        if not received_hash:
            raise AuthenticationFailed("Missing Telegram hash.")

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(data.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            raise AuthenticationFailed("Invalid Telegram init data.")

        auth_date = int(data.get("auth_date", 0))
        if time.time() - auth_date > self.max_age_seconds:
            raise AuthenticationFailed("Telegram init data expired.")

        telegram_user = json.loads(data.get("user", "{}"))
        telegram_id = str(telegram_user.get("id"))

        try:
            employee = EmployeeProfile.objects.select_related("user").get(
                telegram_id=telegram_id,
                is_active=True,
            )
        except EmployeeProfile.DoesNotExist:
            raise AuthenticationFailed("Employee is not registered or inactive.")

        return employee.user, None


class TelegramBotAuthentication(BaseAuthentication):
    scheme = 'TelegramBot'

    token_backend = TokenBackend(
        algorithm='HS256',
        signing_key=settings.TELEGRAM_BOT_SECRET_TOKEN,
        audience='textile-api',
        issuer='textile-telegram-bot',
        leeway=5,
    )

    @classmethod
    def decode_assertion(cls, authorization):

        try:
            scheme, token = authorization.split(' ', 1)
        except ValueError:
            return None

        if scheme != cls.scheme:
            return None

        try:
            claims = cls.token_backend.decode(token, verify=True)
        except TokenBackendError:
            raise AuthenticationFailed('Invalid bot assertion.')

        required_claims = {
            'sub',
            'telegram_user_id',
            'telegram_update_id',
            'iat',
            'nbf',
            'exp',
            'jti',
        }

        if not required_claims.issubset(claims):
            raise AuthenticationFailed(
                'Bot assertion is missing required claims.'
            )

        telegram_id = str(claims['telegram_user_id'])

        if claims['sub'] != f'telegram-user:{telegram_id}':
            raise AuthenticationFailed('Invalid bot assertion subject.')

        return claims

    def authenticate(self, request):
        claims = self.decode_assertion(request.headers.get('Authorization', ''))
        if claims is None:
            return None

        telegram_id = str(claims['telegram_user_id'])

        try:
            employee = EmployeeProfile.objects.select_related('user').get(
                telegram_id=telegram_id,
                is_active=True,
                user__role='employee',
            )
        except EmployeeProfile.DoesNotExist:
            raise AuthenticationFailed(
                'Employee is not registered or inactive.'
            )

        return employee.user, claims
