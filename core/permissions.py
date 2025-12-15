from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """Только админ может изменять, остальные могут читать"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)


class IsAdmin(permissions.BasePermission):
    """Только админ"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

