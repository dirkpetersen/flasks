import os
from typing import Dict, Any

def parse_meta_fields() -> Dict[str, Any]:
    """Parse META_SEL and META_MSEL environment variables"""
    meta_fields: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(('META_SEL_', 'META_MSEL_')):
            field_name, options = value.split(':', 1)
            field_id = field_name.lower().replace(' ', '_')
            meta_fields[field_id] = {
                'name': field_name,
                'options': options.split(','),
                'multiple': key.startswith('META_MSEL_'),
                'id': field_id
            }
    return meta_fields
