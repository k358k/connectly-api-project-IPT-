from posts.models import User, ExternalAuthProvider
from django.db import transaction
# add this for temporary testing the database error in our view.py for the line 297: from django.db import IntegrityError 
import logging

logger = logging.getLogger(__name__)

# This is used to manage a user accounts, linking them with external authentication providers like Google OAuth
class UserService:
    
    def find_or_create_user(self, google_claims):
        # Add this syntax for testing the database error: raise IntegrityError("Forced duplicate for testing")
        google_id = google_claims['google_id']
        email = google_claims['email']
        
        # Using this method to attempts in find an existing user based on Google claims. If no user is found, it creates a new user and links it to the Google account
        with transaction.atomic():
            external_auth = ExternalAuthProvider.objects.filter(
                provider='google',
                provider_user_id=google_id
            ).select_related('user').first()
            
            if external_auth:
                logger.info(f"User found via external auth: {external_auth.user.id}")
                return external_auth.user, False
            
            user = User.objects.filter(email=email).first()
            if user:
                user.google_id = google_id
                user.auth_provider = 'google'
                user.profile_picture = google_claims.get('picture', '')
                user.save()
                
                ExternalAuthProvider.objects.create(
                    user=user,
                    provider='google',
                    provider_user_id=google_id,
                    id_token=google_claims.get('id_token', '')
                )
                logger.info(f"Linked Google account to existing user: {user.id}")
                return user, False
            
            return self._create_new_user(google_claims), True
    
    # This is to create new user credentials based on the policy of GoogleOAuth
    def _create_new_user(self, google_claims):
        email = google_claims['email']
        full_name = google_claims.get('name', '')
        name_parts = full_name.split()
        

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name_parts[0] if name_parts else '',
            last_name=' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
            password=None,
            google_id=google_claims['google_id'],
            auth_provider='google',
            profile_picture=google_claims.get('picture', '')
        )

        # Creating a track-record using ExternalAuthProvider to connect a new user account with their Google OAuth credentials
        ExternalAuthProvider.objects.create(
            user=user,
            provider='google',
            provider_user_id=google_claims['google_id'],
            id_token=google_claims.get('id_token', '')
        )
        
        logger.info(f"Created new user from Google: {user.id}")
        return user