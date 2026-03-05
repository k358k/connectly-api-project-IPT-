from django.db import models

# Create your models here.

# Defines what User is 
class User(models.Model):
    username = models.CharField(max_length=100, unique=True) 
    email = models.EmailField(unique=True) 
    created_at = models.DateTimeField(auto_now_add=True)  


    def __str__(self):
        return self.username

# Defines what Post is and assigns user who created the post
class Post(models.Model):
    content = models.TextField() 
    author = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE) 
    created_at = models.DateTimeField(auto_now_add=True) 


    def __str__(self):
        return f"Post by {self.author.username} at {self.created_at}"

# Defines what Comment is and assigns its author and parent post
class Comment(models.Model):
    text = models.TextField()
    author = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"

