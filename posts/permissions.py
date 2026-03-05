from rest_framework import permissions

class IsPostAuthor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Allow access if user is in 'Admin' group
        if request.user.groups.filter(name='Admin').exists():
            return True
        # Otherwise, only the owner can edit/delete
        return obj.author == request.user
