import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from tollbooth_simulator.api.passages import app


def test_receive_toll_passage_returns_ok() -> None:
    fake_producer = AsyncMock()

    # Simulates the Kafka message returned after successful delivery.
    delivered_message = MagicMock()
    delivered_message.partition.return_value = 0
    delivered_message.offset.return_value = 10

    # producer.produce() returns something that we await a second time
    # to receive Kafka's delivery acknowledgement.
    async def delivery_result():
        return delivered_message

    fake_producer.produce.return_value = delivery_result()

    # Replace the real Kafka producer with our fake producer.
    app.state.kafka_producer = fake_producer

    client = TestClient(app)

    passage_event = {
        "eventId": "00000000-0000-4000-8000-000000000001",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-12T18:00:00Z",
    }

    response = client.post(
        "/toll-passages",
        json=passage_event,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Confirm that the endpoint submitted exactly one Kafka message.
    fake_producer.produce.assert_awaited_once()

    kafka_arguments = fake_producer.produce.await_args.kwargs

    assert kafka_arguments["topic"] == "toll-passages"
    assert kafka_arguments["key"] == "ABC-123"

    published_event = json.loads(kafka_arguments["value"])

    assert published_event["eventId"] == passage_event["eventId"]
    assert (
        published_event["licensePlateId"]
        == passage_event["licensePlateId"]
    )

    assert datetime.fromisoformat(
        published_event["timestamp"].replace("Z", "+00:00")
    ) == datetime.fromisoformat(
        passage_event["timestamp"].replace("Z", "+00:00")
    )