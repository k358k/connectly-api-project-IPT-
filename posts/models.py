from django.db import models
from django.contrib.auth.models import AbstractUser

# This part defines what a "User" looks like in your database
# Changed from User (model) to AbstractUser model. We used AbstractUser in order to activate the attributes of google OAuth
class User(AbstractUser):
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    auth_provider = models.CharField(
        max_length=10, 
        choices=[('local', 'Local'), ('google', 'Google')],
        default='local'
    )
    profile_picture = models.URLField(blank=True, null=True)
    
    # Adding groups and permissions field to avoid the old user model from being identified to new model which "AbstractUser" model
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',  
        related_query_name='custom_user'
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',  
        related_query_name='custom_user'
    )

    # Added Google OAuth features
    class Meta:
        indexes = [
            models.Index(fields=['google_id']),
            models.Index(fields=['email']),
        ]

    # This is usually used to get the email address of a user    
    def __str__(self):
        return self.email
    
# This part defines what a "Post" looks like and links it to a User
class Post(models.Model):
    content = models.TextField()
    # Adding related_name='posts' helps the User model find its posts
    author = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This matches the specific format in your instructions
        return f"Post by {self.author.username} at {self.created_at}"

# This part defines what a "Comment" looks like and links it to both User and Post
class Comment(models.Model):
    text = models.TextField()
    # These related_names are crucial for the Serializers to work later
    author = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"
    
# This part defines what a "Like" looks like and links it to both User and Post   
class Like(models.Model):
    user = models.ForeignKey(User, related_name='likes', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This ensures a user can only like a specific post once
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked Post {self.post.id}"
    

# Added this class to provide a better user experience by allowing users to log in with their existing accounts from external providers that is link with google like github, facebook, etc
class ExternalAuthProvider(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='external_auths'
    )
    provider = models.CharField(
        max_length=50,
        choices=[('google', 'Google'), ('facebook', 'Facebook'), ('github', 'GitHub')],
        default='google'
    )
    provider_user_id = models.CharField(max_length=255)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    id_token = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Added this to sets up the rules for the ExternalAuthProvider model. One important rule is that it prevents a user from accidentally connecting the same Google (or Facebook, or GitHub) account multiple times. This ensures that the data stays clean and consistent, and that there aren't any confusing duplicate entries in the system
    class Meta:
        unique_together = ['provider', 'provider_user_id']
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
            models.Index(fields=['user', 'provider']),
        ]
        verbose_name = "External Authentication Provider"
        verbose_name_plural = "External Authentication Providers"
    
    def __str__(self):
        return f"{self.user.email} - {self.provider}"