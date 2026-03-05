from rest_framework import permissions

# This class is used to verify that only the authenticated user who created the object is allowed to modify or delete it.
# Read-only access is allowed to all users.  Other users cannot modify or delete due to lack of privilege.
class IsAuthorOrReadOnly(permissions.BasePermission):
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user.is_authenticated and obj.author == request.user