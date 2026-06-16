"""Database connection pool using psycopg2."""
import psycopg2
import psycopg2.pool
import psycopg2.extras
from contextlib import contextmanager
from config import settings

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=settings.database_url,
        )
    return _pool


@contextmanager
def get_db():
    """Context manager that yields a dict-cursor connection and auto-commits/rolls back."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        conn.autocommit = False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        pool.putconn(conn)


def fetchall(query: str, params=None) -> list[dict]:
    with get_db() as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetchone(query: str, params=None) -> dict | None:
    with get_db() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute(query: str, params=None) -> None:
    with get_db() as cur:
        cur.execute(query, params)
