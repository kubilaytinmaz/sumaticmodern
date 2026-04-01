"""
Sumatic Modern IoT - Redis Client
Async Redis connection with cache utility methods.
"""
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Redis connection pool
redis_pool: Optional[aioredis.ConnectionPool] = None
redis_client: Optional[aioredis.Redis] = None
_redis_available: Optional[bool] = None  # None = not checked yet


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get or create the Redis client instance.
    
    Returns:
        Async Redis client, or None if Redis is unavailable
    """
    global redis_client, redis_pool, _redis_available
    
    # If we already know Redis is unavailable, return None immediately
    if _redis_available is False:
        return None
    
    if redis_client is None:
        try:
            redis_pool = aioredis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=2,  # 2 second connect timeout
                socket_timeout=2,           # 2 second operation timeout
            )
            redis_client = aioredis.Redis(connection_pool=redis_pool)
            # Test the connection
            await redis_client.ping()
            _redis_available = True
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Running without Redis cache.")
            _redis_available = False
            redis_client = None
            if redis_pool is not None:
                try:
                    await redis_pool.disconnect()
                except Exception:
                    pass
                redis_pool = None
            return None
    
    return redis_client


async def close_redis() -> None:
    """Close Redis connection pool on shutdown."""
    global redis_client, redis_pool
    
    if redis_client is not None:
        await redis_client.close()
        redis_client = None
    
    if redis_pool is not None:
        await redis_pool.disconnect()
        redis_pool = None


# ─── Cache Utilities ───────────────────────────────────────────────────


async def cache_get(key: str) -> Optional[str]:
    """
    Get a value from Redis cache.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found or Redis unavailable
    """
    try:
        client = await get_redis()
        if client is None:
            return None
        return await client.get(key)
    except Exception:
        # Redis unavailable - return None gracefully
        return None


async def cache_set(
    key: str,
    value: str,
    expire_seconds: int = 300,
) -> bool:
    """
    Set a value in Redis cache with expiration.
    
    Args:
        key: Cache key
        value: Value to cache
        expire_seconds: TTL in seconds (default: 5 minutes)
        
    Returns:
        True if set successfully, False if Redis unavailable
    """
    try:
        client = await get_redis()
        if client is None:
            return False
        return await client.set(key, value, ex=expire_seconds)
    except Exception:
        # Redis unavailable - return False gracefully
        return False


async def cache_delete(key: str) -> int:
    """
    Delete a key from Redis cache.
    
    Args:
        key: Cache key to delete
        
    Returns:
        Number of keys deleted (0 or 1, or 0 if Redis unavailable)
    """
    try:
        client = await get_redis()
        if client is None:
            return 0
        return await client.delete(key)
    except Exception:
        # Redis unavailable - return 0 gracefully
        return 0


async def cache_exists(key: str) -> bool:
    """
    Check if a key exists in Redis cache.
    
    Args:
        key: Cache key
        
    Returns:
        True if key exists, False if not or Redis unavailable
    """
    try:
        client = await get_redis()
        if client is None:
            return False
        return bool(await client.exists(key))
    except Exception:
        # Redis unavailable - return False gracefully
        return False


async def cache_set_json(
    key: str,
    data: dict,
    expire_seconds: int = 300,
) -> bool:
    """
    Set a JSON-serializable dict in Redis cache.
    
    Args:
        key: Cache key
        data: Dictionary to cache
        expire_seconds: TTL in seconds (default: 5 minutes)
        
    Returns:
        True if set successfully
    """
    import json
    value = json.dumps(data, default=str)
    return await cache_set(key, value, expire_seconds)


async def cache_get_json(key: str) -> Optional[dict]:
    """
    Get a JSON object from Redis cache.
    
    Args:
        key: Cache key
        
    Returns:
        Parsed dictionary or None if not found or Redis unavailable
    """
    import json
    try:
        value = await cache_get(key)
        if value is None:
            return None
        return json.loads(value)
    except (json.JSONDecodeError, Exception):
        # Invalid JSON or Redis unavailable - return None gracefully
        return None


async def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.
    
    Args:
        pattern: Glob-style pattern (e.g., 'device:*')
        
    Returns:
        Number of keys deleted (0 if Redis unavailable)
    """
    try:
        client = await get_redis()
        if client is None:
            return 0
        deleted = 0
        async for key in client.scan_iter(match=pattern):
            deleted += await client.delete(key)
        return deleted
    except Exception:
        # Redis unavailable - return 0 gracefully
        return 0


# ─── Token Blacklist ───────────────────────────────────────────────────


async def blacklist_token(jti: str, expire_seconds: int = 86400) -> bool:
    """
    Add a JWT token ID to the blacklist.
    
    Args:
        jti: JWT token ID
        expire_seconds: TTL in seconds (default: 24 hours)
        
    Returns:
        True if blacklisted successfully
    """
    key = f"token_blacklist:{jti}"
    return await cache_set(key, "1", expire_seconds)


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a JWT token ID is blacklisted.
    
    Args:
        jti: JWT token ID
        
    Returns:
        True if token is blacklisted, False if not or Redis unavailable
    """
    try:
        key = f"token_blacklist:{jti}"
        return await cache_exists(key)
    except Exception:
        # Redis unavailable - treat as not blacklisted
        return False


# ─── Device Real-time Cache ───────────────────────────────────────────


async def cache_device_reading(device_id: int, reading: dict) -> bool:
    """
    Cache the latest device reading for real-time access.
    
    Args:
        device_id: Device ID
        reading: Reading data to cache
        
    Returns:
        True if cached successfully
    """
    key = f"device:reading:latest:{device_id}"
    return await cache_set_json(key, reading, expire_seconds=600)


async def get_cached_device_reading(device_id: int) -> Optional[dict]:
    """
    Get the cached latest reading for a device.
    
    Args:
        device_id: Device ID
        
    Returns:
        Cached reading data or None
    """
    key = f"device:reading:latest:{device_id}"
    return await cache_get_json(key)
