from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings
import logging

# This helps to track the login process of the user using GoogleAuth, allowing us to see any errors that occur and ensure the system is correctly verifying users
logger = logging.getLogger(__name__)

# This class handles Google OAuth token verification and domain restriction for user authentication
class GoogleAuthService:
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        # To set the allowed domain which is set from .env file (sensitive details)
        self.allowed_domain = getattr(settings, 'GOOGLE_ALLOWED_DOMAIN', None)
    
    def verify_token(self, google_id_token):
        try:
            id_info = id_token.verify_oauth2_token(
                google_id_token, 
                requests.Request(), 
                self.client_id
            )
            
            # Extracts and structures the user's profile data from the verified token claims
            claims = {
                'google_id': id_info['sub'],
                'email': id_info['email'],
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'email_verified': id_info.get('email_verified', False),
                'hd': id_info.get('hd', '')  # To know which domain is set for users.
            }

            # If not allowed. return None and prevent proceeding to the next page
            if not self._check_domain_allowed(claims):
                logger.warning(f"Domain not allowed: {claims.get('email')}")
                return None
            
            return claims
            
        except ValueError as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None
        

    # This is a way to verify the user email addresses if this is a scope of the set domain or not
    def _check_domain_allowed(self, claims):
        if not self.allowed_domain:
            return True
        
        email = claims.get('email', '')
        hd = claims.get('hd', '')  # Institution domain from Google
        
        # Verifying the user email addresses 
        if '@' in email:
            email_domain = email.split('@')[1]
        else:
            email_domain = ''
        
        # Comparing the user email addresses and the domain set if it is in the scope
        if email_domain == self.allowed_domain or hd == self.allowed_domain:
            return True
        
        # If not after tracking the user claims. It will not proceed to next page of the login
        logger.warning(f"Domain check failed: email_domain={email_domain}, hd={hd}, allowed={self.allowed_domain}")
        return False
