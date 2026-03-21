from django.views.decorators.csrf import csrf_exempt
import os
import json
import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.core.cache import cache  # NEW: Added for Caching

# REST Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

# Local imports
from .models import User, Post, Comment, Like
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from .permissions import IsAdminRole, IsOwnerOrAdmin, PostPrivacyPermission

# Services & Patterns
from factories.post_factory import PostFactory
from singletons.logger_singleton import LoggerSingleton
# NEW: Import your Config Singleton (make sure this file exists in your project)
# Change this line in your views.py
from singletons.config_manager import ConfigManager


# --- 1. SETUP ---
logger = LoggerSingleton().get_logger()
config = ConfigManager()

class FeedPagination(PageNumberPagination):
    # Change this line to use your get_setting method:
    page_size = config.get_setting("DEFAULT_PAGE_SIZE") 
    page_size_query_param = 'page_size'
    max_page_size = 100

# --- 2. AUTH & USERS ---
class LoginView(TokenObtainPairView):
    """Standard JWT Login View"""
    pass

class UserListCreate(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST': 
            return [AllowAny()]
        return [IsAdminRole()]
    
    def perform_create(self, serializer):
        # 1. Save the user first (this creates the record)
        user = serializer.save()
        
        # 2. Grab the password directly from the request data
        raw_password = self.request.data.get('password')
        
        # 3. Hash the password manually so the login works later
        if raw_password:
            user.set_password(raw_password)
            user.save()

@csrf_exempt
def google_login(request):
    """Placeholder for Google Auth - Requirement for HW6"""
    return JsonResponse({'message': 'Google Login process initiated'}, status=200)

# --- 3. POSTS & FACTORY ---
class PostListCreate(generics.ListCreateAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        cache.clear() # NEW: Invalidate cache when new content is added

class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsOwnerOrAdmin]

class CreatePostView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            post = PostFactory.create_post(
                post_type=request.data.get('post_type'),
                title=request.data.get('title'),
                content=request.data.get('content', ''),
                author=request.user,
                metadata=request.data.get('metadata', {}),
                privacy=request.data.get('privacy', 'public')
            )
            serializer = PostSerializer(post)
            
            # NEW: Invalidate the news feed cache so the new post appears
            cache.clear() 
            
            logger.info(f"Factory created {post.post_type} post for user {request.user.id}")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --- 4. NEWS FEED (Optimization) ---

class NewsFeedView(generics.ListAPIView):
    serializer_class = PostSerializer
    pagination_class = FeedPagination
    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]

    # NEW: list method added to handle Cache logic
    def list(self, request, *args, **kwargs):
        user_id = request.user.id if request.user.is_authenticated else "guest"
        page = request.query_params.get('page', 1)
        cache_key = f"feed_user_{user_id}_page_{page}"

        cached_data = cache.get(cache_key)
        if cached_data:
            print(f">>> CACHE HIT: Serving Feed for {user_id}") # ADD THIS
            return Response(cached_data, headers={"X-Cache": "HIT"})

        response = super().list(request, *args, **kwargs)
        print(f">>> CACHE MISS: Database Query for {user_id}") # ADD THIS

        timeout = config.get_setting("CACHE_TIMEOUT") or 60
        cache.set(cache_key, response.data, timeout)
        
        response.headers["X-Cache"] = "MISS"
        return response

    def get_queryset(self):
        # Retained Eager Loading (HW9)
        queryset = Post.objects.select_related('author').prefetch_related('comments', 'likes').order_by('-created_at')
        user = self.request.user
        if user.is_authenticated:
            if user.role == 'admin': return queryset
            return queryset.filter(Q(privacy='public') | Q(author=user))
        return queryset.filter(privacy='public')

# --- 5. INTERACTIONS ---
class LikePostView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if not created:
            like.delete()
            cache.clear() # Invalidate cache on unlike
            return Response({'message': 'Unliked'}, status=200)
        
        cache.clear() # Invalidate cache on like
        return Response({'message': 'Liked'}, status=201)

class CommentListCreate(APIView):
    authentication_classes = [JWTAuthentication]
    def get_permissions(self):
        if self.request.method == 'POST': return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id).select_related('author')
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if post.privacy == 'private' and post.author != request.user and request.user.role != 'admin':
            return Response({'error': 'Private post'}, status=403)
        
        data = request.data.copy()
        data.update({'post': post_id, 'author': request.user.id})
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            cache.clear() # Invalidate cache so new comment count shows up
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsOwnerOrAdmin]
    lookup_url_kwarg = 'comment_id'