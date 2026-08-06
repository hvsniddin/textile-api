from rest_framework import permissions

from apps.authentication.models import User


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission that allows admin users to perform any action,
    while non-admin users can only view (read-only).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsAdminOrReadOnlyByRole(permissions.BasePermission):
    """
    Permission that allows admin role users to perform any action,
    while non-admin users can only view (read-only).
    Checks the custom 'role' field on the User model, or is_staff/is_superuser.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow if user is superuser, staff, or has admin role
        return (
            request.user.is_superuser
            or request.user.is_staff
            or (hasattr(request.user, 'role') and request.user.role == User.Role.ADMIN)
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Allow if user is superuser, staff, or has admin role
        return (
            request.user.is_superuser
            or request.user.is_staff
            or (hasattr(request.user, 'role') and request.user.role == User.Role.ADMIN)
        )

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or (hasattr(request.user, 'role') and request.user.role == 'admin')
            )
        )
