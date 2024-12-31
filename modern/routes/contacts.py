from flask import Blueprint, jsonify, request, render_template
from http import HTTPStatus
from typing import Tuple, Dict, Any, Union
from ..models import Contact

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('/')
def index() -> str:
    """Render the main application page"""
    return render_template('index.html')

@contacts_bp.route('/api/contacts', methods=['GET'])
def get_contacts() -> Tuple[Dict[str, Any], int]:
    """Get all contacts"""
    contacts = Contact.get_all()
    return jsonify([contact.to_dict() for contact in contacts]), HTTPStatus.OK

@contacts_bp.route('/api/contacts', methods=['POST'])
def create_contact() -> Tuple[Dict[str, Any], int]:
    """Create a new contact"""
    data = request.get_json()
    try:
        contact = Contact(**data)
        contact.save()
        return jsonify(contact.to_dict()), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({'error': str(e)}), HTTPStatus.BAD_REQUEST

@contacts_bp.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id: int) -> Tuple[Dict[str, Any], int]:
    """Update an existing contact"""
    contact = Contact.get(contact_id)
    if not contact:
        return jsonify({'error': 'Contact not found'}), HTTPStatus.NOT_FOUND
    
    data = request.get_json()
    for key, value in data.items():
        setattr(contact, key, value)
    contact.save()
    return jsonify(contact.to_dict()), HTTPStatus.OK

@contacts_bp.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id: int) -> Tuple[Dict[str, str], int]:
    """Delete a contact"""
    contact = Contact.get(contact_id)
    if not contact:
        return jsonify({'error': 'Contact not found'}), HTTPStatus.NOT_FOUND
    contact.delete()
    return jsonify({'message': 'Contact deleted'}), HTTPStatus.OK
