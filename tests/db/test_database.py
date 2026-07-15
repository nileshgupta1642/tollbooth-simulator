from unittest.mock import MagicMock, patch

import pytest

from tollbooth_simulator.db.database import (
    create_connection,
    get_connection_pool,
)


@pytest.fixture(autouse=True)
def configure_database_environment(monkeypatch) -> None:
    monkeypatch.setenv("MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("MYSQL_PORT", "3306")
    monkeypatch.setenv("MYSQL_USER", "tollbooth")
    monkeypatch.setenv("MYSQL_PASSWORD", "test-password")
    monkeypatch.setenv("MYSQL_DATABASE", "tollbooth")


def setup_function() -> None:
    # get_connection_pool() is cached, so clear it before each test.
    get_connection_pool.cache_clear()


def teardown_function() -> None:
    get_connection_pool.cache_clear()


@patch(
    "tollbooth_simulator.db.database.MySQLConnectionPool"
)
def test_get_connection_pool_creates_pool_once(
    mock_pool_class: MagicMock,
) -> None:
    expected_pool = MagicMock()
    mock_pool_class.return_value = expected_pool

    first_result = get_connection_pool()
    second_result = get_connection_pool()

    assert first_result is expected_pool
    assert second_result is expected_pool

    mock_pool_class.assert_called_once_with(
        pool_name="tollbooth_pool",
        pool_size=5,
        host="127.0.0.1",
        port=3306,
        user="tollbooth",
        password="test-password",
        database="tollbooth",
    )


@patch(
    "tollbooth_simulator.db.database.MySQLConnectionPool"
)
def test_create_connection_borrows_connection_from_pool(
    mock_pool_class: MagicMock,
) -> None:
    expected_connection = MagicMock()
    fake_pool = MagicMock()
    fake_pool.get_connection.return_value = expected_connection

    mock_pool_class.return_value = fake_pool

    connection = create_connection()

    assert connection is expected_connection
    fake_pool.get_connection.assert_called_once_with()
