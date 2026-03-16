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
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination

# SimpleJWT Authentication
from rest_framework_simplejwt.authentication import JWTAuthentication

# Local imports
from .models import User, Post, Comment, Like, ExternalAuthProvider
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from .permissions import IsPostAuthor, IsAuthorOrReadOnly

# ── HW8 ADDED: Import new RBAC permission classes ─────────────────────────────
# These three classes were created in permissions.py for HW8. We import them
# here so that we can attach them to the specific views that need them.
# IsAdminRole is used on endpoints that only admins are allowed to access.
# IsOwnerOrAdmin is used when both the owner and admin should have access.
# PostPrivacyPermission is used to control who can view a post based on
# whether that post is set to public or private.
# ── END HW8 ADDED ─────────────────────────────────────────────────────────────
from .permissions import IsAdminRole, IsOwnerOrAdmin, PostPrivacyPermission

# ── HW8 ADDED: Q object for combining multiple database filter conditions ─────
# Q is a Django tool that lets you combine multiple filter conditions when
# querying the database. Without Q you can only filter by one condition at
# a time. With Q you can say give me posts that are public OR posts that
# belong to the current user. The vertical bar between two Q objects means
# OR in the same way it does in regular Python code. We need this in HW8
# because the feed and post list need to return different sets of posts
# depending on the role and identity of the user making the request.
# ── END HW8 ADDED ─────────────────────────────────────────────────────────────
from django.db.models import Q

# Services for Google Auth (Homework 6)
from .services.google_auth import GoogleAuthService
from .services.user_service import UserService
from .services.token_service import TokenService

from factories.post_factory import PostFactory
from singletons.logger_singleton import LoggerSingleton

# Initialize the Singleton Logger
logger = LoggerSingleton().get_logger()

# --- HOMEWORK 7: NEWS FEED LOGIC ---

class FeedPagination(PageNumberPagination):
    """
    HW 7 Requirement: Pagination to limit results per request.
    """
    page_size = 5  # Returns 5 posts per page
    page_size_query_param = 'page_size'
    max_page_size = 100

class NewsFeedView(generics.ListAPIView):
    """
    HW 7 Requirement: GET /feed endpoint.
    Retrieves posts sorted by date (newest first) with pagination.
    """
    # ── HW8 CHANGED: NewsFeedView now filters posts by role and privacy ────────
    # Before HW8 the feed returned every single post in the database to everyone
    # regardless of who was asking or what the privacy setting of each post was.
    # Now the feed filters posts based on who is making the request.
    
    # The three different cases handled by get_queryset below:
    #
    #   Case 1: The request comes from an admin user
    #     An admin can see every post in the database including private ones.
    #     This is because admins are trusted to manage the entire application.
    
    #   Case 2: The request comes from a regular logged in user
    #     They can see all public posts plus their own private posts.
    #     They cannot see private posts that belong to other users.
    #
    #   Case 3: The request comes from a guest who is not logged in
    #     They can only see public posts. No private posts are returned at all.
    
    # Why we filter at the database level and not in Python code:
    #   Imagine the database has 10000 posts and 8000 of them are public. If
    #   we fetched all 10000 posts first and then removed the private ones in
    #   Python code, the server would have to load all 10000 posts into memory
    #   just to throw 2000 of them away. By filtering at the database level
    #   the database does the work and only sends back the 8000 posts we
    #   actually need. This is faster and uses far less server memory.
    
    # OLD code before HW8:
    # queryset = Post.objects.all().order_by('-created_at')
    # ── END HW8 CHANGED ───────────────────────────────────────────────────────
    serializer_class = PostSerializer
    pagination_class = FeedPagination
    permission_classes = [AllowAny] # Set to AllowAny for easy instructor testing
    authentication_classes = [JWTAuthentication] # HW8 ADDED: needed to identify the user inside get_queryset

    def get_queryset(self):
        user = self.request.user

        # Admin sees every post including private ones
        if user.is_authenticated and user.role == 'admin':
            return Post.objects.all().order_by('-created_at')

        # Authenticated user sees public posts and their own private posts
        if user.is_authenticated:
            return Post.objects.filter(
                Q(privacy='public') | Q(author=user)
            ).order_by('-created_at')

        # Guest sees only public posts
        return Post.objects.filter(privacy='public').order_by('-created_at')

# --- USER MANAGEMENT ---

class UserListCreate(APIView):
    permission_classes = [AllowAny]  # Allow anyone of the user to access it

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
    permission_classes = [AllowAny]  # Allow anyone to reach the login endpoint

    # GET: Render the Connectly login page with the Google Sign-In button
    def get(self, request):
        return render(request, 'login.html', {
            'google_client_id': settings.GOOGLE_CLIENT_ID,
        })
    
    # POST: Google redirects here with 'credential' after the user signs in
    def post(self, request):
        # Google One Tap / redirect mode sends the token as a form field 'credential'
        google_id_token = request.POST.get('credential') or request.data.get('credential')

        if not google_id_token:
            return render(request, 'login.html', {
                'google_client_id': settings.GOOGLE_CLIENT_ID,
                'error': 'No Google token received. Please try again.',
            })

        auth_service = GoogleAuthService()
        claims = auth_service.verify_token(google_id_token)

        if not claims:
            allowed_domain = getattr(settings, 'GOOGLE_ALLOWED_DOMAIN', None)
            return render(request, 'login.html', {
                'google_client_id': settings.GOOGLE_CLIENT_ID,
                'error': 'Access denied. Only school email addresses are allowed.',
                'allowed_domain': allowed_domain,
            })

        # Render the page with user info and the Google ID token.
        # The user copies this token and sends it to Postman to exchange for a JWT.
        return render(request, 'login.html', {
            'google_client_id': settings.GOOGLE_CLIENT_ID,
            'user_name':  claims.get('name', ''),
            'user_email': claims.get('email', ''),
            'id_token':   google_id_token,
        })

# --- POSTS & FACTORY ---

class PostListCreate(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ── HW8 CHANGED: PostListCreate now filters posts by role and privacy ──
        # Before HW8 this endpoint returned every post in the database to any
        # authenticated user without checking privacy. Now it checks the role
        # of the user and filters accordingly. An admin gets everything. A
        # regular user only gets public posts plus their own private posts.
        # OLD code before HW8:
        # posts = Post.objects.all()
        # ── END HW8 CHANGED ───────────────────────────────────────────────────
        user = request.user
        if user.role == 'admin':
            posts = Post.objects.all()
        else:
            posts = Post.objects.filter(
                Q(privacy='public') | Q(author=user)
            )
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PostDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    # ── HW8 CHANGED: permission_classes replaced with get_permissions method ───
    # Before HW8 this view had a fixed permission_classes list that applied the
    # same permissions to every HTTP method. The problem is that GET and DELETE
    # need completely different permission rules. GET needs to be open to guests
    # so they can view public posts. DELETE needs to be restricted to admins only.
    # Having one fixed list cannot handle both cases at the same time. The
    # get_permissions method solves this by returning a different set of
    # permission classes depending on which HTTP method was used in the request.
    # OLD code before HW8:
    # permission_classes = [IsAuthenticated, IsAuthorOrReadOnly]
    # ── END HW8 CHANGED ───────────────────────────────────────────────────────

    def get_permissions(self):
        if self.request.method == 'DELETE':
            # IsAuthenticated checks if a token was provided at all.
            # If no token was provided the user receives a 401 Unauthorized.
            # IsAdminRole then checks if the authenticated user has the admin
            # role. If they do not they receive a 403 Forbidden response.
            return [IsAuthenticated(), IsAdminRole()]
        # GET is open to everyone and privacy is checked manually inside get()
        return [AllowAny()]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        # ── HW8 ADDED: Privacy enforcement for GET /posts/{id} ────────────────
        # When someone requests a specific post we need to check whether that
        # post is private and if so whether the person requesting it is allowed
        # to see it. There are three possible scenarios:
        
        #   Person A is the owner of the post
        #     They are always allowed to view their own post regardless of the
        #     privacy setting. They receive a 200 OK response.
        
        #   Person B is a logged in user who is not the owner
        #     They know who this person is but they do not own this post.
        #     They receive a 403 Forbidden response which means the system
        #     knows who they are but they are not allowed to view this post.
        
        #   Person C has no token at all and is completely unknown
        #     They receive a 401 Unauthorized response which means the system
        #     does not know who they are and cannot verify their identity.
        #     We handle this manually here because Django REST Framework would
        #     return 403 by default for anonymous users but we need 401 to
        #     match the behavior shown in our authentication diagram.
        # ── END HW8 ADDED ─────────────────────────────────────────────────────
        if post.privacy == 'private':

            if not request.user or not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required to view this private post.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if request.user.role != 'admin' and post.author != request.user:
                return Response(
                    {'error': 'This post is private. Only the owner can view it.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # ── HW8 CHANGED: self.check_object_permissions removed ────────────────
        # The old code used self.check_object_permissions to run the permission
        # classes against the specific post object. This is no longer needed
        # because we now handle all privacy checks manually in the if block
        # above which gives us full control over the exact error responses.
        # OLD code before HW8:
        # self.check_object_permissions(request, post)
        # ── END HW8 CHANGED ───────────────────────────────────────────────────
        serializer = PostSerializer(post)
        return Response(serializer.data)
    
    # I added this to trigger the 403 Forbidden status code in Postman, as shown in the diagram
    # The reason for this is that I previously forgot this functionality on our code for HW#6
    # The intended way to trigger this error is by attempting to delete posts that do not belong to the user, which is now correctly handled.
    # ── HW8 CHANGED: delete is now restricted to admin users only ─────────────
    # Before HW8 only the author of a post could delete it. Now only users with
    # the admin role can delete any post. The permission classes set up in
    # get_permissions above handle the 401 and 403 responses automatically
    # before this method is even called. By the time the code inside this
    # method runs we already know the user is authenticated and is an admin.
    # OLD code before HW8 used self.check_object_permissions which checked
    # whether the user was the author. That check is no longer needed here.
    # ── END HW8 CHANGED ───────────────────────────────────────────────────────
    def delete(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            post.delete()
            logger.info(f"Post {pk} deleted by admin {request.user.id}")
            return Response({'message': 'Post deleted successfully'}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

class CreatePostView(APIView):
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

# --- COMMENTS & LIKES ---

# FEEDBACK FIX: We added JWT token authentication and permission classes, consistent with PostListCreate and PostDetailView, so that only verified users can access comments.
# FEEDBACK FIX: Comments are now connected to a specific post in the URL instead of being separated from PostListCreate and PostDetailView.
# FEEDBACK FIX: You can now view all comments on a specific post using the GET method, which was not possible before.
class CommentListCreate(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
 
    def get(self, request, post_id):
        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        comments = Comment.objects.filter(post_id=post_id)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)
 
    def post(self, request, post_id):
        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        data = {**request.data, 'post': post_id}
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── HW8 ADDED: CommentDetailView ─────────────────────────────────────────────
# Before HW8 there was no way to delete a comment through the API at all.
# The HW8 instructions say that only admin users should be able to delete
# posts or comments. This new view adds that missing DELETE functionality
# for comments and restricts it to admin users only following the same
# pattern used in PostDetailView above.

# How the permission check works here:
#   When a DELETE request arrives, get_permissions returns IsAuthenticated
#   and IsAdminRole. IsAuthenticated checks whether the request has a valid
#   token at all. If there is no token the user receives a 401 Unauthorized
#   response. If there is a valid token IsAdminRole then checks whether that
#   user has the admin role. If they are not an admin they receive a 403
#   Forbidden response. Only if both checks pass does the delete method run.
# ── END HW8 ADDED ─────────────────────────────────────────────────────────────
class CommentDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    def delete(self, request, post_id, comment_id):
        # Verify the parent post exists first
        try:
            Post.objects.get(pk=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        # Then find the specific comment that belongs to that post
        try:
            comment = Comment.objects.get(pk=comment_id, post_id=post_id)
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)

        # By the time we reach this line the permission classes above have
        # already confirmed the user is authenticated and has the admin role
        comment.delete()
        logger.info(f"Comment {comment_id} deleted by admin {request.user.id}")
        return Response({'message': 'Comment deleted successfully'}, status=status.HTTP_200_OK)


# FEEDBACK FIX: Added JWTAuthentication and IsAuthenticated to create a secured endpoint.
# This ensures only logged-in users can like or unlike posts, maintaining consistency
# with other protected views like PostListCreate and PostDetailView.
class LikePostView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

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

# --- GOOGLE AUTH VIEWS (HW 6) ---

@csrf_exempt
def google_login(request):
    """
    HW 6 Requirement: Handle Google Login, Domain Validation, and Return JWT.
    """
    # FEEDBACK FIX: We removed the GET method for dummy token syntax because we had brought back the 'env file.' 
    # This file allows us to direct traffic to our ngrok URL: https://overoffensive-michal-turgid.ngrok-free.dev/login/
    # This means, we can now properly obtain the Google token, along with the JWT token, in Postman for submission.

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        google_id_token = data.get('google_id_token')

        # FIX 1: If you don't provide a Google token, it will return a 400 error. This means a Google token is required and cannot be empty.
        if not google_id_token:
            return JsonResponse({'error': 'google_id_token is required in request body.'}, status=400)
        
        auth_service = GoogleAuthService()
        claims = auth_service.verify_token(google_id_token)

        # Check claims FIRST before accessing any fields on it
        if not claims:
            return JsonResponse({'error': 'Token verification failed. Token may be expired or invalid.'}, status=401)
 
        # FIX 2: To force this error, we need to mark the Google account we logged in with as verified 
        # Then, sign in again to get the token and paste it into the environment variables in postman within the directory we created.
        if not claims.get('email_verified'): # or claims.get('email_verified') - TEMP: force trigger
            return JsonResponse({'error': 'Your Google account email address is not verified. Please verify your email address with Google and try again'}, status=401)

        # FIX 3: To make this specific error appear, we need to do a few things with the Google account you're using
        # First, we have to make sure the account is marked as 'verified,' which basically means confirming it's linked to our institution domain. 
        # After that, you'll need to sign out of your Google account and then sign-in again
        # Once you're log-in is succesfull, you'll need to get the token from the payload by using developer tools, you'll find it in more tools using the 3 dots icon in the upper right corner
        # After that, you'll send it the request again in postman as a new POST request method. Following these steps should reliably produce the error we're looking for.
        # We've also updated the type of error message you'll receive. Previously, it might have shown a '403 Forbidden' error
        # This type of error usually means you don't have permission to do a certain action. However, we've changed it to a '401 Unauthorized' error, which is a more accurate description for this particular situation
        # The reason for this change is that the '403 Forbidden' error was accidentally put in the wrong place in our code, specifically in a part called google_login within the views.py file. 
        # The '403 Forbidden' error is actually meant for situations where a user truly lacks the necessary permissions for an action, such as trying to delete a post
        # That correct logic for permission-related errors is handled in a different file, permissions.py
        # So, if you were to try and delete a post without the right permissions, you would then see a message like: 'You do not have permission to perform this action.'

        # DOMAIN VALIDATION: Ensures only school emails can log in
        user_email = claims.get('email', '')
        if not user_email.endswith('@mmdc.mcl.edu.ph'): # or user_email.endswith('@mmdc.mcl.edu.ph') - TEMP: force trigger
            return JsonResponse({
                'error': 'Invalid Google token. Only @mmdc.mcl.edu.ph email addresses are allowed.'
            }, status=401)
        
        # Linking Google tokens to user profiles
        user_service = UserService()
        user, is_new = user_service.find_or_create_user(claims)
        
        # Token Validation: Generating local JWT
        # ── HW8 NOTE: role is now included in the token payload ───────────────
        # TokenService.generate_token was updated in HW8 to also store the
        # user's role inside the token. This means every time this login
        # endpoint runs successfully and generates a new token, that token
        # will carry the role of the user who just logged in. The permission
        # classes in permissions.py will then be able to read that role
        # instantly on every future request without needing to query the
        # database. We also return the role in the response below so that
        # anyone testing in Postman can immediately confirm what role was
        # assigned to the user who just logged in.
        # ── END HW8 NOTE ──────────────────────────────────────────────────────
        internal_token = TokenService.generate_token(user)
        
        return JsonResponse({
            'access_token': internal_token['access'],
            'refresh_token': internal_token['refresh'],
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name() or user.username,
                'auth_provider': getattr(user, 'auth_provider', 'google'),
                'profile_picture': getattr(user, 'profile_picture', ''),
                'is_new_user': is_new,
                'role': user.role, # HW8 ADDED: role is now returned in the login response
            }
        }, status=200)
    
    # FIX 4: Instead of a 500 status code (which means your system is completely broken), we've changed this to a 409 status code
    # The 409 code is the correct one to use when there's a specific conflict happening in your database.
    except IntegrityError:
        return JsonResponse({'error': 'Account creation failed. Email address may already be in use.'}, status=409)

    # FIX 5: The status code 500 is actually correct for this situation
    # However, the corresponding error message is missing, as indicated in our AAF Diagram.
    except DatabaseError:
        return JsonResponse({'error': 'Account creation failed due to a database error. Please try again later.'}, status=500)

    # INTERNAL SERVER ERROR
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 

@csrf_exempt
def debug_token(request):
    token = request.POST.get('credential')
    return JsonResponse({"token_received": bool(token), "token_length": len(token) if token else 0})