import os
import json
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, DatabaseError
from django.conf import settings
from django.contrib.auth import authenticate

# REST Framework imports
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

# SimpleJWT Authentication (The standard for MS-2)
from rest_framework_simplejwt.authentication import JWTAuthentication

# Local imports
from .models import User, Post, Comment, Like, ExternalAuthProvider
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from .permissions import IsPostAuthor, IsAuthorOrReadOnly
from factories.post_factory import PostFactory
from singletons.logger_singleton import LoggerSingleton

# Services for Google Auth
from .services.google_auth import GoogleAuthService
from .services.user_service import UserService
from .services.token_service import TokenService

# Initialize the Singleton Logger
logger = LoggerSingleton().get_logger()

# --- USER MANAGEMENT ---

class UserListCreate(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({"error": "Username and password required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.create_user(username=username, password=password)
        logger.info(f"User created: {username}")
        return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            return Response({"message": "Authenticated!"})
        return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

# --- POSTS & FACTORY ---

class PostListCreate(APIView):
    authentication_classes = [JWTAuthentication] # Use JWT for MS-2
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PostDetailView(APIView):
    """
    Combines MS-1 Metadata and MS-2 RBAC/Permissions logic.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            self.check_object_permissions(request, post)
            serializer = PostSerializer(post)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

class CreatePostView(APIView):
    """Uses the PostFactory from MS-1"""
    def post(self, request):
        data = request.data
        try:
            post = PostFactory.create_post(
                post_type=data.get('post_type'),
                author_id=data.get('author'),
                title=data.get('title'),
                content=data.get('content', ''),
                metadata=data.get('metadata', {})
            )
            logger.info(f"Post created via Factory: {post.id}")
            return Response({'message': 'Post created successfully!', 'post_id': post.id}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            logger.error(f"Post creation failed: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# --- COMMENTS & LIKES (HW 5) ---

class CommentListCreate(APIView):
    def get(self, request):
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LikePostView(APIView):
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        like, created = Like.objects.get_or_create(user=user, post=post)
        if not created:
            like.delete()
            return Response({"message": "Post unliked"}, status=status.HTTP_200_OK)
        return Response({"message": "Post liked"}, status=status.HTTP_201_CREATED)

# --- GOOGLE AUTH VIEWS (MS-2) ---

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        google_token = request.POST.get('credential')
        if google_token:
            auth_service = GoogleAuthService()
            claims = auth_service.verify_token(google_token)
            if claims:
                user_service = UserService()
                try:
                    user, is_new = user_service.find_or_create_user(claims)
                    context = {
                        'google_client_id': settings.GOOGLE_CLIENT_ID,
                        'id_token': google_token,
                        'user_email': user.email,
                        'user_name': user.get_full_name()
                    }
                    return render(request, 'login.html', context)
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    return render(request, 'login.html', {'error': 'Failed to create user account.'})
        return render(request, 'login.html', {'error': 'Invalid token'})
    
    return render(request, 'login.html', {'google_client_id': settings.GOOGLE_CLIENT_ID})

@csrf_exempt
def google_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        google_id_token = data.get('google_id_token')
        auth_service = GoogleAuthService()
        claims = auth_service.verify_token(google_id_token)
        
        if not claims or not claims.get('email_verified'):
            return JsonResponse({'error': 'Token verification failed'}, status=401)
        
        user_service = UserService()
        user, is_new = user_service.find_or_create_user(claims)
        internal_token = TokenService.generate_token(user)
        
        return JsonResponse({
            'access_token': internal_token['access'],
            'refresh_token': internal_token['refresh'],
            'user': {'id': user.id, 'email': user.email}
        }, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def debug_token(request):
    token = request.POST.get('credential')
    return JsonResponse({"token_received": bool(token), "token_length": len(token) if token else 0})