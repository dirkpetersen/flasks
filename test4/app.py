#!/usr/bin/env python3

from typing import Optional, Tuple
import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from .config import Config
from .blueprints.errors import errors_bp

def create_app(config_class: type = Config) -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)

    # Register blueprints
    app.register_blueprint(errors_bp)

    # Register main routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/meta-fields')
    def get_meta_fields():
        return jsonify(app.config.get('META_FIELDS', {}))

    @app.route('/api/new-id')
    def get_new_id():
        from test4.database import RedisDB
        db = RedisDB()
        try:
            new_id = db.generate_work_id()
            return jsonify({'id': new_id})
        except Exception as e:
            app.logger.error(f"Error generating new ID: {e}")
            return jsonify({'error': 'Failed to generate ID'}), 500

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

