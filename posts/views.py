import os
import json
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, DatabaseError
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsAuthorOrReadOnly
from .models import User, Post, Comment, Like, ExternalAuthProvider
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from .services.google_auth import GoogleAuthService
from .services.user_service import UserService
from .services.token_service import TokenService

# Used to identify where errors occur within the system itself.
logger = logging.getLogger(__name__)

# This class handles getting all users and creating a new one
class UserListCreate(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# This class handles getting all posts and creating a new one
class PostListCreate(APIView):
    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# This class uses a custom permission that allows any user to view the content, but only the authenticated author of the content can modify or delete it
class PostDetailView(APIView):
    permission_classes = [IsAuthorOrReadOnly]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            self.check_object_permissions(request, post)
            serializer = PostSerializer(post)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

# This class handles getting all comments and creating a new one
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
    
# This class handles liking and unliking a post
class LikePostView(APIView):
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        # Expecting {"user_id": <id>} in the Postman request body
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        # The Toggle Logic
        like, created = Like.objects.get_or_create(user=user, post=post)

        if not created:
            # If the record already existed, delete it (Unlike)
            like.delete()
            return Response({"message": "Post unliked"}, status=status.HTTP_200_OK)

        # If it's a new record (Like)
        return Response({"message": "Post liked"}, status=status.HTTP_201_CREATED)
    
# It is used to display the login page, including the Google Client ID needed for the Google Sign-In button
@csrf_exempt
def login_view(request):

    # It displays the login page and handles the Google Sign-In authentication response (POST request). After successful authentication and verification, it provides access to the token
    logger.info(f"login_view accessed with method: {request.method}")
    logger.info(f"Content-Type: {request.content_type}")
    
    # Using this to handle the POST request from Google (this is where the token arrives)
    if request.method == 'POST':
        logger.info("Processing POST request from Google")
        
        # It tracks all authentication request from Google (POST) for debugging
        logger.info(f"POST data keys: {list(request.POST.keys())}")
        
        # After user login from google sign-in button, it authenticate here until it form a JWT token based on the credential of the user
        google_token = request.POST.get('credential')
        
        if google_token:
            logger.info(f"Google token received! Length: {len(google_token)}")
            logger.info(f"Token preview: {google_token[:100]}...")
            
            # Verifying the token and generate JWT token
            auth_service = GoogleAuthService()
            claims = auth_service.verify_token(google_token)
            
            if claims:
                logger.info(f"Google token verified! Email: {claims.get('email')}")
                
                if not claims.get('email_verified'):
                    logger.warning("Email not verified")
                    context = {
                        'google_client_id': settings.GOOGLE_CLIENT_ID,
                        'error': 'Your Google account email address is not verified.'
                    }
                    return render(request, 'login.html', context)
                
                # Finds an existing user or creates a new one based on the verified Google claims
                user_service = UserService()
                try:
                    user, is_new = user_service.find_or_create_user(claims)
                    logger.info(f"User created/retrieved: {user.email} (is_new: {is_new})")
                    
                    # Generates an internal JWT token for the authenticated user
                    internal_token = TokenService.generate_token(user)
                    logger.info(f"Internal token generated for user: {user.email}")
                    
                    # Builds the context with the user's credentials and token to pass to the login template
                    context = {
                        'google_client_id': settings.GOOGLE_CLIENT_ID,
                        'id_token': google_token, # Changed from internal tokens to google token. 
                                                  # This is a crucial part wherein the actual tokens required for the Postman test cannot be generated
                                                  # This is because the token generated on Google, which is a summary of the token (JWT) that we obtained from Google, should only appear after we enter what we copied from the Google token
                                                  # Usually the length of google token characters is 1,000 and above. And the internal token (JWT) is about 200 and above only.
                        'user_email': user.email,
                        'user_name': user.get_full_name()
                    }
                    return render(request, 'login.html', context)
                    
                # Failed to create user, return error to login page
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    context = {
                        'google_client_id': settings.GOOGLE_CLIENT_ID,
                        'error': 'Failed to create user account. Please try again.'
                    }
                    return render(request, 'login.html', context)
            else:
                # Invalid token, reject the login from the user
                logger.error("Token verification failed!")
                
                # Restricts access to users within the allowed domain only
                if settings.GOOGLE_ALLOWED_DOMAIN:
                    error_msg = f"Access denied. Only users with @{settings.GOOGLE_ALLOWED_DOMAIN} email addresses are allowed to sign in."
                else:
                    error_msg = "Invalid Google token. Unable to verify your Google account."
                
                context = {
                    'google_client_id': settings.GOOGLE_CLIENT_ID,
                    'error': error_msg,
                    'allowed_domain': settings.GOOGLE_ALLOWED_DOMAIN  # Passes the allowed domain to the template to display in the error message
                }
                return render(request, 'login.html', context)
        else:
            logger.warning("No token in POST data")
            # No token received, return the default login page
            logger.info("Showing default login page")
            context = {
                'google_client_id': settings.GOOGLE_CLIENT_ID
            }
            return render(request, 'login.html', context)
    
    # User arrived via URL, check if token is included
    elif request.method == 'GET':
        logger.info("Processing GET request to login_view")
        
        # Look for token in the URL as a fallback
        google_token = request.GET.get('id_token') or request.GET.get('credential')
        if google_token:
            logger.info(f"Token received via GET! Length: {len(google_token)}")
            
            # Verify the Google token and extract user claims
            auth_service = GoogleAuthService()
            claims = auth_service.verify_token(google_token)
            
            if claims and claims.get('email_verified'):
                user_service = UserService()
                try:
                    user, is_new = user_service.find_or_create_user(claims)
                    internal_token = TokenService.generate_token(user)
                    
                    context = {
                        'google_client_id': settings.GOOGLE_CLIENT_ID,
                        'id_token': google_token, # Changed from internal token (JWT) to Google token to ensure the process of consistency
                                                  # We changed also this to avoid confusion
                                                  # If we cannot replace this with the actual token that has already been generated as a Google token, it may cause confusion on the service side POST request and GET request where the token generation will not be correct
                                                  # An example of this is that there may be two options for token generation; it's either the Google token or our internal token (JWT) that will be generated after we sign in from Google.
                        'user_email': user.email,
                        'user_name': user.get_full_name()
                    }
                    return render(request, 'login.html', context)
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
            else:
                logger.error("Token verification failed via GET")
                
                # Show specific error if domain is restricted, otherwise show generic invalid token error
                if settings.GOOGLE_ALLOWED_DOMAIN:
                    error_msg = f"Access denied. Only users with @{settings.GOOGLE_ALLOWED_DOMAIN} email addresses are allowed to sign in."
                else:
                    error_msg = "Invalid Google token. Unable to verify your Google account."
                
                context = {
                    'google_client_id': settings.GOOGLE_CLIENT_ID,
                    'error': error_msg,
                    'allowed_domain': settings.GOOGLE_ALLOWED_DOMAIN
                }
                return render(request, 'login.html', context)
    
    # Default - show login page
    logger.info("Displaying default login page")
    context = {
        'google_client_id': settings.GOOGLE_CLIENT_ID
    }
    return render(request, 'login.html', context)

# This is usually for a user on getting a token request without a validation of CSRF (Cross-Site Request Forgery).
@csrf_exempt
def google_login(request):
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON. Please check your request body.'}, status=400)
        
        google_id_token = data.get('google_id_token')
        
        if not google_id_token:
            return JsonResponse(
                {'error': 'google_id_token is required in request body.'}, 
                status=400
            )
        
        auth_service = GoogleAuthService()
        claims = auth_service.verify_token(google_id_token)
        
        if not claims:
            # Show specific error if domain is restricted, otherwise it cannot generate a token
            if settings.GOOGLE_ALLOWED_DOMAIN:
                error_msg = f'Invalid Google token. Only users with @{settings.GOOGLE_ALLOWED_DOMAIN} email addresses are allowed.'
            else:
                error_msg = 'Invalid Google token. Token verification failed.'
            
            return JsonResponse(
                {'error': error_msg}, 
                status=401
            )
        
        # Reject if email is not verified by Google
        if not claims.get('email_verified'): # Change to false to force this error message. For example, if not false: syntax something like that
            return JsonResponse(
                {'error': 'Your Google account email address is not verified. Please verify your email address with Google and try again'}, 
                status=401
            )
        
        user_service = UserService()
        try:
            user, is_new = user_service.find_or_create_user(claims)

        # Email already exists in the database
        except IntegrityError as e:  
            logger.error(f"IntegrityError during user creation: {str(e)}")
            return JsonResponse(
                {'error': 'Account creation failed. Email address may already be in use.'},
                status=409
            )
        except DatabaseError as e:  
            logger.error(f"DatabaseError during user creation: {str(e)}")
            return JsonResponse(
                {'error': 'Account creation failed due to a database error. Please try again later.'},
                status=500
            )  
        except Exception as e:
            logger.error(f"Unexpected error during user creation: {str(e)}")
            return JsonResponse(
                {'error': 'Account creation failed. Please try again later.'},
                status=500  
            )   
       
        # Create an authentication token for the user after they successfully sign in.
        # This is the scenario; two tokens are given, one for making requests (access) and one for
        # getting a new token when the first one expires (refresh).
        internal_token = TokenService.generate_token(user)
        
        response_data = {
            'access_token': internal_token['access'],
            'refresh_token': internal_token['refresh'],
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name(),
                'auth_provider': user.auth_provider,
                'profile_picture': user.profile_picture,
                'is_new_user': is_new
            }
        }
        
        logger.info(f"Google login successful: {user.email} (New user: {is_new})")
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return JsonResponse(
            {'error': 'Internal server error. Please try again later.'}, 
            status=500
        )

# DEBUG ENDPOINT - Handles form data properly
@csrf_exempt
def debug_token(request):
    # Simple endpoint to see what Google sends
    print("\n" + "="*50)
    print("DEBUG ENDPOINT HIT!")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Body length: {len(request.body)}")
    print(f"Raw body: {request.body}")
    
    # Handle form-encoded data (this is what Google actually sends)
    if request.content_type == 'application/x-www-form-urlencoded':
        print("Processing form-encoded data")
        token = request.POST.get('credential')
        if token:
            print(f"Token found in form data! Length: {len(token)}")
            print(f"Token preview: {token[:100]}...")
            return JsonResponse({
                "status": "success", 
                "format": "form-data",
                "token_received": True,
                "token_length": len(token)
            })
        else:
            print(f"No credential field found. POST keys: {request.POST.keys()}")
            return JsonResponse({
                "status": "error", 
                "format": "form-data",
                "message": "No credential field",
                "keys": list(request.POST.keys())
            })
    
    # Try JSON parsing as fallback
    try:
        data = json.loads(request.body)
        print(f"Parsed JSON data: {data}")
        return JsonResponse({"status": "received", "format": "json", "data": data})
    except:
        # Just acknowledge receipt
        print("Could not parse as JSON, returning raw body")
        return JsonResponse({
            "status": "received", 
            "format": "raw",
            "body": str(request.body)
        })