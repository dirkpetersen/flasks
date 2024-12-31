from typing import Any, Dict
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration class"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False