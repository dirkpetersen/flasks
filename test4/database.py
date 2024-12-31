from typing import Optional, Dict, List, Any, Union
import random
import string
import time
from datetime import datetime
import redis
from redis.commands.json.path import Path
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
                    sort_by="created_at",
                    sort_desc=True,
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
        """Search records with improved JSON handling"""
        try:
            # Escape special characters in query
            escaped_query = query.replace('"', '\\"').replace("'", "\\'")
            
            # Build search query using JSON path syntax
            search_parts = []
            if query:
                search_parts.append(f'(@title:"{escaped_query}" | @description:"{escaped_query}")')
            if creator_id:
                search_parts.append(f'@creator_id:{{{creator_id}}}')
            
            final_query = ' '.join(search_parts) if search_parts else '*'
            
            # Execute search with JSON-aware parameters
            res = self.client.ft(self.INDEX_NAME).search(
                final_query,
                sort_by="created_at",
                sort_desc=True
            )
            
            # Process results maintaining JSON structure
            records = []
            for doc in res.docs:
                try:
                    # Handle both string and direct JSON responses
                    if hasattr(doc, 'json'):
                        data = self.client.json().get(doc.id, Path.root_path())
                    else:
                        data = doc.__dict__
                    
                    if isinstance(data, list):
                        data = data[0]
                    
                    data['id'] = doc.id.split(':')[1]
                    records.append(data)
                except Exception as e:
                    current_app.logger.error(f"Error processing search result: {e}")
                    continue
            
            return records
        except Exception as e:
            current_app.logger.error(f"Error searching records: {e}")
            return []

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID using RedisJSON path"""
        try:
            key = f'record:{record_id}'
            # Use RedisJSON path to get specific fields
            data = self.client.json().get(key, Path.root_path())
            if data:
                if isinstance(data, list):
                    data = data[0]  # Handle case where root path returns list
                data['id'] = record_id
                return data
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting record: {e}")
            return None

    def save_record(self, record_id: str, data: Dict[str, Any]) -> bool:
        """Save or update a record using RedisJSON paths"""
        key = f'record:{record_id}'
        try:
            # Process timestamps
            if 'created_at' not in data:
                data['created_at'] = int(time.time())
            
            # Convert ISO timestamps to Unix timestamps
            for field in ['time_start', 'time_end']:
                if data.get(field):
                    data[field] = int(datetime.fromisoformat(data[field]).timestamp())
            
            # Initialize record if it doesn't exist
            if not self.client.exists(key):
                self.client.json().set(key, Path.root_path(), {})
            
            # Update fields using JSON path operations
            for field, value in data.items():
                if value not in (None, "", [], {}):
                    if isinstance(value, dict):
                        # Merge nested dictionaries
                        self.client.json().merge(key, f"$.{field}", value)
                    else:
                        # Set non-dictionary values
                        self.client.json().set(key, f"$.{field}", value)
                elif field in ['meta']:
                    # Preserve empty meta field as dictionary
                    self.client.json().set(key, f"$.{field}", {})
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error saving record {record_id}: {e}")
            raise RuntimeError(f"Failed to save record: {str(e)}")

    def delete_record(self, record_id: str) -> bool:
        """Delete a record"""
        return bool(self.client.delete(f'record:{record_id}'))

