import psycopg2
from psycopg2 import pool as pg_pool

from config import settings
from logger import get_logger

log = get_logger(__name__)
_pool: pg_pool.ThreadedConnectionPool | None = None


def init_pool(minconn: int = 1, maxconn: int = 10) -> None:
    global _pool
    log.info("Initialising PostgreSQL connection pool (min=%d, max=%d)", minconn, maxconn)
    _pool = pg_pool.ThreadedConnectionPool(
        minconn,
        maxconn,
        dsn=settings.postgres_dsn,
    )
    log.info("Connection pool ready")


def get_conn():
    if _pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _pool.getconn()


def put_conn(conn) -> None:
    if _pool is not None:
        _pool.putconn(conn)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        log.info("Closing PostgreSQL connection pool")
        _pool.closeall()
        _pool = None


class ManagedConn:
    """Context manager that borrows a connection from the pool."""

    def __enter__(self):
        self.conn = get_conn()
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            log.warning("Rolling back transaction due to %s", exc_type.__name__)
            self.conn.rollback()
        put_conn(self.conn)
        return False
