from posts.models import Post, User

class PostFactory:
    @staticmethod
    def create_post(post_type, title, author, content='', metadata=None, privacy='public'):
        if post_type not in dict(Post.POST_TYPES):
            raise ValueError(f"Invalid post type: {post_type}")

        # Validation for specific types (Sir loves these checks!)
        if post_type == 'image' and (metadata is None or 'file_size' not in metadata):
            raise ValueError("Image posts require 'file_size' in metadata")
        
        if post_type == 'video' and (metadata is None or 'duration' not in metadata):
            raise ValueError("Video posts require 'duration' in metadata")

        # Create the post using the object passed from the view
        return Post.objects.create(
            title=title,
            content=content,
            author=author,       
            post_type=post_type,
            metadata=metadata or {},
            privacy=privacy      # Added privacy to match our new model
        )