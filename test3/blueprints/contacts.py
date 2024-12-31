from typing import Dict, Any, Tuple
from flask import Blueprint, jsonify, request, render_template, current_app
from ..database import RedisDB
import uuid

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@contacts_bp.route('/api/records')
def get_records():
    """API endpoint to get all record IDs"""
    db = RedisDB()
    records = db.get_all_records()
    return jsonify([r.replace('contact:', '') for r in records])

@contacts_bp.route('/api/record/<record_id>')
def get_record(record_id: str):
    """API endpoint to get a single record"""
    db = RedisDB()
    record = db.get_record(record_id)
    if record:
        return jsonify(record)
    return jsonify({'error': 'Record not found'}), 404

@contacts_bp.route('/api/record', methods=['POST'])
def create_record():
    """API endpoint to create a new record"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    record_id = str(uuid.uuid4())
    db = RedisDB()
    if db.save_record(record_id, data):
        return jsonify({'id': record_id}), 201
    return jsonify({'error': 'Failed to save record'}), 500

@contacts_bp.route('/api/record/<record_id>', methods=['PUT'])
def update_record(record_id: str):
    """API endpoint to update a record"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    db = RedisDB()
    if db.save_record(record_id, data):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed to update record'}), 500

@contacts_bp.route('/api/record/<record_id>', methods=['DELETE'])
def delete_record(record_id: str):
    """API endpoint to delete a record"""
    db = RedisDB()
    if db.delete_record(record_id):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Failed to delete record'}), 500

@contacts_bp.route('/api/search')
def search_records():
    """API endpoint to search records"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    
    terms = query.split()
    db = RedisDB()
    records = db.search_records(terms)
    return jsonify([r.replace('contact:', '') for r in records])
