import json
import random
import string
import redis
import os
from datetime import datetime
import pytz
from typing import List, Optional

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0))
)

class WorkRecord:
    def __init__(self, id: str = None, title: str = None, description: str = None,
                 start_date: datetime = None, end_date: datetime = None,
                 active: bool = True, creator_id: str = None,
                 created_at: datetime = None, **meta_fields):
        self.id = id
        self.title = title
        self.description = description
        # Ensure dates are stored in UTC
        self.start_date = start_date.astimezone(pytz.UTC) if start_date else None
        self.end_date = end_date.astimezone(pytz.UTC) if end_date else None
        self.active = active
        self.creator_id = creator_id
        self.created_at = created_at or datetime.now(pytz.UTC)
        
        # Handle dynamic meta fields
        for field_name, value in meta_fields.items():
            setattr(self, field_name, value)

    @staticmethod
    def generate_id() -> str:
        pattern = os.getenv('WORK_ID_PATTERN', '(XX-XX)')
        # Define separate character sets for first X and subsequent X's
        valid_chars_first = string.ascii_uppercase.replace('O', '')  # Only letters for first X
        valid_chars_rest = valid_chars_first + string.digits.replace('0', '')  # Letters and numbers for rest
        
        result = ''
        first_x = True
        for char in pattern:
            if char == 'X':
                if first_x:
                    result += random.choice(valid_chars_first)
                    first_x = False
                else:
                    result += random.choice(valid_chars_rest)
            else:
                result += char
        return result

    def to_dict(self) -> dict:
        data = {}
        if self.id:
            data['id'] = self.id
        if self.title:
            data['title'] = self.title
        if self.description:
            data['description'] = self.description
        if self.start_date:
            data['start_date'] = self.start_date.isoformat()
        if self.end_date:
            data['end_date'] = self.end_date.isoformat()
        if self.active is not None:
            data['active'] = self.active
        if self.creator_id:
            data['creator_id'] = self.creator_id
        if self.work_type:
            data['work_type'] = self.work_type
        if self.required_apps:
            data['required_apps'] = self.required_apps
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkRecord':
        if not data:
            return None
            
        record = cls()
        record.id = data.get('id')
        record.title = data.get('title')
        record.description = data.get('description')
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'])
            if not start_date.tzinfo:
                start_date = pytz.UTC.localize(start_date)
            record.start_date = start_date.astimezone(pytz.UTC)
        else:
            record.start_date = None
            
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'])
            if not end_date.tzinfo:
                end_date = pytz.UTC.localize(end_date)
            record.end_date = end_date.astimezone(pytz.UTC)
        else:
            record.end_date = None
        record.active = data.get('active', True)
        record.creator_id = data.get('creator_id')
        # Get meta fields directly from data using original field names
        for key in data:
            # Skip standard fields that are already handled
            if key in ['id', 'title', 'description', 'start_date', 'end_date', 
                      'active', 'creator_id', 'created_at']:
                continue
            # Set the field using the original name from .env
            setattr(record, key, data.get(key))
        record.created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        return record

    def save(self):
        redis_client.set(f"work:{self.id}", json.dumps(self.to_dict()))
        redis_client.sadd(f"user_works:{self.creator_id}", self.id)

    @classmethod
    def get_by_id(cls, id: str) -> Optional['WorkRecord']:
        data = redis_client.get(f"work:{id}")
        if not data:
            return None
        return cls.from_dict(json.loads(data))

    @classmethod
    def get_by_user(cls, user_id: str) -> List['WorkRecord']:
        work_ids = redis_client.smembers(f"user_works:{user_id}")
        records = []
        for work_id in work_ids:
            record = cls.get_by_id(work_id.decode())
            if record:
                records.append(record)
        return sorted(records, key=lambda x: x.created_at, reverse=True)

    @classmethod
    def search(cls, query: str, user_only: bool = False, user_id: str = None) -> List['WorkRecord']:
        if user_only and not user_id:
            return []
            
        # Treat asterisk as empty string
        query = '' if query == '*' else query
            
        all_keys = redis_client.keys("work:*")
        results = []
        
        for key in all_keys:
            record = cls.get_by_id(key.decode().split(':')[1])
            if not record:
                continue
                
            if user_only and record.creator_id != user_id:
                continue
                
            # Search in title, description and id with None checks
            searchable_text = []
            if record.title:
                searchable_text.append(record.title.lower())
            if record.description:
                searchable_text.append(record.description.lower())
            if record.id:
                searchable_text.append(record.id.lower())
                
            if any(query.lower() in text for text in searchable_text):
                results.append(record)
                
        return sorted(results, key=lambda x: x.created_at, reverse=True)
