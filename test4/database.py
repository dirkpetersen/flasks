from typing import Optional, Dict, List, Any, Union
import random
import string
import time
import json
from datetime import datetime, timezone
import redis
from redis.commands.json.path import Path
from flask import current_app

records_per_page = 7

class RedisDB:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host=None, port=None, db=None):
        if not hasattr(self, 'client'):
            # Use parameters if provided, otherwise get from Flask config
            if host is None or port is None:
                from flask import current_app
                host = current_app.config['REDIS_HOST']
                port = current_app.config['REDIS_PORT']
                db = current_app.config.get('REDIS_DB', 0)
            
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True
            )
            
            # Only log if we have an application context
            try:
                from flask import current_app
                current_app.logger.debug("Redis client initialized")
            except RuntimeError:
                print("Redis client initialized")


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
                       page: int = 1, per_page: int = records_per_page,
                       show_all: bool = False) -> Dict[str, Any]:
        """Get paginated records, optionally filtered by creator"""
        try:
            # Get all records
            keys = self.client.keys('record:*')
            records = []
            
            for key in keys:
                data = self.client.json().get(key, Path.root_path())
                if isinstance(data, list):
                    data = data[0]
                
                # Filter by creator_id and public flag
                if not show_all and creator_id:
                    # Show only user's records when not showing all
                    if data.get('creator_id') != creator_id:
                        continue
                else:
                    # When showing all records, show all public ones and user's private ones
                    if data.get('public') is False and data.get('creator_id') != creator_id:
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

    def search_records(self, query: str, creator_id: Optional[str] = None, 
                      show_all: bool = False) -> List[Dict[str, Any]]:
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
                    
                    # Filter by creator_id and public flag
                    if not show_all and creator_id:
                        # Show only user's records when not showing all
                        if data.get('creator_id') != creator_id:
                            continue
                    else:
                        # When showing all records, show all public ones and user's private ones
                        if data.get('public') is False and data.get('creator_id') != creator_id:
                            continue
                    
                    # Boolean AND search in title and description
                    if terms:
                        # Include all fields in search
                        searchable_parts = [
                            str(data.get('title', '')),
                            str(data.get('description', '')),
                            str(data.get('access_control_by', '')),
                            str(data.get('id', '')),
                            str(data.get('creator_id', ''))
                        ]
                        
                        # Add all meta field values to searchable text
                        if data.get('meta'):
                            for meta_value in data['meta'].values():
                                if isinstance(meta_value, list):
                                    searchable_parts.extend(str(v) for v in meta_value)
                                else:
                                    searchable_parts.append(str(meta_value))
                        
                        searchable_text = ' '.join(searchable_parts).lower()
                        
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
            
            # Return only the first N records
            return records[:records_per_page]
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
            
            # Handle time fields - they should already be UTC timestamps from frontend
            for field in ['time_start', 'time_end']:
                if data.get(field):
                    # Ensure the value is an integer
                    try:
                        data[field] = int(data[field])
                    except (TypeError, ValueError) as e:
                        raise ValueError(f"Invalid timestamp for {field}: {data[field]}")
            
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

    def get_public_record_ids(self) -> List[str]:
        """Get IDs of all public records"""
        keys = self.client.keys('record:*')
        public_ids = []
        for key in keys:
            try:
                data = self.client.json().get(key, Path.root_path())
                if isinstance(data, list):
                    data = data[0]
                if data.get('public', False):
                    record_id = key.split(':')[1]
                    public_ids.append(record_id)
            except Exception as e:
                current_app.logger.error(f"Error processing record {key}: {e}")
                continue
        return sorted(public_ids)

    def get_public_record(self, partial_id: str) -> Optional[Dict[str, Any]]:
        """Get a public record by ID or partial ID"""
        try:
            # Convert partial_id to uppercase for consistency
            partial_id = partial_id.upper()
            
            # If partial ID provided, try to match against pattern
            if '-' not in partial_id:
                pattern = current_app.config['WORK_ID_PATTERN']
                x_positions = [i for i, char in enumerate(pattern) if char == 'X']
                if len(partial_id) == len(x_positions):
                    # Reconstruct full ID using pattern
                    id_chars = list(pattern)
                    for pos, char in zip(x_positions, partial_id):
                        id_chars[pos] = char
                    full_id = ''.join(id_chars)
                else:
                    return None
            else:
                full_id = partial_id

            # Get record data
            key = f'record:{full_id}'
            data = self.client.json().get(key, Path.root_path())
            if data:
                if isinstance(data, list):
                    data = data[0]
                # Only return if record is public
                if data.get('public', False):
                    data['id'] = full_id
                    return data
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting public record: {e}")
            return None

