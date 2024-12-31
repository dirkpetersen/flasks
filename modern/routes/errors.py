from flask import Blueprint, jsonify
from http import HTTPStatus
from typing import Tuple, Dict

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def not_found_error(error) -> Tuple[Dict[str, str], int]:
    return jsonify({'error': 'Resource not found'}), HTTPStatus.NOT_FOUND

@errors_bp.app_errorhandler(500)
def internal_error(error) -> Tuple[Dict[str, str], int]:
    return jsonify({'error': 'Internal server error'}), HTTPStatus.INTERNAL_SERVER_ERROR
