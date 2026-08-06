from django.db import transaction
from rest_framework import serializers
from .models import User, EmployeeProfile
from .utils import normalize_phone


class EmployeeProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ['id', 'user', 'username', 'email', 'full_name', 'phone_number', 'telegram_id', 'is_active', 'registered_at', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = EmployeeProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'role', 'profile', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class CreateEmployeeSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=32)


    def validate_phone_number(self, value):
        phone = normalize_phone(value)

        if EmployeeProfile.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError("Employee with this phone number already exists.")

        if User.objects.filter(username=phone).exists():
            raise serializers.ValidationError("User with this phone number already exists.")

        return phone

    @transaction.atomic
    def create(self, validated_data):
        full_name = validated_data["full_name"]
        phone_number = validated_data["phone_number"]

        user = User(
            username=phone_number,
            role=User.Role.EMPLOYEE,
            is_active=True,
        )
        user.set_unusable_password()
        user.save()

        profile = EmployeeProfile.objects.create(
            user=user,
            full_name=full_name,
            phone_number=phone_number,
            telegram_id=None,
            is_active=False,
        )

        return {
            "user": user,
            "profile": profile,
        }
