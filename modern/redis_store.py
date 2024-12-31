import redis
import os
from typing import Optional
from flask import current_app

redis_client: Optional[redis.Redis] = None

def init_redis(app=None):
    """Initialize Redis connection"""
    global redis_client
    try:
        if redis_client is None:
            redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                health_check_interval=5
            )
            # Test the connection
            redis_client.ping()
            if app:
                app.logger.info("Redis connection established successfully")
    except redis.ConnectionError as e:
        error_msg = f"Redis connection failed: {e}"
        if app:
            app.logger.error(error_msg)
        else:
            print(f" * {error_msg}")
        redis_client = None
    return redis_client

def get_redis():
    """Get Redis client with connection check"""
    global redis_client
    if redis_client is None:
        return init_redis(current_app._get_current_object() if current_app else None)
    try:
        redis_client.ping()
        return redis_client
    except redis.ConnectionError:
        return init_redis(current_app._get_current_object() if current_app else None)
