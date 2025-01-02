from typing import Optional, Dict, List, Any, Union
import random
import string
import time
import json
from datetime import datetime, timezone
import redis
from redis.commands.json.path import Path
from flask import current_app

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
                db=current_app.config.get('REDIS_DB', 0),
                decode_responses=True
            )
            current_app.logger.debug("Redis client initialized")


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
            # Get all records
            keys = self.client.keys('record:*')
            records = []
            
            for key in keys:
                data = self.client.json().get(key, Path.root_path())
                if isinstance(data, list):
                    data = data[0]
                
                # Filter by creator_id if specified
                if creator_id and data.get('creator_id') != creator_id:
                    continue
                    
                data['id'] = key.split(':')[1]
                records.append(data)
            
            # Sort by changed_at, falling back to created_at
            records.sort(key=lambda x: x.get('changed_at', x.get('created_at', 0)), reverse=True)
            total = len(records)
            
            # Debug logging
            current_app.logger.debug(f"Found {len(records)} total records")
            current_app.logger.debug("Records before pagination: %s", json.dumps(records, indent=2))
            
            # Apply pagination
            start = (page - 1) * per_page
            end = start + per_page
            paginated_records = records[start:end]
            
            current_app.logger.debug("Records after pagination: %s", json.dumps(paginated_records, indent=2))
            
            result = {
                'records': paginated_records,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
            current_app.logger.debug("Returning result: %s", json.dumps(result, indent=2))
            return result
        except Exception as e:
            current_app.logger.error(f"Error getting records: {e}")
            return {'records': [], 'total': 0, 'pages': 0}

    def search_records(self, query: str, creator_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search records with Boolean AND and quoted string support"""
        try:
            # Get all records
            keys = self.client.keys('record:*')
            records = []
            
            # Parse search terms, respecting quotes
            terms = []
            current_term = []
            in_quotes = False
            quote_char = None
            
            # Split query into terms, preserving quoted strings
            for char in query:
                if char in ['"', "'"]:
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif quote_char == char:
                        in_quotes = False
                        if current_term:
                            terms.append(''.join(current_term).lower())
                            current_term = []
                    else:
                        current_term.append(char)
                elif char.isspace() and not in_quotes:
                    if current_term:
                        terms.append(''.join(current_term).lower())
                        current_term = []
                else:
                    current_term.append(char)
            
            if current_term:
                terms.append(''.join(current_term).lower())
            
            # Remove empty terms
            terms = [term for term in terms if term]
            
            for key in keys:
                try:
                    data = self.client.json().get(key, Path.root_path())
                    if isinstance(data, list):
                        data = data[0]
                    
                    # Filter by creator_id if specified
                    if creator_id and data.get('creator_id') != creator_id:
                        continue
                    
                    # Boolean AND search in title and description
                    if terms:
                        title = str(data.get('title', '')).lower()
                        description = str(data.get('description', '')).lower()
                        searchable_text = f"{title} {description}"
                        
                        # All terms must match for the record to be included
                        if not all(term in searchable_text for term in terms):
                            continue
                    
                    data['id'] = key.split(':')[1]
                    records.append(data)
                except Exception as e:
                    current_app.logger.error(f"Error processing record {key}: {e}")
                    continue
                    
            # Sort by created_at
            records.sort(key=lambda x: x.get('created_at', 0), reverse=True)
            
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
            # Only set created_at for new records
            if not self.client.exists(key):
                # Store UTC timestamp without timezone offset for new records
                now = datetime.now(timezone.utc)
                data['created_at'] = int(now.timestamp())
                data['changed_at'] = int(now.timestamp())
            else:
                # Remove created_at if it was sent in update
                data.pop('created_at', None)
                # Always update changed_at on modifications
                data['changed_at'] = int(datetime.now(timezone.utc).timestamp())
            
            # Convert ISO timestamps to UTC Unix timestamps
            for field in ['time_start', 'time_end']:
                if data.get(field):
                    # Parse ISO string to datetime
                    dt = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    # Ensure UTC
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    # Convert to UTC timestamp
                    data[field] = int(dt.timestamp())
            
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

