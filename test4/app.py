#!/usr/bin/env python3

from typing import Optional, Tuple
import os
import sys
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from redis.exceptions import ConnectionError
from .config import Config
from .database import RedisDB
from .blueprints.errors import errors_bp

def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)
    
    # Check Redis connectivity
    with app.app_context():
        try:
            redis_db = RedisDB()
            redis_db.client.ping()
        except ConnectionError as e:
            app.logger.error(f"Failed to connect to Redis: {e}")
            @app.route('/')
            def maintenance():
                return render_template('errors/maintenance.html'), 503
            return app

    # Register blueprints
    app.register_blueprint(errors_bp)
    from .blueprints.work_id import work_id_bp
    app.register_blueprint(work_id_bp)

    @app.errorhandler(Exception)
    def handle_error(error):
        app.logger.error(f"Unhandled error: {error}", exc_info=True)
        if hasattr(error, 'code') and error.code:
            return jsonify({'error': str(error)}), error.code
        return jsonify({'error': str(error)}), 500

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

