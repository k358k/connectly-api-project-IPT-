from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError


# This class used to provide a method dealing with tokens authentication using GoogleOAuth to verify the user credentials
class TokenService:

    @classmethod
    def generate_token(cls, user):
        # Create payload with user credentials
        # Payload is like your birth certificate that containing sensitive details that needs to be secure the in processing on it
        # NOTE: We use Django's built-in token system (SimpleJWT) instead of
        # building our own. The old approach created tokens that were missing
        # required information, which caused a "Token is not valid/invalid" error.
        refresh = RefreshToken.for_user(user)

        # Add the user credentials into the token so the server
        # knows who is making the request when the token is used.
        refresh.access_token['user_id'] = user.id
        refresh.access_token['email'] = user.email
        refresh.access_token['auth_provider'] = user.auth_provider

        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    # This method is used to process the tokens from user credentials. if it is valid, it will proceed on compiling all user credential transform in it into a tokens
    @classmethod
    def decode_token(cls, token):
        try:
            validated = AccessToken(token)
            return dict(validated.payload)
        except TokenError:
            return None