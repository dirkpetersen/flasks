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
    def __init__(self, **kwargs):
        """Initialize a work record with validation"""
        self._data = {}
        
        print("\nDEBUG - WorkRecord Init - Incoming kwargs:", kwargs)
        
        # List of known fields and extract them
        known_fields = {
            'id', 'title', 'description', 'start_date', 'end_date',
            'active', 'creator_id', 'created_at'
        }
        
        # Extract known fields from kwargs
        for field in known_fields:
            self._data[field] = kwargs.get(field)
            print(f"DEBUG - WorkRecord Init - Setting {field}:", self._data[field])
        
        # Convert dates to UTC timezone
        if self._data['start_date']:
            self._data['start_date'] = self._data['start_date'].astimezone(pytz.UTC)
        if self._data['end_date']:
            self._data['end_date'] = self._data['end_date'].astimezone(pytz.UTC)
        self._data['created_at'] = self._data['created_at'] or datetime.now(pytz.UTC)
        

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
        data = self._data.copy()
        
        # Convert datetime objects to ISO format strings
        if data.get('start_date'):
            data['start_date'] = data['start_date'].isoformat()
        if data.get('end_date'):
            data['end_date'] = data['end_date'].isoformat()
        if data.get('created_at'):
            data['created_at'] = data['created_at'].isoformat()
            
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkRecord':
        if not data:
            return None
            
        # Handle created_at with default value
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
            if not created_at.tzinfo:
                created_at = pytz.UTC.localize(created_at)
        else:
            created_at = datetime.now(pytz.UTC)
            
        # Process dates
        start_date = None
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'])
            if not start_date.tzinfo:
                start_date = pytz.UTC.localize(start_date)
            start_date = start_date.astimezone(pytz.UTC)
            
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'])
            if not end_date.tzinfo:
                end_date = pytz.UTC.localize(end_date)
            end_date = end_date.astimezone(pytz.UTC)
            
                
        # Create record with all fields
        record = cls(
            id=data.get('id'),
            title=data.get('title'),
            description=data.get('description'),
            start_date=start_date,
            end_date=end_date,
            active=data.get('active', True),
            creator_id=data.get('creator_id'),
            created_at=created_at,
        )
        return record

    def validate(self):
        """Validate record data before saving"""
        if self._data.get('id') == '(ML-3A)':
            print("\nDEBUG - WorkRecord Validate:")
            print("Validating record data:", self._data)

        
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End date cannot be before start date")
                
        if not self.title:
            raise ValueError("Title is required")
            
        if not self.creator_id:
            raise ValueError("Creator ID is required")

    def save(self):
        try:
            print("\nDEBUG - WorkRecord save - Current _data contents:", self._data)
                    
            self.validate()
            record_data = self.to_dict()
            
            print("\nDEBUG - WorkRecord save - Data being saved:")
            print(f"Key: work:{self.id}")
            print(f"Data: {json.dumps(record_data, indent=2)}")
            print(f"User works key: user_works:{self.creator_id}")
            
            # Try to save and verify the data
            redis_client.set(f"work:{self.id}", json.dumps(record_data))
            redis_client.sadd(f"user_works:{self.creator_id}", self.id)
            
            # Verify the save
            saved_data = redis_client.get(f"work:{self.id}")
            if saved_data:
                if self.id == '(ML-3A)':
                    print("\nDEBUG - Verification - Data in Redis:")
                    print(json.loads(saved_data))
            else:
                if self.id == '(ML-3A)':
                    print("\nDEBUG - ERROR: Data not found in Redis after save!")
                
        except redis.RedisError as e:
            if self.id == '(ML-3A)':
                print(f"\nDEBUG - Redis Error: {str(e)}")
            raise RuntimeError(f"Database error: {str(e)}")
        except Exception as e:
            if self.id == '(ML-3A)':
                print(f"\nDEBUG - Unexpected Error: {str(e)}")
            raise

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
    def __getattr__(self, name):
        return self._data.get(name)
        
    def __setattr__(self, name, value):
        if name == '_data':
            super().__setattr__(name, value)
        else:
            print(f"DEBUG - WorkRecord __setattr__ - Setting {name} to:", value)
            print(f"DEBUG - WorkRecord __setattr__ - Value type:", type(value))
            self._data[name] = value
