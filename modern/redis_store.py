import redis
import os
from typing import Optional

redis_client: Optional[redis.Redis] = None

def init_redis(app=None):
    """Initialize Redis connection"""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
    return redis_client
