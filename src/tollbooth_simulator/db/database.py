from functools import lru_cache

from mysql.connector.pooling import (
    MySQLConnectionPool,
    PooledMySQLConnection,
)


@lru_cache(maxsize=1)
def get_connection_pool() -> MySQLConnectionPool:
    """
    Create one connection pool for the lifetime of this process.
    """

    return MySQLConnectionPool(
        pool_name="tollbooth_pool",
        pool_size=5,
        host="127.0.0.1",
        port=3306,
        user="tollbooth",
        password="tollbooth",
        database="tollbooth",
    )


def create_connection() -> PooledMySQLConnection:
    """
    Borrow one database connection from the pool.

    Calling close() on this connection returns it to the pool.
    """

    return get_connection_pool().get_connection()