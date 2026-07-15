import json

from confluent_kafka import Consumer, KafkaException


KAFKA_TOPIC = "toll-passages"

consumer = Consumer(
    {
        "bootstrap.servers": "localhost:9092",
        "group.id": "toll-charging-service",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    }
)


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

            print("Received toll passage:", event)

            # Mark this message as processed only after the
            # processing above succeeds.
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