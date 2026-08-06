from rest_framework import serializers

from apps.authentication.models import User

from .models import Category, Product, ProcessStep, ProductProcessStep, EmployeeReport


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'category', 'category_name', 'code', 'name', 'description', 'is_active', 'picture', 'created_at', 'updated_at']


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']


class ProductProcessStepSerializer(serializers.ModelSerializer):
    step_name = serializers.CharField(source='step.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductProcessStep
        fields = ['id', 'step', 'step_name', 'product', 'product_name', 'price', 'order', 'created_at', 'updated_at']


class EmployeeReportSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    step_name = serializers.CharField(source='step.step.name', read_only=True)
    product_name = serializers.CharField(source='step.product.name', read_only=True)
    step_price = serializers.IntegerField(source='step.price', read_only=True)

    class Meta:
        model = EmployeeReport
        fields = [
            'id',
            'employee',
            'employee_name',
            'step',
            'step_name',
            'product_name',
            'step_price',
            'count',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['employee', 'employee_name', 'step_name', 'product_name', 'created_at', 'updated_at']

    def _is_admin_user(self, user):
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, 'role', None) == User.Role.ADMIN
            )
        )

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        instance = getattr(self, 'instance', None)
        is_admin = self._is_admin_user(user)

        if instance is None:
            if 'employee' in self.initial_data:
                raise serializers.ValidationError({'employee': 'Employee is assigned automatically.'})
            if 'status' in self.initial_data:
                raise serializers.ValidationError({'status': 'Status can only be changed by admins.'})
            return attrs

        if instance.status in (EmployeeReport.Status.APPROVED, EmployeeReport.Status.REJECTED):
            raise serializers.ValidationError('Approved or rejected reports cannot be changed.')

        if is_admin:
            forbidden_fields = set(self.initial_data.keys()) - {'status'}
            if forbidden_fields:
                raise serializers.ValidationError('Admins can only approve or reject reports.')
            if 'status' not in attrs:
                raise serializers.ValidationError({'status': 'This field is required.'})
            if attrs['status'] == EmployeeReport.Status.PENDING:
                raise serializers.ValidationError({'status': 'Admins can only approve or reject reports.'})
            return attrs

        if 'status' in self.initial_data:
            raise serializers.ValidationError({'status': 'Status can only be changed by admins.'})

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        if not user or not user.is_authenticated:
            raise serializers.ValidationError('Authentication is required.')

        if getattr(user, 'role', None) != User.Role.EMPLOYEE:
            raise serializers.ValidationError('Only employee users can create employee reports.')

        employee = getattr(user, 'profile', None)
        if employee is None:
            raise serializers.ValidationError('Employee profile is required.')

        validated_data['employee'] = employee
        return super().create(validated_data)
