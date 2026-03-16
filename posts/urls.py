from django.urls import path
from . import views
from .views import (
    UserListCreate, 
    LoginView, 
    PostListCreate, 
    PostDetailView, 
    CreatePostView, 
    CommentListCreate,
    CommentDetailView,  # ── HW8 ADDED: handles admin-only comment deletion
    LikePostView,
    NewsFeedView  # <--- CRITICAL: Added for HW 7
)

urlpatterns = [
    # User and Local Auth
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), 

    
    # Third-Party / Google Auth (HW 6)

    # The testing link http://127.0.0.1:8000/posts/auth/google/login/ is no longer needed
    # because we have removed the GET method for the dummy token syntax in google_login
    # within views.py. We can now use our correct ngrok URL:
    # https://overoffensive-michal-turgid.ngrok-free.dev/login/, which was previously
    # inaccessible because the .env file was not available or included in GitHub.
    path('auth/google/login/', views.google_login, name='google_login'),
    path('debug-token/', views.debug_token, name='debug-token'),
    
    # Posts & News Feed (HW 7)
    # Testing link: http://127.0.0.1:8000/posts/feed/
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('feed/', NewsFeedView.as_view(), name='news-feed'), # <--- CRITICAL: Added for HW 7
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('create-post/', CreatePostView.as_view(), name='create-post'),
    
    
    # Interactions

    # FEEDBACK FIX: Comments are now connected to their specific post using the post ID in the URL.
    # Previously, comments had a separated endpoint which did not follow the required REST API format.
    path('posts/<int:post_id>/comments/', CommentListCreate.as_view(), name='comment-list-create'),

    # ── HW8 ADDED: Admin-only comment delete endpoint ─────────────────────────
    # Before HW8 there was no URL registered for deleting a specific comment.
    # The HW8 instructions require that only admin users can delete comments.
    # This new URL pattern makes it possible to target a specific comment by
    # providing both the post id and the comment id in the URL. When a DELETE
    # request is sent to this URL it is handled by CommentDetailView which
    # checks that the user is authenticated and has the admin role before
    # allowing the deletion to proceed.
    
    # How to use this endpoint in Postman:
    #   Method: DELETE
    #   URL: http://127.0.0.1:8000/posts/posts/{post_id}/comments/{comment_id}/
    #   Authorization: Bearer token with admin role
    
    #   If no token is provided the response will be 401 Unauthorized.
    #   If the token belongs to a non-admin user the response will be 403 Forbidden.
    #   If both the post and comment exist and the user is admin the response
    #   will be 200 OK with a message saying the comment was deleted successfully.
    # ── END HW8 ADDED ─────────────────────────────────────────────────────────
    path('posts/<int:post_id>/comments/<int:comment_id>/', CommentDetailView.as_view(), name='comment-detail'),

    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
]