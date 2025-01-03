from flask import Blueprint, render_template, jsonify, request, current_app
from test4.database import RedisDB
from test4.utils import local_only

work_id_bp = Blueprint('work_id', __name__)

@work_id_bp.route('/api/records', methods=['GET'])
@local_only
def get_records():
    db = RedisDB()
    page = request.args.get('page', 1, type=int)
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    user_id = request.args.get('user_id')
    
    if not show_all and user_id:
        records = db.get_all_records(creator_id=user_id, page=page)
    else:
        records = db.get_all_records(page=page)
    
    return jsonify(records)

@work_id_bp.route('/api/records/<record_id>', methods=['GET'])
@local_only
def get_record(record_id):
    db = RedisDB()
    record = db.get_record(record_id)
    if record:
        return jsonify(record)
    return jsonify({'error': 'Record not found'}), 404

@work_id_bp.route('/api/records', methods=['POST'])
@local_only
def create_record():
    db = RedisDB()
    data = request.get_json()
    record_id = data.get('id')
    if not record_id:
        return jsonify({'error': 'Record ID is required'}), 400
    try:
        db.save_record(record_id, data)
        return jsonify({'message': 'Record created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@work_id_bp.route('/api/records/<record_id>', methods=['PUT'])
@local_only
def update_record(record_id):
    db = RedisDB()
    data = request.get_json()
    try:
        db.save_record(record_id, data)
        return jsonify({'message': 'Record updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@work_id_bp.route('/api/search')
@local_only
def search_records():
    db = RedisDB()
    # Decode the query parameter since it may be URL encoded
    query = request.args.get('q', '', type=str)
    query = query.strip()
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    user_id = request.args.get('user_id')
    
    if not show_all and user_id:
        records = db.search_records(query, creator_id=user_id)
    else:
        records = db.search_records(query)
    
    return jsonify(records)

@work_id_bp.route('/')
def index():
    return render_template('index.html', app_name=current_app.config['APP_NAME'])

@work_id_bp.route('/api/meta-fields')
@local_only
def get_meta_fields():
    from flask import current_app
    return jsonify(current_app.config.get('META_FIELDS', {}))

@work_id_bp.route('/api/new-id')
@local_only
def get_new_id():
    try:
        db = RedisDB()
        new_id = db.generate_work_id()
        if not new_id:
            raise ValueError("Failed to generate a valid ID")
        return jsonify({'id': new_id})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error generating new ID: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@work_id_bp.route('/api/public/ids')
def get_public_ids():
    """Get list of all public record IDs"""
    try:
        db = RedisDB()
        public_ids = db.get_public_record_ids()
        return jsonify(public_ids)
    except Exception as e:
        current_app.logger.error(f"Error getting public IDs: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@work_id_bp.route('/api/public/id/<record_id>')
def get_public_record(record_id):
    """Get a public record by ID or partial ID"""
    try:
        db = RedisDB()
        record = db.get_public_record(record_id)
        if record:
            return jsonify(record)
        return jsonify({'error': 'Record not found or not public'}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting public record: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
