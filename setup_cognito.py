import boto3
import os
from cognito_helper import CognitoHelper

def setup_cognito_users():
    """Setup test users in Cognito for development"""
    cognito = CognitoHelper()
    
    # Test users to create
    test_users = [
        {
            'username': 'user1',
            'email': 'user1@example.com',
            'password': 'Password123!'
        },
        {
            'username': 'admin1', 
            'email': 'admin1@example.com',
            'password': 'Adminpass123!'
        }
    ]
    
    for user in test_users:
        try:
            print(f"Creating user: {user['username']}")
            
            # First try to sign up normally
            result = cognito.sign_up(user['username'], user['password'], user['email'])
            
            if result['success']:
                print(f"✓ User {user['username']} signed up successfully")
                print("  Please check email for confirmation code")
            else:
                print(f"✗ Sign up failed: {result.get('error_message')}")
                
        except Exception as e:
            print(f"Error creating user {user['username']}: {e}")

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ['COGNITO_USER_POOL_ID'] = 'your-user-pool-id'
    os.environ['COGNITO_CLIENT_ID'] = 'your-client-id'
    # os.environ['COGNITO_CLIENT_SECRET'] = 'your-client-secret'  # Optional
    
    setup_cognito_users()