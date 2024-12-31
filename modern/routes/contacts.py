from flask import Blueprint, jsonify, request, render_template
from http import HTTPStatus
from typing import Tuple, Dict, Any, Union
from ..models import Contact
from ..extensions import db

contacts_bp = Blueprint('contacts', __name__)

@contacts_bp.route('/')
def index() -> str:
    """Render the main application page"""
    return render_template('index.html')

@contacts_bp.route('/api/contacts', methods=['GET'])
def get_contacts() -> Tuple[Dict[str, Any], int]:
    """Get all contacts"""
    contacts = Contact.query.all()
    return jsonify([contact.to_dict() for contact in contacts]), HTTPStatus.OK

@contacts_bp.route('/api/contacts', methods=['POST'])
def create_contact() -> Tuple[Dict[str, Any], int]:
    """Create a new contact"""
    data = request.get_json()
    contact = Contact(**data)
    db.session.add(contact)
    db.session.commit()
    return jsonify(contact.to_dict()), HTTPStatus.CREATED

@contacts_bp.route('/api/contacts/<int:contact_id>', methods=['PUT'])
def update_contact(contact_id: int) -> Tuple[Dict[str, Any], int]:
    """Update an existing contact"""
    contact = Contact.query.get_or_404(contact_id)
    data = request.get_json()
    for key, value in data.items():
        setattr(contact, key, value)
    db.session.commit()
    return jsonify(contact.to_dict()), HTTPStatus.OK

@contacts_bp.route('/api/contacts/<int:contact_id>', methods=['DELETE'])
def delete_contact(contact_id: int) -> Tuple[Dict[str, str], int]:
    """Delete a contact"""
    contact = Contact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    return jsonify({'message': 'Contact deleted'}), HTTPStatus.OK
