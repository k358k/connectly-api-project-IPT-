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

    # ── HW8 ADDED: Role field ─────────────────────────────────────────────────

    # We use TextChoices for CharField instead of IntegerField because:
    #   - CharField stores human-readable strings such as "admin" directly in
    #     the database, while IntegerField stores numbers such as 1, 2, and 3
    #     which require a separate lookup just to understand what they mean
    #   - IntegerField is risky because if you reorder the list, all the values
    #     shift as well. For example, what was 1=admin could accidentally become
    #     1=superadmin without anyone knowing it or understanding it clearly
    #   - TextChoices strictly validates the input, which means invalid values
    #     such as "ADMIN" in the wrong case or "superadmin" as an undefined role
    #     will never be allowed to be saved into the database
    # TextChoices is a Django feature that extends Python's str and Enum types,
    # offering a structured and readable way to define choices for CharField.
    
    # About default='user' and what get role='user' means:
    #   Imagine you already have 10 existing users in your database before this
    #   new role field was added. Those users never had a role assigned to them
    #   because the role feature did not exist yet at the time they were created.
    #   When you run the migration to add this new role column, Django needs to
    #   decide what value to fill in for those 10 users who never had a role.
    #   This is where default='user' comes in. It tells Django to automatically
    #   fill in the value 'user' for every existing row that does not have a
    #   role yet. So after the migration runs, all 10 existing users will now
    #   have role='user' assigned to them without you having to do anything
    #   manually. This also means no existing data is deleted or lost in the
    #   process which is exactly what we call zero data loss and it is the
    #   reason we chose Option 2 of our migration strategy over Option 1
    #   which would have required clearing and re-populating the database.

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        USER  = 'user',  'User'
        GUEST = 'guest', 'Guest'

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────

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

    POST_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
        ('text', 'Text'),
    )
    title = models.CharField(max_length=255, default="Untitled Post")

    content = models.TextField()
    # Adding related_name='posts' helps the User model find its posts
    author = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    post_type = models.CharField(max_length=10, choices=POST_TYPES, default='text')
    metadata = models.JSONField(default=dict, blank=True)

    # ── HW8 ADDED: Privacy field ──────────────────────────────────────────────

    # We use TextChoices for CharField for the same reasons as the Role field
    # above. It stores human-readable strings, prevents invalid values from
    # being saved, and gives us a structured way to define choices.
    
    # About default='public' and what backwards compatibility means:
    #   Imagine you already have 50 existing posts in your database before this
    #   new privacy field was added. Those posts never had a privacy setting
    #   assigned to them because the privacy feature did not exist yet at the
    #   time they were created. When you run the migration to add this new
    #   privacy column, Django needs to decide what value to fill in for those
    #   50 posts that never had a privacy setting.
    #   This is where default='public' comes in. It tells Django to
    #   automatically fill in the value 'public' for every existing post that
    #   does not have a privacy setting yet. This is intentional because those
    #   posts were created when everything was visible to everyone and the
    #   authors never chose to make them private. If we had used default='private'
    #   instead, all 50 existing posts would suddenly become invisible to every
    #   user the moment the migration runs, even though the authors never asked
    #   for that. That would be an unintended consequence that breaks the
    #   experience for everyone using the application. By using default='public'
    #   we make sure existing posts continue to behave exactly the way they
    #   always did which is what we call backwards compatibility.
    class Privacy(models.TextChoices):
        PUBLIC  = 'public',  'Public'
        PRIVATE = 'private', 'Private'

    privacy = models.CharField(
        max_length=10,
        choices=Privacy.choices,
        default=Privacy.PUBLIC,
    )
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────
    class Privacy(models.TextChoices):
        PUBLIC  = 'public',  'Public'
        PRIVATE = 'private', 'Private'

    privacy = models.CharField(
        max_length=10,
        choices=Privacy.choices,
        default=Privacy.PUBLIC,
    )
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────

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