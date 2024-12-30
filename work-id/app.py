#! /usr/bin/env python3

import sys, os, base64, io, random, string
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response, session
from captcha.image import ImageCaptcha
from dotenv import load_dotenv
from models import WorkRecord, redis_client

# Load environment variables
load_dotenv()

debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
force_captcha = os.getenv('FORCE_CAPTCHA', 'False').lower() == 'true'
app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session

def get_meta_fields():
    meta_fields = {'single_select': {}, 'multi_select': {}}
    
    # Get all environment variables
    for key, value in os.environ.items():
        # Process single select fields
        if key.startswith('META_SEL_'):
            field_name = key[9:]  # Remove 'META_SEL_' prefix
            meta_fields['single_select'][field_name] = value.split(',')
            
        # Process multi select fields
        elif key.startswith('META_MSEL_'):
            field_name = key[10:]  # Remove 'META_MSEL_' prefix
            meta_fields['multi_select'][field_name] = value.split(',')
            
    return meta_fields

@app.route('/')
def index():
    user_id = request.cookies.get('creator_id', '')
    meta_fields = get_meta_fields()
    app_name = os.getenv('APP_NAME', 'Work-ID')
    return render_template('index.html', 
                         user_id=user_id,
                         meta_fields=meta_fields,
                         new_id=WorkRecord.generate_id(),
                         force_captcha=force_captcha,
                         app_name=app_name)

@app.route('/api/captcha')
def get_captcha():
    image = ImageCaptcha(width=280, height=90)
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    session['captcha_text'] = captcha_text
    
    # Generate the image
    data = image.generate(captcha_text)
    
    # Convert to base64
    buffered = io.BytesIO()
    image.write(captcha_text, buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({'image': img_str})

@app.route('/api/records', methods=['GET'])
def get_records():
    try:
        recent = request.args.get('recent', None)
        user_id = request.cookies.get('creator_id')
        
        # Get all records
        all_keys = redis_client.keys("work:*")
        records = []
    
        for key in all_keys:
            record = WorkRecord.get_by_id(key.decode().split(':')[1])
            if record:
                records.append(record)
    
        # Sort by created_at timestamp, newest first
        records.sort(key=lambda x: x.created_at, reverse=True)
    
        if recent:
            try:
                limit = int(recent)
                if limit < 1:
                    return jsonify({'error': 'Recent parameter must be positive'}), 400
                # Apply limit and return just IDs
                records = records[:limit]
                return jsonify([record.id for record in records])
            except ValueError:
                return jsonify({'error': 'Invalid recent parameter'}), 400
    
        # If user_id is set, return full records for that user
        if user_id:
            user_records = [r for r in records if r.creator_id == user_id]
            return jsonify([record.to_dict() for record in user_records])
    
        # Default behavior - return all IDs when no email is set
        return jsonify([record.id for record in records])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/records', methods=['POST'])
def create_record():
    data = request.json
    
    # Only check CAPTCHA if force_captcha is enabled
    if force_captcha and not session.get('verified', False):
        # Verify CAPTCHA
        captcha_input = data.get('captcha')
        if not captcha_input or captcha_input.upper() != session.get('captcha_text', ''):
            return jsonify({'error': 'Invalid CAPTCHA'}), 400
        session['verified'] = True
    user_id = request.cookies.get('creator_id')
    
    if not user_id:
        return jsonify({'error': 'No user ID set'}), 400

    # Set default times for dates
    start_date = None
    if data.get('start_date'):
        start_date = datetime.fromisoformat(data.get('start_date'))
        # Set to beginning of day (00:00:00)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    end_date = None
    if data.get('end_date'):
        end_date = datetime.fromisoformat(data.get('end_date'))
        # Set to end of day (23:59:59)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Build record data dynamically
    record_data = {
        'id': data.get('id') or WorkRecord.generate_id(),
        'title': data.get('title'),
        'description': data.get('description'),
        'start_date': start_date,
        'end_date': end_date,
        'active': data.get('active', True),
        'creator_id': user_id
    }
    
    # Add meta fields dynamically
    meta_fields = get_meta_fields()
    for field_type in ['single_select', 'multi_select']:
        for field_name in meta_fields[field_type]:
            # Use the original field name from .env for Redis storage
            meta_key = f"META_{'SEL' if field_type == 'single_select' else 'MSEL'}_{field_name}"
            if meta_key in data:
                record_data[meta_key] = data[meta_key]

    record = WorkRecord(**record_data)
    
        record.save()
        return jsonify(record.to_dict())
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/records/<id>', methods=['PUT'])
def update_record(id):
    try:
        data = request.json
        user_id = request.cookies.get('creator_id')
        
        record = WorkRecord.get_by_id(id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        if record.creator_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403

    record.title = data.get('title', record.title)
    record.description = data.get('description', record.description)
    if data.get('start_date'):
        start_date = datetime.fromisoformat(data['start_date'])
        record.start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if data.get('end_date'):
        end_date = datetime.fromisoformat(data['end_date'])
        record.end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    record.active = data.get('active', record.active)
    
    # Get meta fields dynamically from data
    meta_fields = get_meta_fields()
    for field_type in ['single_select', 'multi_select']:
        for field_name in meta_fields[field_type]:
            meta_key = f"META_{'SEL' if field_type == 'single_select' else 'MSEL'}_{field_name}"
            if meta_key in data:
                field_value = data[meta_key]
                setattr(record, meta_key, field_value)
    
    record.save()
    return jsonify(record.to_dict())

@app.route('/api/new-id')
def get_new_id():
    return jsonify({'id': WorkRecord.generate_id()})

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    user_only = request.args.get('user_only', 'false').lower() == 'true'
    user_id = request.cookies.get('creator_id')
    
    if not user_id and user_only:
        return jsonify({'error': 'No user ID set'}), 400
        
    results = WorkRecord.search(query, user_only, user_id)
    return jsonify([record.to_dict() for record in results])

@app.route('/api/set-user-id', methods=['POST'])
def set_user_id():
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
        
    response = make_response(jsonify({'status': 'ok'}))
    response.set_cookie('creator_id', user_id)
    return response

@app.route('/api/records/<id>', methods=['GET'])
@app.route('/api/records/<id>/details', methods=['GET'])
def get_record_details(id):
    """Get detailed information for a specific record by ID"""
    # Get the pattern from env
    pattern = os.getenv('WORK_ID_PATTERN', '(XX-XX)')
    
    # If ID length doesn't match pattern, try to fix it
    if len(id) != len(pattern):
        # Extract non-alphanumeric characters from pattern
        pattern_special = ''.join(c for c in pattern if not c.isalnum())
        # Add missing special characters from pattern
        for char in pattern_special:
            if char not in id:
                pos = pattern.find(char)
                if pos < len(id):
                    id = id[:pos] + char + id[pos:]
                else:
                    id = id + char
    
    record = WorkRecord.get_by_id(id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    return jsonify(record.to_dict())


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
