"""
WSGI config for connectly_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from dotenv import load_dotenv

# Load .env file for the implementation of google-auth as well
load_dotenv()

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'connectly_project.settings')

application = get_wsgi_application()
