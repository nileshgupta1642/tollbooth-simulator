import json
import os
from datetime import datetime, timezone
from uuid import UUID

from confluent_kafka import Consumer, KafkaException

from tollbooth_simulator.storage.passage_store import PassageStore


KAFKA_TOPIC = "toll-passages"
TOLL_RATE_CENTS = int(os.getenv("TOLL_RATE_CENTS", "150"))

consumer = Consumer(
    {
        "bootstrap.servers": "localhost:9092",
        "group.id": "toll-charging-service",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
)

passage_store = PassageStore()


def run_consumer() -> None:
    consumer.subscribe([KAFKA_TOPIC])

    print(f"Listening for events on '{KAFKA_TOPIC}'...")

    try:
        while True:
            message = consumer.poll(timeout=1.0)

            # No new message arrived during this one-second poll.
            if message is None:
                continue

            if message.error():
                raise KafkaException(message.error())

            event = json.loads(
                message.value().decode("utf-8")
            )

            occurred_at = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            )

            # MySQL DATETIME does not store timezone information,
            # so normalize the timestamp to naive UTC.
            occurred_at = occurred_at.astimezone(
                timezone.utc
            ).replace(tzinfo=None)

            created = passage_store.create(
                event_id=UUID(event["eventId"]),
                license_plate_id=event["licensePlateId"],
                cost_cents=TOLL_RATE_CENTS,
                occurred_at=occurred_at,
            )

            # Commit only after the database insert succeeds
            # or the event is confirmed to be a duplicate.
            consumer.commit(
                message=message,
                asynchronous=False,
            )

    except KeyboardInterrupt:
        print("\nStopping consumer...")

    finally:
        consumer.close()


if __name__ == "__main__":
    run_consumer()