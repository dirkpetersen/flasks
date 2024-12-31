#! /usr/bin/env python3

import os
import json
from typing import Optional, Tuple
from datetime import datetime
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

from .routes.records import records
from utils import parse_meta_fields
from database import redis_client

load_dotenv()

def create_app() -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(records)
    
    @app.route('/')
    def index():
        app_name = os.getenv('APP_NAME', 'Work-ID')
        meta_fields = parse_meta_fields()
        records = [json.loads(redis_client.get(key)) for key in redis_client.keys('record:*')]
        return render_template('index.html', 
                             app_name=app_name, 
                             meta_fields=meta_fields,
                             records=records)
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
        
    return app

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    def get_ssl_context() -> Optional[Tuple[str, str]]:
        ssl_cert = os.getenv('SSL_CERT')
        ssl_key = os.getenv('SSL_KEY')
        if ssl_cert and ssl_key:
            cert_path = os.path.expanduser(ssl_cert)
            key_path = os.path.expanduser(ssl_key)
            if os.path.exists(cert_path) and os.path.exists(key_path):
                return (cert_path, key_path)
            print(" * Warning: SSL certificate files specified but not found - starting without SSL")
        return None
    
    ssl_context = get_ssl_context()
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=debug_mode,
        ssl_context=ssl_context
    )

