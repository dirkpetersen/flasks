from typing import Optional, Dict, List, Any
import json
import redis
from flask import current_app

table='default'

class RedisDB:
    _instance = None

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

    def get_all_records(self) -> List[str]:
        """Get all record IDs"""
        return self.client.keys(f'{table}:*')

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID"""
        data = self.client.get(f'{table}:{record_id}')
        return json.loads(data) if data else None

    def save_record(self, record_id: str, data: Dict[str, Any]) -> bool:
        """Save or update a record"""
        key = f'{table}:{record_id}'
        try:
            return bool(self.client.set(key, json.dumps(data)))
        except Exception:
            return False

    def delete_record(self, record_id: str) -> bool:
        """Delete a record"""
        return bool(self.client.delete(f'{table}:{record_id}'))

