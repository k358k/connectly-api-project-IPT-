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


# ── HW8 ADDED: RBAC Permission Classes ───────────────────────────────────────

# What is a Permission Class?
#   A Permission Class is like a keycard reader attached to a specific door
#   in a building. When someone tries to enter that door, the keycard reader
#   checks their badge before letting them in. In our API, every time a user
#   sends a request to a protected endpoint, the permission class runs first
#   and decides whether to allow or block that request. If it returns True
#   the request is allowed to proceed. If it returns False the request is
#   blocked and the user receives an error response automatically.

# Why do we need these new classes for HW8?
#   Before HW8, any authenticated user could delete any post. There was no
#   concept of roles. Now we need to restrict certain actions so that only
#   users with the admin role can perform them. We also need to control who
#   can view a post based on whether that post is set to public or private.
#   These three new classes handle all of that logic in one place so we do
#   not have to repeat the same checks inside every single view.
# ── ─────────────────────────────────────────────────────────────────────────


class IsAdminRole(permissions.BasePermission):
    # ── HW8 ADDED: IsAdminRole ────────────────────────────────────────────────
    # This permission class checks whether the user who sent the request has
    # the admin role. If they do, the request is allowed to proceed. If they
    # do not, the request is blocked and a 403 Forbidden response is returned.
    
    # How it connects to the auth diagram:
    #   After the token is validated by SimpleJWT, Django calls this class
    #   which sits inside the Permissions box shown in the diagram. The method
    #   has_permission reads the role value from the request and returns either
    #   True to grant access or False to deny it.
    
    # Where it is used:
    #   This class is attached to the DELETE endpoint for posts and comments.
    #   Only users with role set to admin will be allowed to delete anything.
    #   A regular user or guest who tries to delete will receive a 403 error
    #   which means they are known to the system but do not have permission.
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────

    # This message is what the user sees in the error response when blocked
    message = 'Access denied. Admin role required.'

    def has_permission(self, request, view):
        # request.user is the person who sent the request
        # request.user.role is the role field we added to the User model
        # We read the role directly from the token payload so we do not need
        # to make an extra trip to the database to find out what role they have
        return (
            request.user is not None and
            request.user.is_authenticated and
            request.user.role == 'admin'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    # ── HW8 ADDED: IsOwnerOrAdmin ─────────────────────────────────────────────
    # This permission class handles situations where either the owner of a
    # post or an admin should be allowed to perform an action. Think of it
    # like a building where the owner of a room and the building manager both
    # have a key. Everyone else is turned away at the door.
    
    # How it works:
    #   If the user is an admin they are always allowed regardless of whether
    #   they own the post or not. If the user is a regular user they are only
    #   allowed if they are the author of the specific post being accessed.
    #   Anyone who is not the owner and not an admin receives a 403 error.
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────

    message = 'Access denied. You must be the post owner or an admin.'

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        # Admin bypasses ownership check and can access any post
        if request.user.role == 'admin':
            return True
        # Regular user must be the author of the post
        return obj.author == request.user


class PostPrivacyPermission(permissions.BasePermission):
    # ── HW8 ADDED: PostPrivacyPermission ──────────────────────────────────────
    # This permission class controls who is allowed to view a post based on
    # the privacy setting of that post. Think of it like a door with a sign
    # that says either Open to Everyone or Private. If the sign says Open to
    # Everyone then anyone can walk in. If the sign says Private then only
    # the owner of the room and the building manager are allowed inside.
    
    # The three scenarios this class handles:
    
    #   Scenario 1: The post is public
    #     Anyone can view it including users who are not logged in at all.
    #     This returns True immediately without checking anything else.
    
    #   Scenario 2: The post is private and the viewer is the owner or admin
    #     The owner of the post can always view their own private post.
    #     An admin can also always view any private post.
    #     Both of these return True.
    
    #   Scenario 3: The post is private and the viewer is someone else
    #     If the viewer is logged in but is not the owner and not an admin
    #     they will receive a 403 Forbidden response which means the system
    #     knows who they are but they do not have permission to view this post.
    #     If the viewer has no token at all and is completely unknown to the
    #     system the 401 Unauthorized response is handled directly inside the
    #     PostDetailView.get() method in views.py because Django REST Framework
    #     would return 403 by default for anonymous users and we need 401 to
    #     match the behavior shown in our authentication diagram.
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────

    message = 'This post is private. Only the owner can view it.'

    def has_object_permission(self, request, view, obj):
        # Public posts can be viewed by everyone including guests
        if obj.privacy == 'public':
            return True

        # Private post requires the viewer to be logged in first
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin can always view any private post
        if request.user.role == 'admin':
            return True

        # Only the post owner can view their own private post
        return obj.author == request.user

# ── END HW8 ADDED ─────────────────────────────────────────────────────────────