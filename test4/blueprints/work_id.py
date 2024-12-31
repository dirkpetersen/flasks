from flask import Blueprint, render_template, jsonify
from test4.database import RedisDB

work_id_bp = Blueprint('work_id', __name__)

@work_id_bp.route('/')
def index():
    return render_template('index.html')

@work_id_bp.route('/api/meta-fields')
def get_meta_fields():
    from flask import current_app
    return jsonify(current_app.config.get('META_FIELDS', {}))

@work_id_bp.route('/api/new-id')
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
