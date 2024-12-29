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
                 timezone: str = None, active: bool = True, creator_email: str = None,
                 work_type: str = None, required_apps: List[str] = None,
                 created_at: datetime = None):
        self.id = id
        self.title = title
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone or str(datetime.now().astimezone().tzinfo)
        self.active = active
        self.creator_email = creator_email
        self.work_type = work_type if work_type else None
        self.required_apps = required_apps if required_apps else None
        self.created_at = created_at or datetime.now(pytz.UTC)

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
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'timezone': self.timezone,
            'active': self.active,
            'creator_email': self.creator_email,
            'work_type': self.work_type if self.work_type else None,
            'required_apps': self.required_apps if self.required_apps else None,
            'created_at': self.created_at.isoformat()
        }

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
            record.start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            record.start_date = None
            
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'])
            record.end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            record.end_date = None
        record.timezone = data.get('timezone')
        record.active = data.get('active', True)
        record.creator_email = data.get('creator_email')
        record.work_type = data.get('work_type')
        record.required_apps = data.get('required_apps', [])
        record.created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        return record

    def save(self):
        redis_client.set(f"work:{self.id}", json.dumps(self.to_dict()))
        redis_client.sadd(f"user_works:{self.creator_email}", self.id)

    @classmethod
    def get_by_id(cls, id: str) -> Optional['WorkRecord']:
        data = redis_client.get(f"work:{id}")
        if not data:
            return None
        return cls.from_dict(json.loads(data))

    @classmethod
    def get_by_user(cls, email: str) -> List['WorkRecord']:
        work_ids = redis_client.smembers(f"user_works:{email}")
        records = []
        for work_id in work_ids:
            record = cls.get_by_id(work_id.decode())
            if record:
                records.append(record)
        return sorted(records, key=lambda x: x.created_at, reverse=True)

    @classmethod
    def search(cls, query: str, user_only: bool = False, user_email: str = None) -> List['WorkRecord']:
        if user_only and not user_email:
            return []
            
        all_keys = redis_client.keys("work:*")
        results = []
        
        for key in all_keys:
            record = cls.get_by_id(key.decode().split(':')[1])
            if not record:
                continue
                
            if user_only and record.creator_email != user_email:
                continue
                
            # Search in title and description
            if (query.lower() in record.title.lower() or 
                query.lower() in record.description.lower() or
                query.lower() in record.id.lower()):
                results.append(record)
                
        return sorted(results, key=lambda x: x.created_at, reverse=True)