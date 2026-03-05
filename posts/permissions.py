from rest_framework import permissions

# Version from MS-1 (Strict)
class IsPostAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Only allow access if the user is the author
        return obj.author == request.user

# Version from MS-2 (Allows public viewing, but restricted editing)
class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow authors of an object to edit it.
    Assumes the model instance has an `author` attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only permissions are allowed for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the author of the post
        return request.user.is_authenticated and obj.author == request.user