from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from mysql.connector.pooling import PooledMySQLConnection

from tollbooth_simulator.db.database import create_connection


class PassageStore:
    def __init__(
        self,
        connection_factory: Callable[
            [], PooledMySQLConnection
        ] = create_connection,
    ) -> None:
        self._connection_factory = connection_factory

    def create(
        self,
        event_id: UUID,
        license_plate_id: str,
        cost_cents: int,
        occurred_at: datetime,
    ) -> None:
        connection = self._connection_factory()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO toll_passages (
                    event_id,
                    license_plate_id,
                    cost_cents,
                    occurred_at
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    str(event_id),
                    license_plate_id,
                    cost_cents,
                    occurred_at,
                ),
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            cursor.close()

            # Because this is a pooled connection, close() returns
            # the connection to the pool instead of destroying it.
            connection.close()

    def get_debt(
        self,
        license_plate_id: str,
    ) -> int:
        connection = self._connection_factory()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT COALESCE(SUM(cost_cents), 0)
                FROM toll_passages
                WHERE license_plate_id = %s
                """,
                (license_plate_id,),
            )

            result = cursor.fetchone()

            if result is None:
                return 0

            return int(result[0])

        finally:
            cursor.close()
            connection.close()