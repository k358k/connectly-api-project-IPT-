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

        # ── HW8 ADDED: Encode role into the token payload ─────────────────────
        # Before HW8, the token only carried the user id, email, and auth
        # provider. It had no information about what role the user had. This
        # was fine before because there were no roles in the system yet. Now
        # that we have roles, every permission class needs to know the role of
        # the user who sent the request in order to decide whether to allow or
        # block that request.
        
        # Why we put the role inside the token instead of looking it up:
        #   Every time a user sends a request to the API, the permission class
        #   runs and needs to check the role. If the role were not stored in
        #   the token, Django would have to go to the database on every single
        #   request just to find out what role that user has. For an application
        #   with many users sending many requests this would slow things down
        #   significantly. By storing the role inside the token when it is first
        #   created, the permission class can read it instantly without ever
        #   needing to touch the database. This makes the application faster
        #   and more efficient.
        
        # What the token payload looks like after this line is added:
        #   user_id, email, auth_provider, and role which will be one of
        #   admin, user, or guest depending on what role that user has.
        refresh.access_token['role'] = user.role
        # ── END HW8 ADDED ─────────────────────────────────────────────────────

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