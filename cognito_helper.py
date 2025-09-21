# cognito_helper.py
import boto3
import hmac
import hashlib
import base64
import json
import logging
from botocore.exceptions import ClientError
from jose import jwt
import requests
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class CognitoHelper:
    def __init__(self):
        try:
            self.region = 'ap-southeast-2'
            self.user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
            self.client_id = os.environ.get('COGNITO_CLIENT_ID')
            self.client_secret = os.environ.get('COGNITO_CLIENT_SECRET')
            
            if not all([self.user_pool_id, self.client_id]):
                raise ValueError("Cognito configuration missing. Set COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID environment variables.")
            
            self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
            self.jwks_url = f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json'
            
            # Cache for JWKS
            self.jwks = None
            self.jwks_last_fetch = None
            
            logger.info("Cognito helper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Cognito helper: {e}")
            raise

    def _get_secret_hash(self, username):
        """Calculate secret hash for Cognito authentication"""
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8') if self.client_secret else b'',
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode()

    def _get_jwks(self):
        """Get JWKS with caching"""
        if self.jwks is None or (self.jwks_last_fetch and 
                                datetime.now() - self.jwks_last_fetch > timedelta(hours=1)):
            try:
                response = requests.get(self.jwks_url, timeout=10)
                response.raise_for_status()
                self.jwks = response.json()
                self.jwks_last_fetch = datetime.now()
                logger.info("JWKS fetched successfully")
            except Exception as e:
                logger.error(f"Failed to fetch JWKS: {e}")
                raise
        return self.jwks

    def sign_up(self, username, password, email):
        """Register a new user"""
        try:
            sign_up_params = {
                'ClientId': self.client_id,
                'Username': username,
                'Password': password,
                'UserAttributes': [
                    {
                        'Name': 'email',
                        'Value': email
                    }
                ]
            }
            
            # Add secret hash if client secret is configured
            if self.client_secret:
                sign_up_params['SecretHash'] = self._get_secret_hash(username)
            
            response = self.cognito_client.sign_up(**sign_up_params)
            
            logger.info(f"User {username} signed up successfully")
            return {
                'success': True,
                'user_sub': response['UserSub'],
                'code_delivery_details': response['CodeDeliveryDetails']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Sign up failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def confirm_sign_up(self, username, confirmation_code):
        """Confirm user registration with code from email"""
        try:
            confirm_params = {
                'ClientId': self.client_id,
                'Username': username,
                'ConfirmationCode': confirmation_code
            }
            
            # Add secret hash if client secret is configured
            if self.client_secret:
                confirm_params['SecretHash'] = self._get_secret_hash(username)
            
            self.cognito_client.confirm_sign_up(**confirm_params)
            
            logger.info(f"User {username} confirmed successfully")
            return {'success': True}
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Confirmation failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def authenticate(self, username, password):
        """Authenticate user and return JWT tokens"""
        try:
            auth_params = {
                'AuthFlow': 'USER_PASSWORD_AUTH',
                'ClientId': self.client_id,
                'AuthParameters': {
                    'USERNAME': username,
                    'PASSWORD': password
                }
            }
            
            # Add secret hash if client secret is configured
            if self.client_secret:
                auth_params['AuthParameters']['SECRET_HASH'] = self._get_secret_hash(username)
            
            response = self.cognito_client.initiate_auth(**auth_params)
            
            tokens = response['AuthenticationResult']
            
            logger.info(f"User {username} authenticated successfully")
            return {
                'success': True,
                'access_token': tokens['AccessToken'],
                'id_token': tokens['IdToken'],
                'refresh_token': tokens['RefreshToken'],
                'expires_in': tokens['ExpiresIn']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Authentication failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def verify_token(self, token):
        """Verify JWT token and return decoded claims"""
        try:
            # Get the JWKS
            jwks = self._get_jwks()
            
            # Get the header from the token
            headers = jwt.get_unverified_header(token)
            kid = headers['kid']
            
            # Find the key in the JWKS
            key = None
            for jwk_key in jwks['keys']:
                if jwk_key['kid'] == kid:
                    key = jwk_key
                    break
            
            if not key:
                raise Exception("Unable to find appropriate key")
            
            # Verify the token
            claims = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}'
            )
            
            logger.info(f"Token verified for user: {claims.get('cognito:username', claims.get('username'))}")
            return claims
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise

    def get_user_info(self, access_token):
        """Get user information using access token"""
        try:
            response = self.cognito_client.get_user(AccessToken=access_token)
            
            user_attributes = {}
            for attr in response['UserAttributes']:
                user_attributes[attr['Name']] = attr['Value']
            
            return {
                'username': response['Username'],
                'attributes': user_attributes
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to get user info: {error_code} - {error_message}")
            raise

    def admin_create_user(self, username, email, temporary_password):
        """Admin create user (for testing or admin purposes)"""
        try:
            response = self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                TemporaryPassword=temporary_password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                MessageAction='SUPPRESS'  # Don't send welcome email
            )
            
            logger.info(f"Admin created user {username}")
            return {'success': True, 'user': response['User']}
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Admin create user failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }
    
        
    def initiate_auth_with_mfa(self, username, password):
        """Authenticate user which may require MFA challenge"""
        try:
            auth_params = {
                'AuthFlow': 'USER_PASSWORD_AUTH',
                'ClientId': self.client_id,
                'AuthParameters': {
                    'USERNAME': username,
                    'PASSWORD': password
                }
            }
            
            if self.client_secret:
                auth_params['AuthParameters']['SECRET_HASH'] = self._get_secret_hash(username)
            
            response = self.cognito_client.initiate_auth(**auth_params)
            
            # If MFA challenge is required
            if response.get('ChallengeName') in ['SOFTWARE_TOKEN_MFA', 'MFA_SETUP']:
                return {
                    'success': True,
                    'challenge_required': True,
                    'challenge_name': response['ChallengeName'],
                    'session': response['Session']
                }
            else:
                # No MFA required, return tokens directly
                tokens = response['AuthenticationResult']
                return {
                    'success': True,
                    'challenge_required': False,
                    'tokens': tokens
                }
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Authentication failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }

    def respond_to_mfa_challenge(self, username, session, mfa_code):
        """Respond to MFA challenge"""
        try:
            response = self.cognito_client.respond_to_auth_challenge(
                ClientId=self.client_id,
                ChallengeName='SOFTWARE_TOKEN_MFA',
                Session=session,
                ChallengeResponses={
                    'USERNAME': username,
                    'SOFTWARE_TOKEN_MFA_CODE': mfa_code
                }
            )
            
            tokens = response['AuthenticationResult']
            return {
                'success': True,
                'tokens': tokens
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"MFA challenge failed: {error_code} - {error_message}")
            return {
                'success': False,
                'error_code': error_code,
                'error_message': error_message
            }