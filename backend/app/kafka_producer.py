"""Kafka producer for chat message events."""

from __future__ import annotations

import json
from threading import Lock
from typing import Any

from .config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_PRODUCE_TIMEOUT_SECONDS,
    KAFKA_TOPIC_CHAT_EVENTS,
)

try:
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover - exercised only when dependency is missing at runtime.
    KafkaProducer = None  # type: ignore[assignment]


_producer = None
_producer_lock = Lock()


def _get_producer():
    global _producer
    if KafkaProducer is None:
        raise RuntimeError("kafka-python is not installed; rebuild the backend image.")

    if _producer is None:
        with _producer_lock:
            if _producer is None:
                _producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    key_serializer=lambda value: str(value).encode("utf-8"),
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    acks="all",
                    retries=3,
                    linger_ms=5,
                )
    return _producer


def publish_message_event(event: dict[str, Any]) -> None:
    """Publish a message event and wait for Kafka to acknowledge it."""
    producer = _get_producer()
    future = producer.send(
        KAFKA_TOPIC_CHAT_EVENTS,
        key=event["room_id"],
        value=event,
    )
    future.get(timeout=KAFKA_PRODUCE_TIMEOUT_SECONDS)
