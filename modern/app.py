#!/usr/bin/env python3

from typing import Optional, Tuple
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

from .redis_store import init_redis
from .routes.contacts import contacts_bp
from .routes.errors import errors_bp
from .config import Config

load_dotenv()

def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app)
    
    # Initialize Redis before registering blueprints
    redis_client = init_redis(app)
    if not redis_client:
        app.logger.error("Failed to initialize Redis connection")
        raise RuntimeError("Failed to initialize Redis connection. Please check Redis server is running and configuration is correct.")
    
    # Register blueprints
    app.register_blueprint(contacts_bp)
    app.register_blueprint(errors_bp)
    
    return app

def get_ssl_context() -> Optional[Tuple[str, str]]:
    """Get SSL context if certificates are configured"""
    ssl_cert = os.getenv('SSL_CERT')
    ssl_key = os.getenv('SSL_KEY')
    if ssl_cert and ssl_key:
        cert_path = os.path.expanduser(ssl_cert)
        key_path = os.path.expanduser(ssl_key)
        if os.path.exists(cert_path) and os.path.exists(key_path):
            return (cert_path, key_path)
        print(" * Warning: SSL certificate files specified but not found - starting without SSL")
    return None

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ssl_context = get_ssl_context()
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=debug_mode,
        ssl_context=ssl_context
    )

