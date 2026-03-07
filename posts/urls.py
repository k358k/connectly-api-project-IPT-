from django.urls import path
from . import views
from .views import (
    UserListCreate, 
    LoginView, 
    PostListCreate, 
    PostDetailView, 
    CreatePostView, 
    CommentListCreate, 
    LikePostView,
    NewsFeedView  # <--- CRITICAL: Added for HW 7
)

urlpatterns = [
    # User and Local Auth
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), 
    
    # Third-Party / Google Auth (HW 6)
    # Testing link: http://127.0.0.1:8000/posts/auth/google/login/
    path('auth/google/login/', views.google_login, name='google_login'),
    path('debug-token/', views.debug_token, name='debug-token'),
    
    # Posts & News Feed (HW 7)
    # Testing link: http://127.0.0.1:8000/posts/feed/
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('feed/', NewsFeedView.as_view(), name='news-feed'), # <--- CRITICAL: Added for HW 7
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('create-post/', CreatePostView.as_view(), name='create-post'),
    
    # Interactions
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
]