import boto3
from botocore.exceptions import ClientError
from email_validator import validate_email, EmailNotValidError
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, url_for
import json
from typing import Optional, Tuple
from .database import RedisDB

def validate_email_address(email: str) -> Tuple[bool, Optional[str]]:
    """Validate email format"""
    try:
        validation = validate_email(email, check_deliverability=True)
        return True, validation.normalized
    except EmailNotValidError as e:
        return False, str(e)

def generate_token(email: str) -> str:
    """Generate a secure token for email verification"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verification')

def verify_token(token: str, expiration=3600) -> Optional[str]:
    """Verify the email verification token"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verification', max_age=expiration)
        return email
    except:
        return None

def send_verification_email(email: str, token: str) -> bool:
    """Send verification email using AWS SES"""
    verify_url = url_for('work_id.verify_email_token', 
                        token=token, 
                        _external=True)
    
    # Create SES client with specified AWS profile
    session = boto3.Session(profile_name=current_app.config['AWS_PROFILE'])
    ses = session.client('ses')
    
    try:
        response = ses.send_email(
            Source=current_app.config['MAIL_DEFAULT_SENDER'],
            Destination={
                'ToAddresses': [email]
            },
            Message={
                'Subject': {
                    'Data': f'Verify your email for {current_app.config["APP_NAME"]}'
                },
                'Body': {
                    'Html': {
                        'Data': f'''
                            <h2>Email Verification</h2>
                            <p>Please click the link below to verify your email for {current_app.config["APP_NAME"]}:</p>
                            <p><a href="{verify_url}">{verify_url}</a></p>
                            <p>This link will expire in 1 hour.</p>
                        '''
                    }
                }
            }
        )
        return True
    except ClientError as e:
        current_app.logger.error(f"Failed to send email: {e.response['Error']['Message']}")
        return False

def store_identity(email: str, verified: bool = False) -> bool:
    """Store identity information in Redis"""
    try:
        db = RedisDB()
        identity_data = {
            'email': email,
            'verified': verified
        }
        return db.client.json().set(f'identity:{email}', '$', identity_data)
    except Exception as e:
        current_app.logger.error(f"Failed to store identity: {e}")
        return False

def get_identity(email: str) -> Optional[dict]:
    """Retrieve identity information from Redis"""
    try:
        db = RedisDB()
        data = db.client.json().get(f'identity:{email}')
        return data[0] if isinstance(data, list) else data
    except Exception as e:
        current_app.logger.error(f"Failed to get identity: {e}")
        return None
