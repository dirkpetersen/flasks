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
        except redis.ResponseError:
            # Create the index
            schema = (
                TextField("$.title", as_name="title"),
                TextField("$.description", as_name="description"),
                TagField("$.creator_id", as_name="creator_id"),
                NumericField("$.created_at", as_name="created_at"),
                NumericField("$.time_start", as_name="time_start"),
                NumericField("$.time_end", as_name="time_end"),
                TagField("$.active", as_name="active")
            )
            
            self.client.ft(self.INDEX_NAME).create_index(
                schema,
                definition=IndexDefinition(
                    prefix=["record:"],
                    index_type=IndexType.JSON
                )
            )

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
        query = "@creator_id:{}".format(creator_id) if creator_id else "*"
        
        try:
            result = self.client.ft(self.INDEX_NAME).search(
                query,
                sort_by="created_at",
                sort_desc=True,
                offset=(page-1)*per_page,
                num=per_page
            )
            
            records = []
            for doc in result.docs:
                record = json.loads(doc.json)
                record['id'] = doc.id.split(':')[1]
                records.append(record)
                
            return {
                'records': records,
                'total': result.total,
                'pages': (result.total + per_page - 1) // per_page
            }
        except redis.ResponseError:
            return {'records': [], 'total': 0, 'pages': 0}

    def search_records(self, query: str, creator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search records with optional creator filter"""
        search_query = f'(@title|description:{query})'
        if creator_id:
            search_query += f' @creator_id:{creator_id}'
            
        try:
            result = self.client.ft(self.INDEX_NAME).search(search_query)
            records = []
            for doc in result.docs:
                record = json.loads(doc.json)
                record['id'] = doc.id.split(':')[1]
                records.append(record)
            return records
        except redis.ResponseError:
            return []

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        data = self.client.json().get(f'record:{record_id}')
        if data:
            data['id'] = record_id
            return data
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
            
            return bool(self.client.json().set(key, '$', data))
        except Exception as e:
            current_app.logger.error(f"Error saving record: {e}")
            return False

    def delete_record(self, record_id: str) -> bool:
        """Delete a record"""
        return bool(self.client.delete(f'record:{record_id}'))

