import os
from datetime import timedelta

class Config:
    """Application configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
