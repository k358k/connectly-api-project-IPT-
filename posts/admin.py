from django.contrib import admin
from .models import User, Post, Like, Comment, ExternalAuthProvider

admin.site.register(User)
admin.site.register(Post)
admin.site.register(Like)
admin.site.register(Comment)
admin.site.register(ExternalAuthProvider)