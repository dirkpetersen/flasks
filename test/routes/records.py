from flask import Blueprint, jsonify, request, redirect, url_for, make_response
from typing import Dict, Any, Optional
import json
from datetime import datetime
import uuid
from test.database import redis_client
from test.utils import parse_meta_fields

records = Blueprint('records', __name__)

@records.route('/save_record', methods=['POST'])
def save_record() -> Any:
    data: Dict = request.form.to_dict(flat=False)
    record_id: Optional[str] = data.get('record_id', [None])[0]
    
    if not record_id:
        record_id = str(uuid.uuid4())
    
    redis_key: str = f"record:{record_id}"
    
    # Convert single items from lists to single values
    processed_data: Dict[str, Any] = {}
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
    return redirect(url_for('main.index'))

@records.route('/get_record/<record_id>')
def get_record(record_id: str) -> Any:
    key = f"record:{record_id}"
    record = redis_client.get(key)
    if record:
        return make_response(jsonify(json.loads(record)), 200)
    return make_response(jsonify({"error": "Record not found"}), 404)

@records.route('/delete/<record_id>')
def delete_record(record_id: str) -> Any:
    redis_client.delete(f"record:{record_id}")
    return redirect(url_for('main.index'))
