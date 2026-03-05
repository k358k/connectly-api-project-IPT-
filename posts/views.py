<<<<<<< HEAD
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .models import Post
from .models import Comment
from .serializers import UserSerializer, PostSerializer, CommentSerializer

# Defines and validates User creation and retrieval
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


# Defines and validates Post creation and retrieval
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


# Defines and validates Comment creation and retrieval
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
=======
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import Post, Comment
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .permissions import IsPostAuthor
from django.contrib.auth import authenticate 

# --- User Management with Hashing ---
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

        # create_user automatically hashes the password
        user = User.objects.create_user(username=username, password=password)
        return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)

# --- Login & Credential Verification ---
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            return Response({"message": "Authenticated!"})
        else:
            return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

# --- Protected Post Management (Token Auth) ---
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
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- Original Comment Management ---
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

# --- Role-Based Access Control (RBAC) ---
class PostDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsPostAuthor]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            self.check_object_permissions(request, post)
            return Response({"content": post.content})
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)






    



>>>>>>> origin/Ricohermozo_Security
