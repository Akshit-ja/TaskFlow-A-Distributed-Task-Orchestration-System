"""
Redis client configuration and utilities.
"""

import logging
import json
from typing import Any, Optional, Dict, List
import redis.asyncio as redis
from redis.exceptions import RedisError

from src.core.config import get_settings, get_redis_config

# Setup logging
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()
redis_config = get_redis_config()


class RedisClient:
    """Redis client wrapper with utilities for task queue operations."""
    
    def __init__(self):
        """Initialize Redis client."""
        self._client: Optional[redis.Redis] = None
    
    async def connect(self) -> redis.Redis:
        """
        Get or create Redis connection.
        
        Returns:
            redis.Redis: Redis client instance
        """
        if self._client is None:
            try:
                self._client = redis.from_url(
                    redis_config["url"],
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self._client.ping()
                logger.info("Connected to Redis successfully")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise
        
        return self._client
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if Redis is healthy.
        
        Returns:
            bool: True if Redis is healthy
        """
        try:
            client = await self.connect()
            await client.ping()
            return True
        except RedisError:
            return False
    
    async def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set JSON value in Redis.
        
        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            expire: Expiration time in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            client = await self.connect()
            json_value = json.dumps(value)
            result = await client.set(key, json_value, ex=expire)
            return result is True
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Failed to set JSON value for key {key}: {e}")
            return False
    
    async def get_json(self, key: str, default: Any = None) -> Any:
        """
        Get JSON value from Redis.
        
        Args:
            key: Redis key
            default: Default value if key doesn't exist
            
        Returns:
            Any: Deserialized JSON value or default
        """
        try:
            client = await self.connect()
            value = await client.get(key)
            if value is None:
                return default
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get JSON value for key {key}: {e}")
            return default
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.
        
        Args:
            keys: Keys to delete
            
        Returns:
            int: Number of keys deleted
        """
        try:
            client = await self.connect()
            return await client.delete(*keys)
        except RedisError as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        try:
            client = await self.connect()
            return await client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    async def lpush(self, key: str, *values: str) -> int:
        """
        Push values to the left of a list.
        
        Args:
            key: Redis key
            values: Values to push
            
        Returns:
            int: Length of list after push
        """
        try:
            client = await self.connect()
            return await client.lpush(key, *values)
        except RedisError as e:
            logger.error(f"Failed to lpush to key {key}: {e}")
            return 0
    
    async def rpop(self, key: str) -> Optional[str]:
        """
        Pop value from the right of a list.
        
        Args:
            key: Redis key
            
        Returns:
            Optional[str]: Popped value or None
        """
        try:
            client = await self.connect()
            return await client.rpop(key)
        except RedisError as e:
            logger.error(f"Failed to rpop from key {key}: {e}")
            return None
    
    async def llen(self, key: str) -> int:
        """
        Get length of a list.
        
        Args:
            key: Redis key
            
        Returns:
            int: Length of list
        """
        try:
            client = await self.connect()
            return await client.llen(key)
        except RedisError as e:
            logger.error(f"Failed to get length of key {key}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Get Redis client instance.
    
    Returns:
        RedisClient: Redis client instance
    """
    return redis_client