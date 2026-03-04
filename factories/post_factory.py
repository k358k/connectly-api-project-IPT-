from posts.models import Post, User  # Added User import

class PostFactory:
    @staticmethod
    def create_post(post_type, title, author_id, content='', metadata=None): # Added author_id here
        if post_type not in dict(Post.POST_TYPES):
            raise ValueError("Invalid post type")

        # 1. Look up the author from the database
        try:
            author = User.objects.get(id=author_id)
        except User.DoesNotExist:
            raise ValueError("The provided Author ID does not exist.")

        # 2. Validation for specific types
        if post_type == 'image' and (metadata is None or 'file_size' not in metadata):
            raise ValueError("Image posts require 'file_size' in metadata")
        
        if post_type == 'video' and (metadata is None or 'duration' not in metadata):
            raise ValueError("Video posts require 'duration' in metadata")

        # 3. Create the post with the author included
        return Post.objects.create(
            title=title,
            content=content,
            author=author,       # <--- THIS WAS MISSING
            post_type=post_type,
            metadata=metadata or {}
        )