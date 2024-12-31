#! /usr/bin/env python3

import sys, os, json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import redis
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Redis connection
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

def parse_meta_fields():
    """Parse META_SEL and META_MSEL environment variables"""
    meta_fields = {}
    for key, value in os.environ.items():
        if key.startswith(('META_SEL_', 'META_MSEL_')):
            field_name, options = value.split(':', 1)
            field_id = field_name.lower().replace(' ', '_')
            meta_fields[field_id] = {
                'name': field_name,
                'options': options.split(','),
                'multiple': key.startswith('META_MSEL_'),
                'id': field_id
            }
    return meta_fields

@app.route('/')
def index():
    app_name = os.getenv('APP_NAME', 'Work-ID')
    meta_fields = parse_meta_fields()
    records = [json.loads(redis_client.get(key)) for key in redis_client.keys('record:*')]
    return render_template('index.html', 
                         app_name=app_name, 
                         meta_fields=meta_fields,
                         records=records)

@app.route('/create', methods=['POST'])
def create_record():
    data = request.form.to_dict(flat=False)
    record_id = f"record:{uuid.uuid4()}"
    
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
    processed_data['created_at'] = datetime.now().isoformat()
    
    redis_client.set(record_id, json.dumps(processed_data))
    return redirect(url_for('index'))

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
