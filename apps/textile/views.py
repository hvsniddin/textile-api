from django.db.models import Count, ExpressionWrapper, F, IntegerField, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import User

from .filters import CategoryFilter, EmployeeReportFilter, ProcessStepFilter, ProductFilter
from .models import Category, Product, ProcessStep, ProductProcessStep, EmployeeReport
from .permissions import IsAdmin, IsAdminOrReadOnlyByRole
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProcessStepSerializer,
    ProductProcessStepSerializer,
    EmployeeReportSerializer,
)
from .services import set_employee_report_status


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        report_summary = EmployeeReport.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status=EmployeeReport.Status.PENDING)),
            approved=Count('id', filter=Q(status=EmployeeReport.Status.APPROVED)),
            rejected=Count('id', filter=Q(status=EmployeeReport.Status.REJECTED)),
            total_items=Sum('count'),
        )
        report_summary['total_items'] = report_summary['total_items'] or 0

        recent_reports = EmployeeReport.objects.select_related(
            'employee__user',
            'step__step',
            'step__product',
        ).order_by('-created_at')[:10]
        pending_reports = EmployeeReport.objects.select_related(
            'employee__user',
            'step__step',
            'step__product',
        ).filter(status=EmployeeReport.Status.PENDING).order_by('-created_at')[:20]

        return Response(
            {
                'summary': {
                    'reports': report_summary,
                    'categories': Category.objects.count(),
                    'products': Product.objects.count(),
                    'active_products': Product.objects.filter(is_active=True).count(),
                    'process_steps': ProcessStep.objects.count(),
                    'product_process_steps': ProductProcessStep.objects.count(),
                },
                'pending_reports': EmployeeReportSerializer(
                    pending_reports,
                    many=True,
                    context={'request': request},
                ).data,
                'recent_reports': EmployeeReportSerializer(
                    recent_reports,
                    many=True,
                    context={'request': request},
                ).data,
                'management': {
                    'categories': '/api/v1/textile/categories/',
                    'products': '/api/v1/textile/products/',
                    'process_steps': '/api/v1/textile/process-steps/',
                    'product_process_steps': '/api/v1/textile/product-process-steps/',
                    'employee_reports': '/api/v1/textile/employee-reports/',
                },
            }
        )


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyByRole]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyByRole]
    filterset_class = ProductFilter
    search_fields = ['code', 'name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('bot_available') == 'true':
            return queryset.filter(
                is_active=True, productprocessstep__isnull=False
            ).distinct().order_by('name')
        return queryset


class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyByRole]
    filterset_class = ProcessStepFilter
    search_fields = ['name', 'description']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class ProductProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProductProcessStep.objects.select_related('step', 'product')
    serializer_class = ProductProcessStepSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyByRole]
    ordering_fields = ['created_at']
    ordering = ['order', 'step__name']

    def get_queryset(self):
        queryset = super().get_queryset()
        product = self.request.query_params.get('product')
        if product:
            queryset = queryset.filter(product_id=product)
        return queryset


class EmployeeReportViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeReportSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = EmployeeReportFilter
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    @action(detail=False, methods=['get'])
    def revenue(self, request):
        month = request.query_params.get('month')
        try:
            month_start = timezone.datetime.strptime(month, '%Y-%m').replace(
                tzinfo=timezone.get_current_timezone()
            )
        except (TypeError, ValueError):
            raise ValidationError({'month': 'Use YYYY-MM format.'})

        next_month = (
            month_start.replace(year=month_start.year + 1, month=1)
            if month_start.month == 12
            else month_start.replace(month=month_start.month + 1)
        )
        revenue_expression = ExpressionWrapper(
            F('count') * F('step__price'), output_field=IntegerField()
        )
        summary = self.get_queryset().filter(
            status=EmployeeReport.Status.APPROVED,
            created_at__gte=month_start,
            created_at__lt=next_month,
        ).aggregate(
            reports_count=Count('id'),
            pieces_count=Sum('count'),
            revenue=Sum(revenue_expression),
        )
        return Response({
            'month': month,
            'reports_count': summary['reports_count'] or 0,
            'pieces_count': summary['pieces_count'] or 0,
            'revenue': summary['revenue'] or 0,
        })

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

    def get_queryset(self):
        queryset = EmployeeReport.objects.select_related(
            'employee__user',
            'step__step',
            'step__product',
        )

        user = self.request.user
        if self._is_admin_user(user):
            return queryset

        if not user or not user.is_authenticated:
            return queryset.none()

        employee = getattr(user, 'profile', None)
        if employee is None:
            return queryset.none()

        return queryset.filter(employee=employee)

    def create(self, request, *args, **kwargs):
        if self._is_admin_user(request.user):
            raise PermissionDenied('Admins can only approve or reject reports.')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if self._is_admin_user(request.user):
            kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if self._is_admin_user(request.user):
            raise PermissionDenied('Admins can only approve or reject reports.')
        if instance.status in (EmployeeReport.Status.APPROVED, EmployeeReport.Status.REJECTED):
            raise ValidationError('Approved or rejected reports cannot be deleted.')
        return super().destroy(request, *args, **kwargs)

    def _set_status(self, request, status_value):
        report = self.get_object()
        if report.status != EmployeeReport.Status.PENDING:
            raise ValidationError('Only pending reports can be approved or rejected.')

        report = set_employee_report_status(report, status_value)
        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        return self._set_status(request, EmployeeReport.Status.APPROVED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        return self._set_status(request, EmployeeReport.Status.REJECTED)
