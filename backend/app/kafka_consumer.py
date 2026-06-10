"""Kafka consumer that writes chat message events to PostgreSQL."""

from __future__ import annotations

import json
import time

from sqlalchemy.exc import SQLAlchemyError

from .config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP, KAFKA_TOPIC_CHAT_EVENTS
from .database import SessionLocal
from .message_service import persist_message_event

try:
    from kafka import KafkaConsumer
except ImportError as exc:  # pragma: no cover - startup guard.
    raise RuntimeError("kafka-python is not installed; rebuild the backend image.") from exc


def build_consumer() -> KafkaConsumer:
    return KafkaConsumer(
        KAFKA_TOPIC_CHAT_EVENTS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        key_deserializer=lambda value: value.decode("utf-8") if value else None,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def consume_forever() -> None:
    while True:
        try:
            consumer = build_consumer()
            print(
                "chat message consumer started "
                f"topic={KAFKA_TOPIC_CHAT_EVENTS} group={KAFKA_CONSUMER_GROUP}",
                flush=True,
            )
            for record in consumer:
                db = SessionLocal()
                try:
                    persist_message_event(db, record.value)
                    consumer.commit()
                except SQLAlchemyError:
                    db.rollback()
                    raise
                finally:
                    db.close()
        except Exception as exc:
            print(f"chat message consumer error: {exc}", flush=True)
            time.sleep(5)


if __name__ == "__main__":
    consume_forever()
