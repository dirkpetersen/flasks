from functools import wraps
from flask import request, jsonify

def local_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.remote_addr.startswith(('127.', '::1')):
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, **kwargs)
    return decorated_function
