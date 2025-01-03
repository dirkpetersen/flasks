from typing import Any, Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

def parse_meta_fields() -> Dict[str, List[str]]:
    """Parse META_SEL and META_MSEL environment variables"""
    meta_fields = {}
    order_counter = 0
    for key, value in os.environ.items():
        if key.startswith(('META_SEL_', 'META_MSEL_')):
            if ':' in value:
                field_name, options = value.split(':', 1)
                field_id = field_name.lower().replace(' ', '_')
                meta_fields[field_id] = {
                    'name': field_name,
                    'options': [opt.strip() for opt in options.split(',')],
                    'multiple': key.startswith('META_MSEL_'),
                    'order': order_counter
                }
                order_counter += 1
    return meta_fields

class Config:
    """Application configuration class"""
    APP_NAME = os.getenv('APP_NAME', 'Work-ID')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-please-change')
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    JSON_SORT_KEYS = False
    JSON_AS_ASCII = False
        
    # Work ID Pattern
    WORK_ID_PATTERN = os.getenv('WORK_ID_PATTERN', 'XXXX-XXXX')
    
    # Email settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 25))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@localhost')
    
    # Meta fields
    META_FIELDS = parse_meta_fields()