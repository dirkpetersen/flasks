from flask import Blueprint, render_template, jsonify, request, current_app, redirect, url_for
from test4.database import RedisDB
from test4.utils import local_only
from test4.email_verification import (
    validate_email_address, generate_token, verify_token,
    send_verification_email, store_identity, get_identity
)

work_id_bp = Blueprint('work_id', __name__)

@work_id_bp.route('/api/records', methods=['GET'])
@local_only
def get_records():
    db = RedisDB()
    page = request.args.get('page', 1, type=int)
    show_all = request.args.get('show_all', 'false').lower() == 'true'
    user_id = request.args.get('user_id')
    records = db.get_all_records(creator_id=user_id, page=page, show_all=show_all)
    
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
    
    # Get existing record
    existing_record = db.get_record(record_id)
    if not existing_record:
        return jsonify({'error': 'Record not found'}), 404
        
    # Check if user owns the record
    if existing_record.get('creator_id') != data.get('creator_id'):
        return jsonify({'error': 'You can only modify your own records'}), 403
    
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
    
    records = db.search_records(query, creator_id=user_id, show_all=show_all)
    
    return jsonify(records)

@work_id_bp.route('/')
def index():
    creator_token = request.cookies.get('creatorToken')
    if not creator_token:
        return redirect(url_for('work_id.verify_email'))
    
    email = verify_creator_token(creator_token)
    if not email or not get_identity(email):
        return redirect(url_for('work_id.verify_email'))
        
    return render_template('index.html', 
                         app_name=current_app.config['APP_NAME'],
                         verified_email=email)

@work_id_bp.route('/verify')
def verify_email():
    return render_template('verify_email.html', app_name=current_app.config['APP_NAME'])

@work_id_bp.route('/api/verify-email', methods=['POST'])
@local_only
def initiate_verification():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
        
    valid, normalized_email = validate_email_address(email)
    if not valid:
        return jsonify({'error': normalized_email}), 400
    
    # Generate verification token
    token = generate_token(normalized_email)
    
    # Store unverified identity
    store_identity(normalized_email, verified=False)
    
    # Send verification email
    if not send_verification_email(normalized_email, token):
        return jsonify({'error': 'Failed to send verification email'}), 500
        
    return jsonify({
        'message': 'Please check your email for two messages:\n' +
                  '1. AWS SES verification request\n' +
                  '2. Application verification link (will arrive after confirming the first email)'
    })

@work_id_bp.route('/verify/<token>')
def verify_email_token(token):
    email = verify_token(token)
    if not email:
        return render_template('verify_email.html', 
                             error='Invalid or expired verification link',
                             app_name=current_app.config['APP_NAME'])
    
    # Update identity as verified
    if not store_identity(email, verified=True):
        return render_template('verify_email.html',
                             error='Failed to verify email',
                             app_name=current_app.config['APP_NAME'])
    
    response = redirect(url_for('work_id.index'))
    creator_token = generate_creator_token(email)
    response.set_cookie('creatorToken', creator_token, max_age=30*24*60*60)  # 30 days
    return response

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
