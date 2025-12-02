"""
Utility module for Redis pub/sub operations.

Provides helpers for publishing and subscribing to Redis channels
for real-time data streaming (e.g., SSE).
"""

import json
import logging
from typing import Generator

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


def get_redis_client() -> redis.Redis:
    """
    Get Redis client from Celery broker URL.

    Returns:
        Redis client instance
    """
    broker_url = settings.CELERY_BROKER_URL
    return redis.from_url(broker_url, decode_responses=True)


def publish_to_channel(channel: str, data: dict) -> None:
    """
    Publish data to a Redis channel.

    Args:
        channel: Redis channel name
        data: Data dictionary to publish (will be JSON serialized)
    """
    try:
        client = get_redis_client()
        message = json.dumps(data)
        client.publish(channel, message)
        logger.debug(f"Published to channel {channel}: {data.get('type')}")
    except Exception as e:
        logger.error(f"Failed to publish to channel {channel}: {e}")


def subscribe_to_channel(channel: str, timeout: int = 300) -> Generator[dict, None, None]:
    """
    Subscribe to a Redis channel and yield messages.

    Args:
        channel: Redis channel name
        timeout: Timeout in seconds for waiting for messages

    Yields:
        Dictionaries of deserialized JSON messages
    """
    client = get_redis_client()
    pubsub = client.pubsub()
    pubsub.subscribe(channel)

    try:
        # Skip the subscription confirmation message
        for message in pubsub.listen():
            if message["type"] == "subscribe":
                continue

            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    yield data

                    # Stop on completion or error
                    if data.get("type") in ["complete", "error"]:
                        break
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    continue

    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
