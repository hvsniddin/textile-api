from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.base.models import TimeStampedModel


# Create your models here.
class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EMPLOYEE = 'employee', 'Employee'

    role = models.CharField(max_length=30, choices=Role.choices, default='employee')
    # profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)


class EmployeeProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)

    telegram_id = models.CharField(max_length=255, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_name
