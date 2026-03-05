from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.db import IntegrityError, DatabaseError
from unittest.mock import patch, MagicMock
from posts.models import User, ExternalAuthProvider
from posts.services.google_auth import GoogleAuthService
from posts.services.token_service import TokenService
from posts.services.user_service import UserService
import json

# Tests for checking if GoogleAuthService works correctly
class GoogleAuthServiceTests(TestCase):
    
    def test_google_auth_service_initialization(self):
        # Check if GoogleAuthService starts up with a valid client ID
        service = GoogleAuthService()
        self.assertIsNotNone(service.client_id)
    
    @patch('posts.services.google_auth.id_token.verify_oauth2_token')
    def test_verify_token_valid(self, mock_verify):
        # Check if a valid token returns the correct user info
        # Fake a successful Google token response
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'email_verified': True
        }
        
        service = GoogleAuthService()
        result = service.verify_token('valid_token')
        
        # Make sure we got a result back and it is not empty
        self.assertIsNotNone(result)
        # Make sure the Google user ID matches what we expect
        self.assertEqual(result['google_id'], '123456789')
        # Make sure the email address matches what we expect
        self.assertEqual(result['email'], 'test@mmdc.mcl.edu.ph')
        # Make sure the name matches what we expect
        self.assertEqual(result['name'], 'Test User')
        # Make sure the email is marked as verified
        self.assertTrue(result['email_verified'])
    
    @patch('posts.services.google_auth.id_token.verify_oauth2_token')
    def test_verify_token_invalid(self, mock_verify):
        # Check if an invalid token returns nothing
        # Pretend Google throws an error when checking the token
        mock_verify.side_effect = ValueError('Invalid token')
        
        service = GoogleAuthService()
        result = service.verify_token('invalid_token')
        
        # The result should be empty since the token was bad
        self.assertIsNone(result)

    # NEW TESTS FOR DOMAIN RESTRICTION 
    @patch('posts.services.google_auth.id_token.verify_oauth2_token')
    def test_verify_token_blocked_domain(self, mock_verify):
        # Check that a token from a non-institution email address (like gmail.com) is rejected
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'test@gmail.com',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'email_verified': True
        }
        service = GoogleAuthService()
        # Only allow school emails
        service.allowed_domain = 'mmdc.mcl.edu.ph'
        result = service.verify_token('valid_token')
        # Should be blocked since the email is not from the allowed school domain
        self.assertIsNone(result)

    @patch('posts.services.google_auth.id_token.verify_oauth2_token')
    def test_verify_token_unverified_email(self, mock_verify):
        # Check that a token with an unconfirmed email still comes back, but shows it is not confirmed
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'email_verified': False
        }
        service = GoogleAuthService()
        service.allowed_domain = 'mmdc.mcl.edu.ph'
        result = service.verify_token('valid_token')
        # We should still get a result back
        self.assertIsNotNone(result)
        # But the email confirmed flag should be set to false
        self.assertFalse(result['email_verified'])


# Tests for checking if TokenService works correctly
class TokenServiceTests(TestCase):
    
    def setUp(self):
        # Create a test user to use in token tests
        self.user = User.objects.create_user(
            username='test@mmdc.mcl.edu.ph',
            email='test@mmdc.mcl.edu.ph',
            first_name='Test',
            last_name='User',
            password='testpass123',
            auth_provider='google',
            google_id='123456789'
        )
    
    def test_generate_token(self):
        # Check if login passes (tokens) are successfully created for a user
        # The method now returns a dict with access and refresh tokens
        tokens = TokenService.generate_token(self.user)
        
        # The result should be a dictionary
        self.assertIsInstance(tokens, dict)
        # It should contain access_token and refresh_token keys
        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        # Both should be non-empty strings
        self.assertTrue(len(tokens['access_token']) > 0)
        self.assertTrue(len(tokens['refresh_token']) > 0)
    
    def test_decode_token(self):
        # Check if a login pass (token) can be read back and contains the right user info
        tokens = TokenService.generate_token(self.user)
        payload = TokenService.decode_token(tokens['access_token'])
        
        # The decoded info should not be empty
        self.assertIsNotNone(payload)
        # The user ID inside the token should match our test user
        self.assertEqual(payload['user_id'], self.user.id)
        # The email inside the token should match our test user
        self.assertEqual(payload['email'], self.user.email)
        # The login method inside the token should say 'google'
        self.assertEqual(payload['auth_provider'], 'google')
    
    def test_decode_token_invalid(self):
        # Check if trying to read a fake or broken token returns nothing
        result = TokenService.decode_token('invalid_token')
        
        # Should be empty since the token is not real
        self.assertIsNone(result)


# Tests for checking if the login page works correctly
class LoginViewTests(TestCase):
    
    def setUp(self):
        # Set up a test browser and the web address for the login page
        self.client = Client()
        self.login_url = reverse('login')
    
    def test_login_view_get(self):
        # Check if visiting the login page works and loads correctly
        response = self.client.get(self.login_url)
        
        # The page should load successfully (status 200 means OK)
        self.assertEqual(response.status_code, 200)
        # The page should use the login template
        self.assertTemplateUsed(response, 'login.html')
        # The page should include the Google sign-in button info
        self.assertIn('google_client_id', response.context)
    
    def test_login_view_post_no_token(self):
        # Check if submitting the login form without a Google pass still loads the page
        response = self.client.post(self.login_url)
        
        # Should return login page with error or show default page
        self.assertEqual(response.status_code, 200)
    
    @patch('posts.views.GoogleAuthService.verify_token')
    @patch('posts.views.UserService.find_or_create_user')
    @patch('posts.views.TokenService.generate_token')
    def test_login_view_post_valid_token(self, mock_generate, mock_find_user, mock_verify):
        # Check if a valid Google sign-in pass logs the user in successfully
        # Set up fake responses so we do not need real Google servers
        mock_verify.return_value = {
            'sub': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'picture': 'https://example.com/pic.jpg',
            'email_verified': True
        }
        
        mock_user = User.objects.create_user(
            username='test@mmdc.mcl.edu.ph',
            email='test@mmdc.mcl.edu.ph',
            first_name='Test',
            last_name='User',
            password='testpass123',
            auth_provider='google',
            google_id='123456789'
        )
        
        mock_find_user.return_value = (mock_user, True)
        # generate_token now returns a dict, not a string
        mock_generate.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token'
        }
        
        # Send login request with a fake Google pass
        response = self.client.post(
            self.login_url,
            data={'credential': 'google_token_123'},
            content_type='application/x-www-form-urlencoded'
        )
        
        # The page should load successfully
        self.assertEqual(response.status_code, 200)
        # The page should have an internal login pass ready to use
        self.assertIn('id_token', response.context)

    # NEW TEST: Verify that the raw Google token is passed to the template 
    @patch('posts.views.GoogleAuthService.verify_token')
    @patch('posts.views.UserService.find_or_create_user')
    @patch('posts.views.TokenService.generate_token')
    def test_login_view_displays_raw_google_token(self, mock_generate, mock_find_user, mock_verify):
        # Check that after a successful login, the page receives the original Google token authentication and not our internal token
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'email_verified': True
        }
        mock_user = User.objects.create_user(
            username='test@mmdc.mcl.edu.ph',
            email='test@mmdc.mcl.edu.ph',
            auth_provider='google',
            google_id='123456789'
        )
        mock_find_user.return_value = (mock_user, False)
        # This is our internal token pass but it should not show up in after we sign-in the login page
        mock_generate.return_value = {
            'access_token': 'dummy_access_token',
            'refresh_token': 'dummy_refresh_token'
        }

        response = self.client.post(
            self.login_url,
            data={'credential': 'raw_google_token_123'},
            content_type='application/x-www-form-urlencoded'
        )
        # The page should load successfully
        self.assertEqual(response.status_code, 200)
        # The page should show the original Google pass, not our internal one
        self.assertEqual(response.context['id_token'], 'raw_google_token_123')

    @patch('posts.views.GoogleAuthService.verify_token')
    def test_login_view_post_invalid_token(self, mock_verify):
        # Check if a bad or fake Google pass shows an error on the login page
        # Pretend the token check came back empty
        mock_verify.return_value = None
        
        response = self.client.post(
            self.login_url,
            data={'credential': 'invalid_token'},
            content_type='application/x-www-form-urlencoded'
        )
        
        # The page should still load
        self.assertEqual(response.status_code, 200)
        # The page should show an error message to the user
        self.assertIn('error', response.context)


# Tests for checking if UserService works correctly
class UserServiceTests(TestCase):
    
    def test_user_service_initialization(self):
        # Check if UserService starts up without issues
        service = UserService()
        self.assertIsNotNone(service)
    
    def test_find_or_create_user_new(self):
        # Check if a brand new user account is created correctly using their Google info
        service = UserService()
        
        user, is_new = service.find_or_create_user({
            'google_id': 'new_google_id_123',
            'email': 'newuser@mmdc.mcl.edu.ph',
            'name': 'New User',
            'picture': 'https://example.com/newpic.jpg'
        })
        
        # This should be a new account
        self.assertTrue(is_new)
        # The email should match what we passed in
        self.assertEqual(user.email, 'newuser@mmdc.mcl.edu.ph')
        # The sign-in method should be set to Google
        self.assertEqual(user.auth_provider, 'google')

    # NEW TESTS FOR USER LOOKUP AND LINKING 
    def test_find_existing_user_by_google_id(self):
        # Check that if a user has already signed in with Google before, we find them instead of making a new account
        service = UserService()
        # Create a user and their saved Google connection
        user = User.objects.create_user(
            username='existing@mmdc.mcl.edu.ph',
            email='existing@mmdc.mcl.edu.ph',
            first_name='Existing',
            last_name='User',
            password='testpass123',
            auth_provider='google',
            google_id='existing_google_id'
        )
        ExternalAuthProvider.objects.create(
            user=user,
            provider='google',
            provider_user_id='existing_google_id'
        )
        claims = {
            'google_id': 'existing_google_id',
            'email': 'someother@mmdc.mcl.edu.ph',  # different email
            'name': 'Existing User',
            'picture': ''
        }
        found_user, is_new = service.find_or_create_user(claims)
        # Should not be marked as new since the user already exists
        self.assertFalse(is_new)
        # Should return the same user we created earlier
        self.assertEqual(found_user.id, user.id)
        # Their email should remain unchanged
        self.assertEqual(found_user.email, 'existing@mmdc.mcl.edu.ph')

    def test_link_existing_user_by_email(self):
        # Check that if a user already has a local account, their Google account gets connected to it
        service = UserService()
        existing_user = User.objects.create_user(
            username='local@mmdc.mcl.edu.ph',
            email='local@mmdc.mcl.edu.ph',
            first_name='Local',
            last_name='User',
            password='testpass123',
            auth_provider='local',
            google_id=None
        )
        claims = {
            'google_id': 'new_google_id_456',
            'email': 'local@mmdc.mcl.edu.ph',
            'name': 'Local User',
            'picture': 'https://example.com/pic.jpg'
        }
        linked_user, is_new = service.find_or_create_user(claims)
        # Should not be a new account since the email already existed
        self.assertFalse(is_new)
        # Should return the same user we created earlier
        self.assertEqual(linked_user.id, existing_user.id)
        # Their Google ID should now be saved
        self.assertEqual(linked_user.google_id, 'new_google_id_456')
        # Their login method should now be updated to Google
        self.assertEqual(linked_user.auth_provider, 'google')
        # A Google connection record should now exist for this user
        self.assertTrue(
            ExternalAuthProvider.objects.filter(
                provider='google',
                provider_user_id='new_google_id_456'
            ).exists()
        )


# NEW TEST SUITE FOR EXTERNAL AUTH PROVIDER MODEL 
class ExternalAuthProviderTests(TestCase):
    # Tests for the saved Google provider/with other external provider for the sign-in connection to our server including the rules and display name

    def setUp(self):
        # Create a basic test user to attach connections to
        self.user = User.objects.create_user(
            username='test@mmdc.mcl.edu.ph',
            email='test@mmdc.mcl.edu.ph',
            password='testpass123'
        )

    def test_create_external_auth_provider(self):
        # Check that saving a new Google connection for a user works correctly
        auth = ExternalAuthProvider.objects.create(
            user=self.user,
            provider='google',
            provider_user_id='google_id_123',
            id_token='test_id_token'
        )
        # The connection should belong to our test user
        self.assertEqual(auth.user, self.user)
        # The provider name should be 'google'
        self.assertEqual(auth.provider, 'google')
        # The Google user ID should match what we saved
        self.assertEqual(auth.provider_user_id, 'google_id_123')
        # The Google pass (token) should match what we saved
        self.assertEqual(auth.id_token, 'test_id_token')
        # The date the connection was made should be recorded
        self.assertIsNotNone(auth.created_at)

    def test_unique_together_constraint(self):
        # Check that you cannot save the same Google account connection twice for the same user
        ExternalAuthProvider.objects.create(
            user=self.user,
            provider='google',
            provider_user_id='google_id_123'
        )
        # Trying to save the same connection again should cause an error
        with self.assertRaises(IntegrityError):
            ExternalAuthProvider.objects.create(
                user=self.user,
                provider='google',
                provider_user_id='google_id_123'
            )

    def test_user_can_have_multiple_providers(self):
        # Check that a individual user can connect more than one External provider to sign-in (both Google and Facebook)
        ExternalAuthProvider.objects.create(
            user=self.user,
            provider='google',
            provider_user_id='google_id_123'
        )
        ExternalAuthProvider.objects.create(
            user=self.user,
            provider='facebook',
            provider_user_id='fb_id_456'
        )
        # The user should now have two saved connections
        self.assertEqual(self.user.external_auths.count(), 2)

    def test_string_representation(self):
        # Check that when you print this connection, it shows the user's email and provider name
        auth = ExternalAuthProvider.objects.create(
            user=self.user,
            provider='google',
            provider_user_id='google_id_123'
        )
        expected = f"{self.user.email} - google"
        self.assertEqual(str(auth), expected)


# NEW TEST SUITE FOR GOOGLE LOGIN API ENDPOINT 
class GoogleLoginAPITests(TestCase):
    # Tests for the Google login endpoint including handling sign-in requests and errors
    def setUp(self):
        # Set up a test browser and the web address for the Google login endpoint
        self.client = Client()
        self.api_url = reverse('google_login')

    @patch('posts.views.GoogleAuthService.verify_token')
    @patch('posts.views.UserService.find_or_create_user')
    @patch('posts.views.TokenService.generate_token')
    def test_google_login_success(self, mock_generate, mock_find_user, mock_verify):
        # Check that a valid Google pass returns a successful response with a login pass and user details
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'email_verified': True
        }
        mock_user = User.objects.create_user(
            username='test@mmdc.mcl.edu.ph',
            email='test@mmdc.mcl.edu.ph',
            auth_provider='google',
            google_id='123456789'
        )
        mock_find_user.return_value = (mock_user, False)
        # generate_token now returns a dict with access and refresh tokens
        mock_generate.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token'
        }

        response = self.client.post(
            self.api_url,
            data=json.dumps({'google_id_token': 'valid_token'}),
            content_type='application/json'
        )
        # Should get a success response
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # The response should include access_token and refresh_token
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertEqual(data['access_token'], 'test_access_token')
        self.assertEqual(data['refresh_token'], 'test_refresh_token')
        # The response should include the user's account details
        self.assertEqual(data['user']['id'], mock_user.id)

    def test_google_login_wrong_method(self):
        # Check that visiting the login endpoint the wrong way (GET instead of POST) is rejected
        response = self.client.get(self.api_url)
        # Should get a "method not allowed" response (405)
        self.assertEqual(response.status_code, 405)

    def test_google_login_missing_token(self):
        # Check that sending a login request without a Google pass returns an error
        response = self.client.post(
            self.api_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        # Should get a "bad request" response (400)
        self.assertEqual(response.status_code, 400)

    def test_google_login_invalid_json(self):
        # Check that sending broken or unreadable data returns an error
        response = self.client.post(
            self.api_url,
            data='not json',
            content_type='application/json'
        )
        # Should get a "bad request" response (400)
        self.assertEqual(response.status_code, 400)

    @patch('posts.views.GoogleAuthService.verify_token')
    def test_google_login_invalid_token(self, mock_verify):
        # Check that a fake or expired Google pass is rejected with a intitution domain message
        mock_verify.return_value = None
        with self.settings(GOOGLE_ALLOWED_DOMAIN='mmdc.mcl.edu.ph'):
            response = self.client.post(
                self.api_url,
                data=json.dumps({'google_id_token': 'invalid'}),
                content_type='application/json'
            )
        # Should get an "unauthorized" response (401)
        self.assertEqual(response.status_code, 401)
        data = response.json()
        # The error message should mention the allowed institution domain
        self.assertIn('mmdc.mcl.edu.ph', data['error'])

    @patch('posts.views.GoogleAuthService.verify_token')
    def test_google_login_unverified_email(self, mock_verify):
        # Check that a Google pass with an unconfirmed email address is rejected
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'email_verified': False
        }
        response = self.client.post(
            self.api_url,
            data=json.dumps({'google_id_token': 'valid_token'}),
            content_type='application/json'
        )
        # Should get an "unauthorized" response (401)
        self.assertEqual(response.status_code, 401)
        # The error message should say the email is not verified
        self.assertIn('not verified', response.json()['error'])

    @patch('posts.views.GoogleAuthService.verify_token')
    @patch('posts.views.UserService.find_or_create_user')
    def test_google_login_integrity_error(self, mock_find_user, mock_verify):
        # Check that if two accounts try to use the same info at the same time, we get a "conflict" error
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'email_verified': True
        }
        # Pretend a duplicate account conflict happened during saving
        mock_find_user.side_effect = IntegrityError('duplicate')
        response = self.client.post(
            self.api_url,
            data=json.dumps({'google_id_token': 'valid_token'}),
            content_type='application/json'
        )
        # Should get a "conflict" response (409)
        self.assertEqual(response.status_code, 409)
        # The error message should say the info is already being used
        self.assertIn('already in use', response.json()['error'])

    # NEW TEST FOR DATABASE ERROR (500)
    @patch('posts.views.GoogleAuthService.verify_token')
    @patch('posts.views.UserService.find_or_create_user')
    def test_google_login_database_error(self, mock_find_user, mock_verify):
        # Check that a database error during user creation returns a 500 error with appropriate message
        mock_verify.return_value = {
            'google_id': '123456789',
            'email': 'test@mmdc.mcl.edu.ph',
            'name': 'Test User',
            'email_verified': True
        }
        # Simulate a database error
        mock_find_user.side_effect = DatabaseError('database connection failed')
        response = self.client.post(
            self.api_url,
            data=json.dumps({'google_id_token': 'valid_token'}),
            content_type='application/json'
        )
        # Should get an "internal server error" response (500)
        self.assertEqual(response.status_code, 500)
        # The error message should mention a database error
        self.assertIn('database error', response.json()['error'].lower())