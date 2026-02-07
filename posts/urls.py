from django.urls import path
from posts.views import UserListCreate, LoginView, PostListCreate, PostDetailView

urlpatterns = [
    path('users/', UserListCreate.as_view(), name='user-list'),
    path('login/', LoginView.as_view(), name='login'), 
    path('posts/', PostListCreate.as_view(), name='post-list'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
]
