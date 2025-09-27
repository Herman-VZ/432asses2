import redis
import json
import os
import logging

logger = logging.getLogger(__name__)

class RedisHelper:
    def __init__(self):
        # Use environment variables from your .env file
        redis_host = os.environ.get('REDIS_HOST', 'localhost')  # Will come from .env
        redis_port = int(os.environ.get('REDIS_PORT', 6379))
        redis_password = os.environ.get('REDIS_PASSWORD', None)
        
        logger.info(f"🔗 Attempting Redis connection to {redis_host}:{redis_port}")
        
        try:
            connection_params = {
                'host': redis_host,
                'port': redis_port,
                'decode_responses': True,
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True
            }
            
            if redis_password:
                connection_params['password'] = redis_password
            
            self.redis_client = redis.Redis(**connection_params)
            self.redis_client.ping()
            logger.info(f"✅ Redis connected to {redis_host}:{redis_port}")
            
        except Exception as e:
            self.redis_client = None
            logger.warning(f"❌ Redis unavailable: {e}")
    
    def cache_get(self, key):
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(key)
            return json.loads(cached) if cached else None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def cache_set(self, key, data, expire=300):
        if not self.redis_client:
            return False
        try:
            self.redis_client.setex(key, expire, json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

redis_helper = RedisHelper()