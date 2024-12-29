#! /usr/bin/env python3

import sys, os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, make_response
from dotenv import load_dotenv
from models import WorkRecord
import pytz

# Load environment variables
load_dotenv()

debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

def get_meta_fields():
    work_types = os.getenv('META_SEL_WorkType', '').split(',')
    required_apps = os.getenv('META_MSEL_RequiredApps', '').split(',')
    return {
        'work_types': work_types,
        'required_apps': required_apps
    }

@app.route('/')
def index():
    email = request.cookies.get('creator_email', '')
    meta_fields = get_meta_fields()
    return render_template('index.html', 
                         email=email,
                         meta_fields=meta_fields,
                         new_id=WorkRecord.generate_id())

@app.route('/api/records', methods=['GET'])
def get_records():
    email = request.cookies.get('creator_email')
    if not email:
        return jsonify({'error': 'No email set'}), 400
    
    records = WorkRecord.get_by_user(email)
    return jsonify([record.to_dict() for record in records])

@app.route('/api/records', methods=['POST'])
def create_record():
    data = request.json
    email = request.cookies.get('creator_email')
    
    if not email:
        return jsonify({'error': 'No email set'}), 400

    record = WorkRecord(
        id=data.get('id') or WorkRecord.generate_id(),
        title=data.get('title'),
        description=data.get('description'),
        start_date=datetime.fromisoformat(data.get('start_date')) if data.get('start_date') else None,
        end_date=datetime.fromisoformat(data.get('end_date')) if data.get('end_date') else None,
        timezone=data.get('timezone') or str(datetime.now().astimezone().tzinfo),
        active=data.get('active', True),
        creator_email=email,
        work_type=data.get('work_type'),
        required_apps=data.get('required_apps', [])
    )
    
    record.save()
    return jsonify(record.to_dict())

@app.route('/api/records/<id>', methods=['PUT'])
def update_record(id):
    data = request.json
    email = request.cookies.get('creator_email')
    
    record = WorkRecord.get_by_id(id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    
    if record.creator_email != email:
        return jsonify({'error': 'Unauthorized'}), 403

    record.title = data.get('title', record.title)
    record.description = data.get('description', record.description)
    record.start_date = datetime.fromisoformat(data['start_date']) if data.get('start_date') else record.start_date
    record.end_date = datetime.fromisoformat(data['end_date']) if data.get('end_date') else record.end_date
    record.timezone = data.get('timezone', record.timezone)
    record.active = data.get('active', record.active)
    record.work_type = data.get('work_type', record.work_type)
    record.required_apps = data.get('required_apps', record.required_apps)
    
    record.save()
    return jsonify(record.to_dict())

@app.route('/api/new-id')
def get_new_id():
    return jsonify({'id': WorkRecord.generate_id()})

@app.route('/api/search')
def search():
    query = request.args.get('q', '')
    user_only = request.args.get('user_only', 'false').lower() == 'true'
    email = request.cookies.get('creator_email')
    
    if not email and user_only:
        return jsonify({'error': 'No email set'}), 400
        
    results = WorkRecord.search(query, user_only, email)
    return jsonify([record.to_dict() for record in results])

@app.route('/api/set-email', methods=['POST'])
def set_email():
    email = request.json.get('email')
    if not email:
        return jsonify({'error': 'Email is required'}), 400
        
    response = make_response(jsonify({'status': 'ok'}))
    response.set_cookie('creator_email', email)
    return response

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
