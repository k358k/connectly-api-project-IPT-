from django.urls import path
from . import views
from .views import (
    UserListCreate, 
    LoginView, 
    PostListCreate, 
    PostDetailView, 
    CreatePostView, 
    CommentListCreate,
    CommentDetailView,
    LikePostView,
    NewsFeedView
)

urlpatterns = [
    # --- User and Auth ---
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), 
    path('auth/google/login/', views.google_login, name='google_login'),
    
    # --- News Feed (Optimized & Paginated) ---
    path('feed/', NewsFeedView.as_view(), name='news-feed'),

    # --- Posts ---
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    # Highlight this during demo: "Our Factory Pattern endpoint"
    path('posts/create-factory/', CreatePostView.as_view(), name='create-post-factory'), 
    
    # --- Interactions (Likes & Comments) ---
    # Instructor Feedback Fix: Ensuring 'like' and 'comment' endpoints follow the {post_id} pattern
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
    path('posts/<int:post_id>/comment/', CommentListCreate.as_view(), name='comment-create'),
    path('posts/<int:post_id>/comments/', CommentListCreate.as_view(), name='comment-list'),
    path('posts/<int:post_id>/comments/<int:comment_id>/', CommentDetailView.as_view(), name='comment-detail'),
]