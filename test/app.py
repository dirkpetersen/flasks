#! /usr/bin/env python3

import os
import json
from typing import Optional, Tuple
from datetime import datetime
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv

from routes.records import records
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

@app.route('/')
def index():
    app_name = os.getenv('APP_NAME', 'Work-ID')
    meta_fields = parse_meta_fields()
    records = [json.loads(redis_client.get(key)) for key in redis_client.keys('record:*')]
    return render_template('index.html', 
                         app_name=app_name, 
                         meta_fields=meta_fields,
                         records=records)

@app.route('/save_record', methods=['POST'])
def save_record():
    data = request.form.to_dict(flat=False)
    record_id = data.get('record_id', [None])[0]
    
    if not record_id:
        record_id = str(uuid.uuid4())
    
    redis_key = f"record:{record_id}"
    
    # Convert single items from lists to single values
    processed_data = {}
    meta_fields = parse_meta_fields()
    
    for field_id, field_info in meta_fields.items():
        if field_id in data:
            if field_info['multiple']:
                processed_data[field_id] = data[field_id]
            else:
                processed_data[field_id] = data[field_id][0]
    
    # Add basic fields
    processed_data['name'] = data['name'][0]
    processed_data['_id'] = record_id
    
    # Only set created_at for new records
    existing_record = redis_client.get(redis_key)
    if existing_record:
        existing_data = json.loads(existing_record)
        processed_data['created_at'] = existing_data['created_at']
    else:
        processed_data['created_at'] = datetime.now().isoformat()
    
    redis_client.set(redis_key, json.dumps(processed_data))
    return redirect(url_for('index'))

@app.route('/get_record/<record_id>')
def get_record(record_id):
    key = f"record:{record_id}"
    print(f"Fetching record with key: {key}")
    record = redis_client.get(key)
    if record:
        print(f"Found record: {record}")
        return jsonify(json.loads(record))
    print(f"Record not found for key: {key}")
    return jsonify({"error": "Record not found"}), 404

@app.route('/delete/<record_id>')
def delete_record(record_id):
    redis_client.delete(f"record:{record_id}")
    return redirect(url_for('index'))

if __name__ == '__main__':
    ssl_cert = os.getenv('SSL_CERT')
    ssl_key = os.getenv('SSL_KEY')    
    ssl_context = None
    if ssl_cert and ssl_key:
        if os.path.exists(os.path.expanduser(ssl_cert)) and os.path.exists(os.path.expanduser(ssl_key)):
            ssl_context = (os.path.expanduser(ssl_cert), os.path.expanduser(ssl_key))
            print(f" * Starting with SSL using cert: {ssl_cert}")
        else:
            print(" * Warning: SSL certificate files specified but not found - starting without SSL")
            if not os.path.exists(os.path.expanduser(ssl_cert)):
                print(f"     Missing certificate file: {ssl_cert}")
            if not os.path.exists(os.path.expanduser(ssl_key)):
                print(f"     Missing key file: {ssl_key}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=debug_mode,
        ssl_context=ssl_context
    )
