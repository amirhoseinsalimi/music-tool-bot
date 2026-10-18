"""Native PostgreSQL connections with explicit transaction and row handling."""
import psycopg2
from psycopg2.extras import DictCursor
from decimal import Decimal

class Cursor(DictCursor):
    @staticmethod
    def normalize(row):
        if row is not None:
            for i,value in enumerate(row):
                if isinstance(value,Decimal) and value == value.to_integral_value(): row[i]=int(value)
        return row
    def fetchone(self): return self.normalize(super().fetchone())
    def fetchall(self): return [self.normalize(row) for row in super().fetchall()]
    def __iter__(self):
        while True:
            row=self.fetchone()
            if row is None: return
            yield row

Error = psycopg2.Error
IntegrityError = psycopg2.IntegrityError
GUARD_SQL = """
CREATE OR REPLACE FUNCTION reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Immutable record: %', TG_TABLE_NAME USING ERRCODE='23514'; END;
$$;
"""

class Database:
    def __init__(self, dsn):
        if not dsn or not isinstance(dsn, str):
            raise ValueError('A PostgreSQL connection string is required')
        self.connection = psycopg2.connect(dsn, connect_timeout=5)
        self.connection.autocommit = True

    def execute(self, query, params=None):
        cursor = self.connection.cursor(cursor_factory=Cursor)
        cursor.execute(query, params)
        return cursor

    def begin_write(self):
        self.execute('BEGIN')
        # Preserve the former serialized-writer contract across API/worker
        # processes. Lock scope follows the database and schema, including tests.
        self.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_database() || ':' || current_schema(), 0))")

    def commit(self):
        self.execute('COMMIT')

    def rollback(self):
        self.execute('ROLLBACK')

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, kind, *_args):
        try:
            if self.connection.get_transaction_status() != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                if kind is None: self.commit()
                else: self.rollback()
        finally:
            self.close()
