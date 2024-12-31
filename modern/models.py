from datetime import datetime
import json
from typing import Dict, Any, List, Optional
from .redis_store import redis_client

class Contact:
    """Contact model for storing contact information in Redis"""
    
    @staticmethod
    def _generate_id() -> int:
        """Generate a new ID using Redis counter"""
        return int(redis_client.incr('contact:id:counter'))

    @staticmethod
    def _get_email_index(email: str) -> Optional[str]:
        """Get contact ID by email"""
        return redis_client.get(f'contact:email:{email}')

    def __init__(self, first_name: str, last_name: str, email: str, phone: str = None, 
                 id: int = None, created_at: str = None, updated_at: str = None):
        self.id = id or self._generate_id()
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or self.created_at

    def save(self) -> None:
        """Save contact to Redis"""
        # Check email uniqueness
        existing_id = self._get_email_index(self.email)
        if existing_id and int(existing_id) != self.id:
            raise ValueError("Email already exists")

        # Save contact data
        redis_client.hset(
            f'contact:{self.id}',
            mapping={
                'first_name': self.first_name,
                'last_name': self.last_name,
                'email': self.email,
                'phone': self.phone or '',
                'created_at': self.created_at,
                'updated_at': datetime.utcnow().isoformat()
            }
        )
        # Update email index
        redis_client.set(f'contact:email:{self.email}', self.id)

    def delete(self) -> None:
        """Delete contact from Redis"""
        redis_client.delete(f'contact:{self.id}')
        redis_client.delete(f'contact:email:{self.email}')

    def to_dict(self) -> Dict[str, Any]:
        """Convert contact to dictionary"""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def get(cls, contact_id: int) -> Optional['Contact']:
        """Get contact by ID"""
        data = redis_client.hgetall(f'contact:{contact_id}')
        if not data:
            return None
        return cls(id=contact_id, **data)

    @classmethod
    def get_all(cls) -> List['Contact']:
        """Get all contacts"""
        contacts = []
        for key in redis_client.keys('contact:[0-9]*'):
            contact_id = int(key.decode().split(':')[1])
            contact = cls.get(contact_id)
            if contact:
                contacts.append(contact)
        return contacts
