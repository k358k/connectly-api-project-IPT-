from django.urls import path
from . import views
from .views import UserListCreate, PostListCreate, CommentListCreate, LikePostView

urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
    path('login/', views.login_view, name='login'),
    path('auth/google/login', views.google_login, name='google_login'),
    path('debug-token/', views.debug_token, name='debug-token'), # Added to debug the errors occur on a google server. (Optional for testing onlu)
]