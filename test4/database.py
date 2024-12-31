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
            # Redis Search only works on DB 0
            self.client = redis.Redis(
                host=current_app.config['REDIS_HOST'],
                port=current_app.config['REDIS_PORT'],
                db=0,  # Force DB 0 for Redis Search compatibility
                decode_responses=True
            )
            self._ensure_search_index()

    def _ensure_search_index(self) -> None:
        """Create search index if it doesn't exist"""
        try:
            # Try to get index info first
            self.client.ft(self.INDEX_NAME).info()
        except redis.ResponseError:
            # Index doesn't exist, create it with auto-detected schema
            try:
                self.client.ft(self.INDEX_NAME).create_index(
                    fields=[
                        TextField("title"),
                        TextField("description"),
                        TagField("creator_id"),
                        NumericField("created_at"),
                        NumericField("time_start"),
                        NumericField("time_end"),
                        TagField("active")
                    ],
                    definition=IndexDefinition(
                        prefix=["record:"],
                        index_type=IndexType.JSON
                    )
                )
                current_app.logger.info("Created Redis Search index with auto-detected schema")
            except redis.ResponseError as e:
                current_app.logger.error(f"Failed to create Redis Search index: {e}")

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
            # Use Redis Search to get records
            query = "*"
            if creator_id:
                query = f"@creator_id:{{{creator_id}}}"
            
            # Execute search with pagination
            try:
                res = self.client.ft(self.INDEX_NAME).search(
                    query,
                    sortby=("created_at", True),
                    offset=(page - 1) * per_page,
                    num=per_page
                )
                
                records = []
                for doc in res.docs:
                    data = json.loads(doc.json)
                    data['id'] = doc.id.split(':')[1]
                    records.append(data)
                
                total = res.total
            except redis.ResponseError as e:
                current_app.logger.error(f"Search error: {e}")
                records = []
                total = 0
            
            # Debug logging
            current_app.logger.debug(f"Found {len(records)} total records")
            current_app.logger.debug(f"Records before pagination: {json.dumps(records, indent=2)}")
            
            # Apply pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_records = records[start:end]
            
            current_app.logger.debug(f"Records after pagination: {json.dumps(paginated_records, indent=2)}")
            
            result = {
                'records': paginated_records,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
            current_app.logger.debug(f"Returning result: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            current_app.logger.error(f"Error getting records: {e}")
            return {'records': [], 'total': 0, 'pages': 0}

    def search_records(self, query: str, creator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search records with optional creator filter"""
        try:
            # Use Redis Search for text search
            search_query = f'(@title:{query} | @description:{query})'
            if creator_id:
                search_query = f'({search_query}) @creator_id:{{{creator_id}}}'
            
            res = self.client.ft(self.INDEX_NAME).search(
                search_query,
                sortby=("created_at", True)
            )
            
            records = []
            for doc in res.docs:
                data = json.loads(doc.json)
                data['id'] = doc.id.split(':')[1]
                records.append(data)
            
            return records
        except Exception as e:
            current_app.logger.error(f"Error searching records: {e}")
            return []

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        try:
            key = f'record:{record_id}'
            # Use regular GET and JSON parsing since RedisJSON is not available
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
            if 'time_start' in data and data['time_start']:
                data['time_start'] = int(datetime.fromisoformat(data['time_start']).timestamp())
            if 'time_end' in data and data['time_end']:
                data['time_end'] = int(datetime.fromisoformat(data['time_end']).timestamp())
                
            # Remove empty fields, including nested dictionaries
            def clean_dict(d):
                if not isinstance(d, dict):
                    return d
                return {k: clean_dict(v) for k, v in d.items() 
                       if v not in (None, "", [], {}) 
                       and not (isinstance(v, dict) and not clean_dict(v))
                       and not (isinstance(v, list) and not v)}
            
            data = clean_dict(data)
            
            # Use regular SET with JSON string since RedisJSON is not available
            success = bool(self.client.set(key, json.dumps(data)))
            if not success:
                raise Exception("Redis SET returned False")
            return True
        except Exception as e:
            current_app.logger.error(f"Error saving record {record_id}: {e}")
            raise RuntimeError(f"Failed to save record: {str(e)}")

    def delete_record(self, record_id: str) -> bool:
        """Delete a record"""
        return bool(self.client.delete(f'record:{record_id}'))

