from rest_framework.permissions import BasePermission

class IsPostAuthor(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Step 3: Only allow access if the user is the author
        return obj.author == request.user