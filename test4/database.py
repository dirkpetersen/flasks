from typing import Optional, Dict, List, Any
import json
import random
import string
import time
from datetime import datetime
import redis
from redis.commands.search.field import TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from flask import current_app

class RedisDB:
    _instance = None
    INDEX_NAME = "records-idx"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'client'):
            self.client = redis.Redis(
                host=current_app.config['REDIS_HOST'],
                port=current_app.config['REDIS_PORT'],
                db=current_app.config['REDIS_DB'],
                decode_responses=True
            )
            self._ensure_search_index()

    def _ensure_search_index(self) -> None:
        """Create search index if it doesn't exist"""
        try:
            self.client.ft(self.INDEX_NAME).info()
        except (redis.ResponseError, redis.exceptions.ModuleError):
            current_app.logger.warning("Redis Search module not available - search functionality will be limited")

    def generate_work_id(self) -> str:
        """Generate a unique work ID based on pattern"""
        pattern = current_app.config['WORK_ID_PATTERN']
        valid_chars = string.ascii_uppercase.replace('O', '') + string.digits.replace('0', '')
        
        while True:
            work_id = ''.join(random.choice(valid_chars) if c == 'X' else c 
                            for c in pattern)
            if not self.get_record(work_id):
                return work_id

    def get_all_records(self, creator_id: Optional[str] = None, 
                       page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """Get paginated records, optionally filtered by creator"""
        try:
            # Fallback to scanning when search is not available
            records = []
            total = 0
            scan_pattern = "record:*"
            cursor = "0"
            
            while cursor != 0:
                cursor, keys = self.client.scan(cursor=cursor, match=scan_pattern)
                for key in keys:
                    data = self.client.json().get(key)
                    if data:
                        record_id = key.split(':')[1]
                        if not creator_id or data.get('creator_id') == creator_id:
                            data['id'] = record_id
                            records.append(data)
                            total += 1
                cursor = int(cursor)
            
            # Sort records by created_at
            records.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            
            # Apply pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_records = records[start:end]
            
            return {
                'records': paginated_records,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        except Exception as e:
            current_app.logger.error(f"Error getting records: {e}")
            return {'records': [], 'total': 0, 'pages': 0}

    def search_records(self, query: str, creator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search records with optional creator filter"""
        try:
            # Fallback to basic filtering when search is not available
            records = []
            scan_pattern = "record:*"
            cursor = "0"
            query = query.lower()
            
            while cursor != 0:
                cursor, keys = self.client.scan(cursor=cursor, match=scan_pattern)
                for key in keys:
                    data = self.client.json().get(key)
                    if data:
                        # Basic text search in title and description
                        title = str(data.get('title', '')).lower()
                        description = str(data.get('description', '')).lower()
                        if (query in title or query in description) and \
                           (not creator_id or data.get('creator_id') == creator_id):
                            record_id = key.split(':')[1]
                            data['id'] = record_id
                            records.append(data)
                cursor = int(cursor)
            
            return records
        except Exception as e:
            current_app.logger.error(f"Error searching records: {e}")
            return []

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        try:
            key = f'record:{record_id}'
            # Try JSON.GET first
            try:
                data = self.client.json().get(key)
            except redis.exceptions.ResponseError:
                # Fallback to regular GET and JSON parsing
                data_str = self.client.get(key)
                data = json.loads(data_str) if data_str else None
            
            if data:
                data['id'] = record_id
                return data
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting record: {e}")
            return None

    def save_record(self, record_id: str, data: Dict[str, Any]) -> bool:
        """Save or update a record"""
        key = f'record:{record_id}'
        try:
            # Ensure timestamps are integers
            if 'created_at' not in data:
                data['created_at'] = int(time.time())
            if 'time_start' in data:
                data['time_start'] = int(datetime.fromisoformat(data['time_start']).timestamp())
            if 'time_end' in data:
                data['time_end'] = int(datetime.fromisoformat(data['time_end']).timestamp())
                
            # Remove empty fields
            data = {k: v for k, v in data.items() if v not in (None, "")}
            
            # Try JSON.SET first
            try:
                return bool(self.client.json().set(key, '$', data))
            except redis.exceptions.ResponseError:
                # Fallback to regular SET with JSON string
                return bool(self.client.set(key, json.dumps(data)))
        except Exception as e:
            current_app.logger.error(f"Error saving record: {e}")
            return False

    def delete_record(self, record_id: str) -> bool:
        """Delete a record"""
        return bool(self.client.delete(f'record:{record_id}'))

