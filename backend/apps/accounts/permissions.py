from rest_framework import permissions


class IsAdminRole(permissions.BasePermission):
    """
    Allows access only to authenticated users with ADMIN role or superuser status.
    Returns HTTP 401 if unauthenticated, and HTTP 403 if authenticated but not an Admin.
    """
    message = "Administrator privileges are required to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            request.user.is_admin
        )


class IsStudentRole(permissions.BasePermission):
    """
    Allows access only to authenticated users with STUDENT role.
    """
    message = "Student privileges are required to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_active and
            request.user.is_student
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission allowing access to object owners or platform admins.
    Assumes object has a `user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_admin:
            return True

        owner = getattr(obj, 'user', None)
        return owner == request.user
