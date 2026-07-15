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

def process_message(
    message,
    passage_store: PassageStore,
    kafka_consumer: Consumer,
) -> tuple[dict, bool]:
    event = json.loads(
        message.value().decode("utf-8")
    )

    occurred_at = datetime.fromisoformat(
        event["timestamp"].replace("Z", "+00:00")
    )

    occurred_at = occurred_at.astimezone(
        timezone.utc
    ).replace(tzinfo=None)

    created = passage_store.create(
        event_id=UUID(event["eventId"]),
        license_plate_id=event["licensePlateId"],
        cost_cents=TOLL_RATE_CENTS,
        occurred_at=occurred_at,
    )

    # This is reached only if the database operation succeeds
    # or the passage is confirmed to be a duplicate.
    kafka_consumer.commit(
        message=message,
        asynchronous=False,
    )

    return event, created


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

            event, created = process_message(
                message=message,
                passage_store=passage_store,
                kafka_consumer=consumer,
            )

            if created:
                print("Stored toll passage:", event)
            else:
                print(
                    "Skipped duplicate toll passage:",
                    event["eventId"]
                    )

    except KeyboardInterrupt:
        print("\nStopping consumer...")

    finally:
        consumer.close()


if __name__ == "__main__":
    run_consumer()