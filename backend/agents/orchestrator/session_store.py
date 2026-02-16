# backend/agents/orchestrator/session_store.py

import json
import uuid
import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

import redis
from redis.connection import ConnectionPool

from backend.config import get_settings


class ConversationStore(ABC):
    """Abstract base class for conversation storage"""

    @abstractmethod
    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session state by session_id"""
        pass

    @abstractmethod
    def save_state(self, session_id: str, state: Dict[str, Any]):
        """Save session state"""
        pass

    @abstractmethod
    def delete_state(self, session_id: str):
        """Delete session state"""
        pass

    @abstractmethod
    def create_new_session_id(self) -> str:
        """Generate a new unique session ID"""
        pass


class InMemoryConversationStore(ConversationStore):
    """
    In-memory session store using Python dict.

    WARNING: All sessions are lost on server restart.
    Use only for development/testing.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(session_id)

    def save_state(self, session_id: str, state: Dict[str, Any]):
        self._store[session_id] = state

    def delete_state(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]

    def create_new_session_id(self) -> str:
        return str(uuid.uuid4())


class RedisConversationStore(ConversationStore):
    """
    Redis-based session store with automatic expiration.

    Features:
    - Persistent storage across server restarts
    - Automatic session TTL (time-to-live)
    - Connection pooling for performance
    - JSON serialization for complex state
    """

    def __init__(self, settings=None):
        if settings is None:
            settings = get_settings()

        self.settings = settings
        self.ttl = settings.session_ttl  # seconds

        # Initialize Redis connection
        try:
            if settings.redis_url:
                # Use redis_url if provided (e.g., for cloud services)
                self.redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    encoding='utf-8'
                )
            else:
                # Use individual connection parameters
                pool = ConnectionPool(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password if settings.redis_password else None,
                    db=settings.redis_db,
                    ssl=settings.redis_ssl,
                    decode_responses=True,
                    encoding='utf-8',
                    max_connections=10
                )
                self.redis_client = redis.Redis(connection_pool=pool)

            # Test connection
            self.redis_client.ping()
            print(f"✅ Redis connection established (TTL: {self.ttl}s)")

        except redis.ConnectionError as e:
            print(f"❌ Redis connection failed: {e}")
            print("⚠️ Falling back to InMemoryConversationStore")
            raise

    def _make_key(self, session_id: str) -> str:
        """Create Redis key with namespace prefix"""
        return f"session:{session_id}"

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            key = self._make_key(session_id)
            data = self.redis_client.get(key)

            if data is None:
                return None

            # Deserialize JSON
            state = json.loads(data)
            return state

        except redis.RedisError as e:
            print(f"Redis get_state error for {session_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error for session {session_id}: {e}")
            return None

    def save_state(self, session_id: str, state: Dict[str, Any]):
        try:
            key = self._make_key(session_id)

            # Serialize to JSON
            data = json.dumps(state, ensure_ascii=False)

            # Save with TTL
            self.redis_client.setex(
                name=key,
                time=self.ttl,
                value=data
            )

        except redis.RedisError as e:
            print(f"Redis save_state error for {session_id}: {e}")
        except (TypeError, ValueError) as e:
            print(f"JSON encode error for session {session_id}: {e}")

    def delete_state(self, session_id: str):
        try:
            key = self._make_key(session_id)
            self.redis_client.delete(key)

        except redis.RedisError as e:
            print(f"Redis delete_state error for {session_id}: {e}")

    def create_new_session_id(self) -> str:
        return str(uuid.uuid4())

    def extend_ttl(self, session_id: str):
        """
        Extend the TTL of an existing session.
        Useful for keeping active sessions alive.
        """
        try:
            key = self._make_key(session_id)
            self.redis_client.expire(key, self.ttl)
        except redis.RedisError as e:
            print(f"Redis extend_ttl error for {session_id}: {e}")

    def get_all_session_ids(self) -> list[str]:
        """
        Get all active session IDs.
        WARNING: Use with caution in production (can be slow with many sessions).
        """
        try:
            keys = self.redis_client.keys("session:*")
            return [key.replace("session:", "") for key in keys]
        except redis.RedisError as e:
            print(f"Redis get_all_session_ids error: {e}")
            return []


def create_conversation_store() -> ConversationStore:
    """
    Factory function to create the appropriate conversation store.

    Returns:
        - RedisConversationStore if use_redis_session=True and Redis is available
        - InMemoryConversationStore otherwise (fallback for dev/testing)
    """
    settings = get_settings()

    if settings.use_redis_session:
        try:
            store = RedisConversationStore(settings)
            print("🚀 Using RedisConversationStore for session management")
            return store
        except Exception as e:
            print(f"⚠️ Failed to initialize Redis: {e}")
            print("🔄 Falling back to InMemoryConversationStore")

    print("💾 Using InMemoryConversationStore (development mode)")
    return InMemoryConversationStore()
