from django.urls import path
from .views import (
    UserListCreate, 
    LoginView, 
    PostListCreate, 
    PostDetailView, 
    CreatePostView, 
    CommentListCreate, 
    LikePostView
)

urlpatterns = [
    # User and Auth
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'),
    
    # Posts
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('create-post/', CreatePostView.as_view(), name='create-post'),
    
    # Interactions
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
]