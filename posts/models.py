from django.db import models
from django.contrib.auth.models import AbstractUser

# --- USER MODEL (HW8 & Google Auth Requirements) ---
class User(AbstractUser):
    """
    Extends AbstractUser to support Google OAuth and Role-Based Access Control (RBAC).
    """
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    auth_provider = models.CharField(
        max_length=10, 
        choices=[('local', 'Local'), ('google', 'Google')],
        default='local'
    )
    profile_picture = models.URLField(blank=True, null=True)

    # HW8: Role-Based Access Control (RBAC)
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER  = 'user',  'User'
        GUEST = 'guest', 'Guest'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )

    # Resolve reverse accessor conflicts with default Django User
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_set',
        blank=True,
        help_text='Specific permissions for this user.'
    )

    class Meta:
        indexes = [
            models.Index(fields=['google_id']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.email


# --- POST MODEL (Factory Pattern & Privacy Requirements) ---
class Post(models.Model):
    """
    Supports different post types via Factory Pattern and Privacy settings for HW8.
    """
    POST_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
        ('text', 'Text'),
    )
    
    title = models.CharField(max_length=255, default="Untitled Post")
    content = models.TextField()
    # related_name='posts' allows counting and retrieval from the User model
    author = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default='text')
    metadata = models.JSONField(default=dict, blank=True)

    # HW8: Privacy Settings
    class Privacy(models.TextChoices):
        PUBLIC  = 'public',  'Public'
        PRIVATE = 'private', 'Private'

    privacy = models.CharField(
        max_length=10,
        choices=Privacy.choices,
        default=Privacy.PUBLIC,
    )

    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"


# --- INTERACTION MODELS (HW5 Requirements) ---

class Comment(models.Model):
    """
    Links users to posts for comments. 
    related_name='comments' is required for your Serializer counts.
    """
    text = models.TextField()
    author = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"


class Like(models.Model):
    """
    Links users to posts for likes.
    unique_together ensures a user can only like a post once.
    """
    user = models.ForeignKey(User, related_name='likes', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked Post {self.post.id}"


# --- AUTH PROVIDER MODEL ---
class ExternalAuthProvider(models.Model):
    """
    Supports Homework 6 External Auth tracking.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='external_auths')
    provider = models.CharField(
        max_length=50,
        choices=[('google', 'Google'), ('facebook', 'Facebook'), ('github', 'GitHub')],
        default='google'
    )
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['provider', 'provider_user_id']
        verbose_name = "External Authentication Provider"