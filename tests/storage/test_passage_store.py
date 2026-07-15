from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from tollbooth_simulator.storage.passage_store import PassageStore


def create_fake_database_objects():
    cursor = MagicMock()
    connection = MagicMock()
    connection.cursor.return_value = cursor

    connection_factory = MagicMock(
        return_value=connection
    )

    return connection_factory, connection, cursor


def test_create_inserts_toll_passage() -> None:
    connection_factory, connection, cursor = (
        create_fake_database_objects()
    )

    store = PassageStore(
        connection_factory=connection_factory
    )

    event_id = UUID(
        "00000000-0000-4000-8000-000000000001"
    )
    occurred_at = datetime(2026, 7, 14, 18, 0, 0)

    store.create(
        event_id=event_id,
        license_plate_id="ABC-123",
        cost_cents=150,
        occurred_at=occurred_at,
    )

    connection_factory.assert_called_once_with()
    connection.cursor.assert_called_once_with()

    cursor.execute.assert_called_once()

    sql, parameters = cursor.execute.call_args.args

    assert "INSERT INTO toll_passages" in sql
    assert parameters == (
        str(event_id),
        "ABC-123",
        150,
        occurred_at,
    )

    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()

    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_create_rolls_back_when_insert_fails() -> None:
    connection_factory, connection, cursor = (
        create_fake_database_objects()
    )

    cursor.execute.side_effect = RuntimeError(
        "Database insert failed"
    )

    store = PassageStore(
        connection_factory=connection_factory
    )

    with pytest.raises(
        RuntimeError,
        match="Database insert failed",
    ):
        store.create(
            event_id=UUID(
                "00000000-0000-4000-8000-000000000001"
            ),
            license_plate_id="ABC-123",
            cost_cents=150,
            occurred_at=datetime(
                2026,
                7,
                14,
                18,
                0,
                0,
            ),
        )

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once_with()

    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_get_debt_returns_sum_for_license_plate() -> None:
    connection_factory, connection, cursor = (
        create_fake_database_objects()
    )

    cursor.fetchone.return_value = (450,)

    store = PassageStore(
        connection_factory=connection_factory
    )

    result = store.get_debt("ABC-123")

    assert result == 450

    cursor.execute.assert_called_once()

    sql, parameters = cursor.execute.call_args.args

    assert "SUM(cost_cents)" in sql
    assert "WHERE license_plate_id = %s" in sql
    assert parameters == ("ABC-123",)

    cursor.fetchone.assert_called_once_with()

    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()


def test_get_debt_returns_zero_when_plate_has_no_records() -> None:
    connection_factory, connection, cursor = (
        create_fake_database_objects()
    )

    # This is what COALESCE(SUM(...), 0) should return.
    cursor.fetchone.return_value = (0,)

    store = PassageStore(
        connection_factory=connection_factory
    )

    result = store.get_debt("UNKNOWN-PLATE")

    assert result == 0

    cursor.close.assert_called_once_with()
    connection.close.assert_called_once_with()