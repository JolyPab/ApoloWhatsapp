import redis
import logging
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
            logger.error(f"Could not connect to Redis: {e}. The bot will run without deduplication.")
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

# Singleton instance
redis_client = RedisClient() 