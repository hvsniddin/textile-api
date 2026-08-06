from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .filters import EmployeeProfileFilter
from .models import User, EmployeeProfile
from .serializers import UserSerializer, EmployeeProfileSerializer, CreateEmployeeSerializer
from apps.textile.permissions import IsAdmin



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related('profile')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.select_related('user')
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_class = EmployeeProfileFilter
    search_fields = ['full_name', 'phone_number']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class CreateEmployeeView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=["post"], url_path="create-employee")
    def create_employee(self, request, *args, **kwargs):
        serializer = CreateEmployeeSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.save()
            user = data["user"]

            return Response(data=UserSerializer(user).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
