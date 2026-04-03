"""
Redis service for short-term memory and real-time communication
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

import aioredis
from aioredis.client import PubSub

from src.config.settings import settings


class RedisService:
    """Service for interacting with Redis for caching, pub/sub, and short-term memory."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.logger = logging.getLogger(__name__)
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection to Redis."""
        async with self._connection_lock:
            if self.redis is None or self.redis.closed:
                try:
                    # Create Redis connection
                    redis_url = f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

                    self.redis = aioredis.from_url(
                        redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                        max_connections=20
                    )

                    # Test connection
                    await self.redis.ping()
                    self.logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

                    # Initialize pub/sub
                    self.pubsub = self.redis.pubsub()

                except Exception as e:
                    self.logger.error(f"Failed to connect to Redis: {str(e)}")
                    raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        async with self._connection_lock:
            if self.pubsub:
                await self.pubsub.close()
                self.pubsub = None

            if self.redis and not self.redis.closed:
                await self.redis.close()
                self.logger.info("Redis connection closed")

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        try:
            if not self.redis or self.redis.closed:
                return {"status": "disconnected", "error": "No active connection"}

            # Test basic operations
            await self.redis.ping()
            memory_info = await self.redis.info("memory")

            return {
                "status": "healthy",
                "connected": True,
                "memory_used": memory_info.get("used_memory_human", "unknown"),
                "connected_clients": memory_info.get("connected_clients", "unknown")
            }

        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    # Key-Value Operations with Secondary Cache
    async def set_value(self, key: str, value: Any, ttl: Optional[int] = None,
                       research_topic: Optional[str] = None) -> bool:
        """Set a value in Redis with optional TTL and research topic indexing."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            elif not isinstance(value, str):
                value = str(value)

            # Set primary value
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)

            # Create secondary cache index if research topic provided
            if research_topic and ttl:
                await self._update_research_topic_index(research_topic, key, ttl)

            return True

        except Exception as e:
            self.logger.error(f"Failed to set value for key {key}: {str(e)}")
            return False

    async def get_value(self, key: str, default: Any = None,
                       research_topic: Optional[str] = None) -> Any:
        """Get a value from Redis with secondary cache lookup."""
        try:
            # Check if this is a research result that might be cached by topic
            if research_topic and key.startswith("task:"):
                cached_result = await self._get_cached_by_topic(research_topic, key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for research topic {research_topic}")
                    return cached_result

            # Standard lookup
            value = await self.redis.get(key)

            if value is None:
                return default

            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        except Exception as e:
            self.logger.error(f"Failed to get value for key {key}: {str(e)}")
            return default

    async def delete_key(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete key {key}: {str(e)}")
            return False

    # Hash Operations
    async def set_hash(self, key: str, field_values: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set hash field-value pairs."""
        try:
            # Convert values to JSON if needed
            processed_values = {}
            for field, value in field_values.items():
                if isinstance(value, (dict, list)):
                    processed_values[field] = json.dumps(value, default=str)
                else:
                    processed_values[field] = str(value)

            await self.redis.hset(key, mapping=processed_values)

            if ttl:
                await self.redis.expire(key, ttl)

            return True

        except Exception as e:
            self.logger.error(f"Failed to set hash {key}: {str(e)}")
            return False

    async def get_hash(self, key: str, field: Optional[str] = None) -> Dict[str, Any]:
        """Get hash field(s) from Redis."""
        try:
            if field:
                value = await self.redis.hget(key, field)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
                return None
            else:
                hash_data = await self.redis.hgetall(key)
                result = {}
                for k, v in hash_data.items():
                    try:
                        result[k] = json.loads(v)
                    except json.JSONDecodeError:
                        result[k] = v
                return result

        except Exception as e:
            self.logger.error(f"Failed to get hash {key}: {str(e)}")
            return {}

    # List Operations
    async def push_to_list(self, key: str, value: Any, max_length: Optional[int] = None) -> bool:
        """Push value to list with optional max length."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            else:
                value = str(value)

            await self.redis.lpush(key, value)

            if max_length:
                await self.redis.ltrim(key, 0, max_length - 1)

            return True

        except Exception as e:
            self.logger.error(f"Failed to push to list {key}: {str(e)}")
            return False

    async def get_list(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get list values from Redis."""
        try:
            values = await self.redis.lrange(key, start, end)
            result = []

            for value in values:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)

            return result

        except Exception as e:
            self.logger.error(f"Failed to get list {key}: {str(e)}")
            return []

    # Pub/Sub Operations
    async def publish(self, channel: str, message: Union[str, Dict]) -> int:
        """Publish message to a channel."""
        try:
            if isinstance(message, dict):
                message = json.dumps(message, default=str)

            return await self.redis.publish(channel, message)

        except Exception as e:
            self.logger.error(f"Failed to publish to channel {channel}: {str(e)}")
            return 0

    async def subscribe(self, channel: str, callback) -> None:
        """Subscribe to a channel with callback."""
        try:
            await self.pubsub.subscribe(**{channel: callback})
            self.logger.info(f"Subscribed to channel: {channel}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to channel {channel}: {str(e)}")
            raise

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        try:
            await self.pubsub.unsubscribe(channel)
            self.logger.info(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from channel {channel}: {str(e)}")

    async def listen(self) -> None:
        """Start listening for pub/sub messages."""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    self.logger.debug(f"Received message on {message['channel']}: {message['data']}")
        except Exception as e:
            self.logger.error(f"Error in pub/sub listener: {str(e)}")

    # Memory Management Operations
    async def store_conversation_turn(self, task_id: str, turn_data: Dict[str, Any]) -> bool:
        """Store a conversation turn in Redis."""
        try:
            key = f"task:{task_id}:conversation_turns"
            turn_data['timestamp'] = turn_data.get('timestamp', asyncio.get_event_loop().time())

            await self.push_to_list(key, turn_data, max_length=100)
            return True

        except Exception as e:
            self.logger.error(f"Failed to store conversation turn for task {task_id}: {str(e)}")
            return False

    async def get_conversation_history(self, task_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for a task."""
        try:
            key = f"task:{task_id}:conversation_turns"
            return await self.get_list(key, 0, limit - 1)

        except Exception as e:
            self.logger.error(f"Failed to get conversation history for task {task_id}: {str(e)}")
            return []

    async def store_agent_state(self, task_id: str, agent_name: str, state: Dict[str, Any]) -> bool:
        """Store agent state in Redis."""
        try:
            key = f"task:{task_id}:agent_state:{agent_name}"
            state['updated_at'] = asyncio.get_event_loop().time()

            await self.set_value(key, state, ttl=settings.SHORT_TERM_MEMORY_TTL)
            return True

        except Exception as e:
            self.logger.error(f"Failed to store agent state for {agent_name}: {str(e)}")
            return False

    async def get_agent_state(self, task_id: str, agent_name: str) -> Dict[str, Any]:
        """Get agent state from Redis."""
        try:
            key = f"task:{task_id}:agent_state:{agent_name}"
            return await self.get_value(key, {})

        except Exception as e:
            self.logger.error(f"Failed to get agent state for {agent_name}: {str(e)}")
            return {}

    # Task Management Operations
    async def create_task_session(self, task_id: str, user_id: str, task_data: Dict[str, Any]) -> bool:
        """Create a new task session in Redis."""
        try:
            session_key = f"task_session:{task_id}"
            session_data = {
                "task_id": task_id,
                "user_id": user_id,
                "created_at": asyncio.get_event_loop().time(),
                "status": "created",
                "data": task_data
            }

            await self.set_value(session_key, session_data, ttl=86400)  # 24 hours
            return True

        except Exception as e:
            self.logger.error(f"Failed to create task session {task_id}: {str(e)}")
            return False

    async def update_task_status(self, task_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
        """Update task status in Redis."""
        try:
            session_key = f"task_session:{task_id}"
            current_data = await self.get_value(session_key, {})

            current_data["status"] = status
            current_data["updated_at"] = asyncio.get_event_loop().time()

            if metadata:
                current_data["metadata"] = {**current_data.get("metadata", {}), **metadata}

            await self.set_value(session_key, current_data, ttl=86400)
            return True

        except Exception as e:
            self.logger.error(f"Failed to update task status {task_id}: {str(e)}")
            return False

    async def get_task_session(self, task_id: str) -> Dict[str, Any]:
        """Get task session data from Redis."""
        try:
            session_key = f"task_session:{task_id}"
            return await self.get_value(session_key, {})

        except Exception as e:
            self.logger.error(f"Failed to get task session {task_id}: {str(e)}")
            return {}

    # Utility Operations
    async def increment_counter(self, key: str, amount: int = 1) -> int:
        """Increment a counter in Redis."""
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            self.logger.error(f"Failed to increment counter {key}: {str(e)}")
            return 0

    async def expire_key(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key."""
        try:
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set expiration for key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            self.logger.error(f"Failed to check existence of key {key}: {str(e)}")
            return False

    async def get_keys_pattern(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern."""
        try:
            return await self.redis.keys(pattern)
        except Exception as e:
            self.logger.error(f"Failed to get keys with pattern {pattern}: {str(e)}")
            return []

    async def flush_database(self) -> bool:
        """Flush the current Redis database. Use with caution!"""
        try:
            await self.redis.flushdb()
            self.logger.warning("Redis database flushed")
            return True
        except Exception as e:
            self.logger.error(f"Failed to flush database: {str(e)}")
            return False

    # Secondary Cache Operations for Research Topics
    async def _update_research_topic_index(self, research_topic: str, key: str, ttl: int) -> None:
        """Update the research topic index for secondary caching."""
        try:
            # Normalize research topic for indexing
            topic_hash = self._hash_research_topic(research_topic)
            index_key = f"research_topic_index:{topic_hash}"

            # Add key to topic index
            await self.redis.sadd(index_key, key)

            # Set expiration on index (slightly longer than the actual data)
            await self.redis.expire(index_key, ttl + 300)  # 5 minutes buffer

        except Exception as e:
            self.logger.error(f"Failed to update research topic index: {str(e)}")

    async def _get_cached_by_topic(self, research_topic: str, original_key: str) -> Optional[Any]:
        """Check for cached results by research topic."""
        try:
            topic_hash = self._hash_research_topic(research_topic)
            index_key = f"research_topic_index:{topic_hash}"

            # Check if we have cached results for this topic
            cached_keys = await self.redis.smembers(index_key)

            if not cached_keys:
                return None

            # Look for exact match first
            if original_key in cached_keys:
                value = await self.redis.get(original_key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value

            # If no exact match, check for similar tasks with same research topic
            for cached_key in cached_keys:
                if cached_key != original_key and cached_key.startswith("task:"):
                    # Check if this cached result is still valid and relevant
                    cached_value = await self.redis.get(cached_key)
                    if cached_value:
                        try:
                            parsed_value = json.loads(cached_value)
                            # Verify it's a complete research result
                            if self._is_complete_research_result(parsed_value):
                                self.logger.info(f"Found similar cached result for topic {research_topic}")
                                return parsed_value
                        except json.JSONDecodeError:
                            continue

            return None

        except Exception as e:
            self.logger.error(f"Failed to get cached result by topic: {str(e)}")
            return None

    def _hash_research_topic(self, research_topic: str) -> str:
        """Create a hash of the research topic for indexing."""
        import hashlib

        # Normalize topic for consistent hashing
        normalized = research_topic.lower().strip()

        # Remove common stop words for better matching
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        words = normalized.split()
        filtered_words = [word for word in words if word not in stop_words]
        normalized = " ".join(filtered_words)

        # Create hash
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _is_complete_research_result(self, value: Any) -> bool:
        """Check if a cached value represents a complete research result."""
        if not isinstance(value, dict):
            return False

        # Check for indicators of a complete research result
        required_keys = ["final_report", "completed_at", "status"]
        has_required = all(key in value for key in required_keys)

        if has_required and value.get("status") == "completed":
            return True

        return False

    async def get_research_topic_cache_stats(self, research_topic: str) -> Dict[str, Any]:
        """Get statistics about cached results for a research topic."""
        try:
            topic_hash = self._hash_research_topic(research_topic)
            index_key = f"research_topic_index:{topic_hash}"

            cached_keys = await self.redis.smembers(index_key)
            stats = {
                "topic": research_topic,
                "topic_hash": topic_hash,
                "cached_items": len(cached_keys),
                "valid_results": 0,
                "expired_items": 0
            }

            for key in cached_keys:
                if await self.redis.exists(key):
                    value = await self.redis.get(key)
                    if value and self._is_complete_research_result(json.loads(value)):
                        stats["valid_results"] += 1
                else:
                    stats["expired_items"] += 1

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get cache stats for topic {research_topic}: {str(e)}")
            return {"error": str(e)}

    async def invalidate_topic_cache(self, research_topic: str) -> bool:
        """Invalidate all cached results for a research topic."""
        try:
            topic_hash = self._hash_research_topic(research_topic)
            index_key = f"research_topic_index:{topic_hash}"

            # Get all keys for this topic
            cached_keys = await self.redis.smembers(index_key)

            # Delete all cached values
            if cached_keys:
                await self.redis.delete(*cached_keys)

            # Delete the index itself
            await self.redis.delete(index_key)

            self.logger.info(f"Invalidated cache for research topic: {research_topic}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to invalidate cache for topic {research_topic}: {str(e)}")
            return False