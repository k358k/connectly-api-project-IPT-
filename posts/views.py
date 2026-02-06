from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User  # From instructions
from .models import Post, Comment
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .permissions import IsPostAuthor
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from factories.post_factory import PostFactory
from singletons.logger_singleton import LoggerSingleton

# Initialize the logger
logger = LoggerSingleton().get_logger()

# Create Users with Hashed Passwords ---
class UserListCreate(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        # We grab the data from the request
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "Username and password required"}, status=status.HTTP_400_BAD_REQUEST)

        # We create the user using Django's built-in method which automatically hashes the password
        user = User.objects.create_user(username=username, password=password)
        
        # For debugging:
        print(user.password) 

        return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

# --- Step 2.3: Verify Passwords During Login ---
from django.contrib.auth import authenticate # From instructions

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # Use the authenticate method to validate credentials
        user = authenticate(username=username, password=password)
        if user is not None:
            print("Authentication successful!") #
            return Response({"message": "Authenticated!"})
        else:
            print("Invalid credentials.") #
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

# This class handles getting all posts and creating a new one
class PostListCreate(APIView):
    authentication_classes = [TokenAuthentication] 
    permission_classes = [IsAuthenticated]          

    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            # IMPORTANT: Link the post to the logged-in user
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    
# new class for RBAC
class PostDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsPostAuthor] 

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            # This line triggers the IsPostAuthor check
            self.check_object_permissions(request, post)
            return Response({"content": post.content})
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)    
    
# New class using the PostFactory
class CreatePostView(APIView):
    def post(self, request):
        data = request.data
        try:
            # Use the Factory instead of Post.objects.create
            post = PostFactory.create_post(
                post_type=data.get('post_type'),
                author_id=data.get('author'),
                title=data.get('title'),
                content=data.get('content', ''),
                metadata=data.get('metadata', {})
            )
            logger.info(f"Post created successfully: {post.id}")
            return Response({'message': 'Post created successfully!', 'post_id': post.id}, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            logger.error(f"Post creation failed: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)