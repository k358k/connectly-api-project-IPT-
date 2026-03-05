from django.urls import path
from . import views
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
    # User and Local Auth
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), # Your class-based login
    
    # Third-Party / Google Auth (MS-2)
    path('auth/google/login/', views.google_login, name='google_login'),
    path('debug-token/', views.debug_token, name='debug-token'),
    
    # Posts
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('create-post/', CreatePostView.as_view(), name='create-post'),
    
    # Interactions
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
]