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
        return phone

    @transaction.atomic
    def create(self, validated_data):
        full_name = validated_data["full_name"]
        phone_number = validated_data["phone_number"]

        user, created = User.objects.get_or_create(
            username=phone_number,
            defaults={
                "role": User.Role.EMPLOYEE,
                "is_active": True,
            }
        )

        if created:
            user.set_unusable_password()
            user.save()
        else:
            # If user already exists, ensure it has the employee role
            if user.role != User.Role.EMPLOYEE:
                user.role = User.Role.EMPLOYEE
                user.save()

        profile, profile_created = EmployeeProfile.objects.update_or_create(
            user=user,
            defaults={
                "full_name": full_name,
                "phone_number": phone_number,
                "is_active": False if not created else False, # Keep it False as per original logic for new profile
            }
        )
        
        # If profile existed, we might want to preserve its is_active status or set it to something specific.
        # The original code set it to False for new profiles.
        # If the user wants to "use that existing user object and change the user info if necessary",
        # updating full_name and phone_number (which is the same) is what we do here.

        return {
            "user": user,
            "profile": profile,
        }
