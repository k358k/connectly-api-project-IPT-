from django.db import models

# This part defines what a "User" looks like in your database
class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

# This part defines what a "Post" looks like and links it to a User
class Post(models.Model):
    content = models.TextField()
    # Adding related_name='posts' helps the User model find its posts
    author = models.ForeignKey(User, related_name='posts', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This matches the specific format in your instructions
        return f"Post by {self.author.username} at {self.created_at}"

# This part defines what a "Comment" looks like and links it to both User and Post
class Comment(models.Model):
    text = models.TextField()
    # These related_names are crucial for the Serializers to work later
    author = models.ForeignKey(User, related_name='comments', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"
    
# This part defines what a "Like" looks like and links it to both User and Post   
class Like(models.Model):
    user = models.ForeignKey(User, related_name='likes', on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This ensures a user can only like a specific post once
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked Post {self.post.id}"