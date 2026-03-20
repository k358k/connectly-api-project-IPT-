from rest_framework import permissions

class IsPostAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user

class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.author == request.user

class IsAdminRole(permissions.BasePermission):
    message = 'Access denied. Admin role required.'
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsOwnerOrAdmin(permissions.BasePermission):
    message = 'Access denied. You must be the post owner or an admin.'
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == 'admin':
            return True
        return obj.author == request.user

class PostPrivacyPermission(permissions.BasePermission):
    message = 'This post is private. Only the owner can view it.'
    def has_object_permission(self, request, view, obj):
        if obj.privacy == 'public':
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == 'admin':
            return True
        return obj.author == request.user