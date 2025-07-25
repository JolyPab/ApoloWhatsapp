import redis
import logging
import json
from config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        try:
            self.r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                username=settings.REDIS_USERNAME,
                decode_responses=True,
                ssl=True
            )
            self.r.ping()
            logger.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to Redis: {e}. The bot will run without session memory and deduplication.")
            self.r = None

    def is_duplicate(self, message_sid: str) -> bool:
        """Checks if a message SID has been processed."""
        if not self.r:
            return False
        if self.r.exists(message_sid):
            logger.info(f"Duplicate message SID received: {message_sid}. Ignoring.")
            return True
        self.r.set(message_sid, "processed", ex=3600) # Expire after 1 hour
        return False

    def get_session_history(self, session_id: str) -> list:
        """Retrieves session history from Redis."""
        if not self.r:
            return []
        try:
            history_json = self.r.get(session_id)
            if history_json:
                return json.loads(history_json)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Could not decode session history for {session_id}: {e}. Starting new session.")
        return []

    def save_session_history(self, session_id: str, history: list):
        """Saves session history to Redis."""
        if not self.r:
            return
        try:
            self.r.set(session_id, json.dumps(history))
        except TypeError as e:
            logger.error(f"Failed to serialize session history for {session_id}: {e}")

# Singleton instance
redis_client = RedisClient() 