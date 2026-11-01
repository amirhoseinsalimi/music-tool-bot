"""Small process-local pool for best-effort PostgreSQL telemetry writes."""
from contextlib import contextmanager
from threading import Lock

from psycopg2.pool import ThreadedConnectionPool

_pool_lock = Lock()
_pools = {}


def _pool_for(connection_options):
    key = tuple(sorted(connection_options.items()))
    with _pool_lock:
        pool = _pools.get(key)
        if pool is None:
            pool = ThreadedConnectionPool(1, 8, **connection_options)
            _pools[key] = pool
        return pool


@contextmanager
def pooled_connection(**connection_options):
    """Lease a connection; discard it after errors and reuse it otherwise."""
    pool = _pool_for(connection_options)
    connection = pool.getconn()
    try:
        yield connection
    except BaseException:
        pool.putconn(connection, close=True)
        raise
    else:
        pool.putconn(connection, close=bool(connection.closed))
