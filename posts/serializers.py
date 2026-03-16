from rest_framework import serializers
from .models import User, Post, Comment, Like   

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Password is EXCLUDED
        # ── HW8 ADDED: role field added to UserSerializer ─────────────────────
        # Before HW8 the API response for a user only showed the id, username,
        # and email. The role field did not exist yet so there was nothing to
        # show. Now that we have added the role field to the User model we also
        # need to include it here so that anyone reading the API response can
        # see what role that user has. Without adding it here the role would
        # exist in the database but would never appear in any API response
        # which would make it impossible to verify during Postman testing.
        # ── END HW8 ADDED ─────────────────────────────────────────────────────
        fields = ['id', 'username', 'email', 'role']

# This serializer includes related posts for a user
class PostSerializer(serializers.ModelSerializer):
    # This allows you to see comments when you view a post
    comments = serializers.StringRelatedField(many=True, read_only=True)

    # These fields will show the count of likes and comments for each post
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = Post
        # ── HW8 CHANGED: privacy field added to PostSerializer ────────────────
        # Before HW8 the API response for a post did not include the privacy
        # field because it did not exist yet. Now that we have added it to the
        # Post model we need to include it here as well so that the privacy
        # value shows up in every API response for a post. This allows users
        # to see whether a post is public or private and also allows them to
        # set the privacy when creating a new post by including it in the
        # request body.
        # OLD fields list before HW8:
        # fields = ['id', 'content', 'author', 'created_at', 'comments', 'like_count', 'comment_count']
        # ── END HW8 CHANGED ───────────────────────────────────────────────────
        fields = ['id', 'title', 'content', 'author', 'created_at', 'comments', 'like_count', 'comment_count', 'privacy']

        # ── HW8 ADDED: read_only_fields for author ────────────────────────────
        # When a user creates a new post by sending a POST request, the author
        # of that post should be set automatically to whoever is currently
        # logged in. This is handled in the view using the line
        # serializer.save(author=request.user) which attaches the logged in
        # user as the author before saving. However if we do not mark author
        # as read only here, Django REST Framework will expect the user to
        # manually include the author field in the request body. If they forget
        # to include it the API will return a 400 Bad Request error saying that
        # the author field is required. By marking it as read only we tell
        # Django REST Framework that the author will always be provided by the
        # server and should never be required from the user in the request body.
        # ── END HW8 ADDED ─────────────────────────────────────────────────────
        read_only_fields = ['author']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'text', 'author', 'post', 'created_at']

    # Validation to make sure the post exists
    def validate_post(self, value):
        if not Post.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Post not found.")
        return value

    # Validation to make sure the author exists
    def validate_author(self, value):
        if not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Author not found.")
        return value