from django.urls import path
from .views import UserListCreate, PostListCreate, CommentListCreate, LikePostView

urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),

]