from rest_framework import serializers
from .models import User, Post, Comment, Like   

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email'] # Password is EXCLUDED

# This serializer includes related posts for a user
class PostSerializer(serializers.ModelSerializer):
    # This allows you to see comments when you view a post
    comments = serializers.StringRelatedField(many=True, read_only=True)

    # These fields will show the count of likes and comments for each post
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)


    class Meta:
        model = Post
        fields = ['id', 'content', 'author', 'created_at', 'comments', 'like_count', 'comment_count']

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
