import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from tollbooth_simulator.consumer import process_message


def create_fake_message(event: dict) -> MagicMock:
    message = MagicMock()
    message.value.return_value = json.dumps(event).encode(
        "utf-8"
    )
    return message


@patch(
    "tollbooth_simulator.consumer.TOLL_RATE_CENTS",
    150,
)
def test_process_message_stores_passage_and_commits_offset() -> None:
    event = {
        "eventId": "00000000-0000-4000-8000-000000000001",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-14T18:00:00Z",
    }

    message = create_fake_message(event)

    passage_store = MagicMock()
    passage_store.create.return_value = True

    kafka_consumer = MagicMock()

    returned_event, created = process_message(
        message=message,
        passage_store=passage_store,
        kafka_consumer=kafka_consumer,
    )

    assert returned_event == event
    assert created is True

    passage_store.create.assert_called_once_with(
        event_id=UUID(event["eventId"]),
        license_plate_id="ABC-123",
        cost_cents=150,
        occurred_at=datetime(2026, 7, 14, 18, 0, 0),
    )

    kafka_consumer.commit.assert_called_once_with(
        message=message,
        asynchronous=False,
    )


def test_process_message_commits_duplicate_event() -> None:
    event = {
        "eventId": "00000000-0000-4000-8000-000000000001",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-14T18:00:00Z",
    }

    message = create_fake_message(event)

    passage_store = MagicMock()

    # False means this event_id was already in MySQL.
    passage_store.create.return_value = False

    kafka_consumer = MagicMock()

    _, created = process_message(
        message=message,
        passage_store=passage_store,
        kafka_consumer=kafka_consumer,
    )

    assert created is False

    # A duplicate is already safely stored, so its offset
    # should be committed.
    kafka_consumer.commit.assert_called_once_with(
        message=message,
        asynchronous=False,
    )


def test_process_message_does_not_commit_when_database_fails() -> None:
    event = {
        "eventId": "00000000-0000-4000-8000-000000000001",
        "licensePlateId": "ABC-123",
        "timestamp": "2026-07-14T18:00:00Z",
    }

    message = create_fake_message(event)

    passage_store = MagicMock()
    passage_store.create.side_effect = RuntimeError(
        "Database unavailable"
    )

    kafka_consumer = MagicMock()

    with pytest.raises(
        RuntimeError,
        match="Database unavailable",
    ):
        process_message(
            message=message,
            passage_store=passage_store,
            kafka_consumer=kafka_consumer,
        )

    kafka_consumer.commit.assert_not_called()