<<<<<<< HEAD
from django.urls import path, include
from .views import UserListCreate, PostListCreate, CommentListCreate



urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list-create'),
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'),
]
=======
from django.urls import path
from posts.views import UserListCreate, LoginView, PostListCreate, PostDetailView

urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), 
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
]
>>>>>>> origin/Ricohermozo_Security
