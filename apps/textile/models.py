from django.db import models

from apps.base.models import TimeStampedModel


# Create your models here.
class Category(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    code = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    picture = models.ImageField(upload_to='product_pictures/', null=True, blank=True)

    def __str__(self):
        return f'{self.code} - {self.name}'


class ProcessStep(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class ProductProcessStep(TimeStampedModel):
    step = models.ForeignKey(ProcessStep, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    price = models.PositiveIntegerField()
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return f'{self.product} / {self.step}'


class EmployeeReport(TimeStampedModel):
    class Status(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PENDING = 'pending', 'Pending'

    employee = models.ForeignKey("authentication.EmployeeProfile", on_delete=models.CASCADE)
    step = models.ForeignKey("textile.ProductProcessStep", on_delete=models.SET_NULL, null=True)
    price_snapshot = models.PositiveIntegerField(null=True, blank=True)
    count = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f'{self.employee} - {self.step} ({self.count})'
