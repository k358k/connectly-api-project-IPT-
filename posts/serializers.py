from rest_framework import serializers
from .models import User, Post, Comment

# Serializes User
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'created_at']


# Serializes Post and attaches a nested serializer of User
class PostSerializer(serializers.ModelSerializer):
    comments = serializers.StringRelatedField(many=True, read_only=True) # Many-to-One relationship, read only for client


    class Meta:
        model = Post
        fields = ['id', 'content', 'author', 'created_at', 'comments']


# Serializes Comment then validates post and author
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'text', 'author', 'post', 'created_at']


    def validate_post(self, value):
        if not Post.objects.filter(id=value.id).exists(): # Determines if post exists
            raise serializers.ValidationError("Post not found.")
        return value

    def validate_author(self, value):
        if not User.objects.filter(id=value.id).exists(): # Determines if author exists
            raise serializers.ValidationError("Author not found.")
        return value

