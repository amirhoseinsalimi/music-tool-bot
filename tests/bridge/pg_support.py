"""Disposable schemas on real PostgreSQL; never substitute another SQL engine."""
import os
import uuid
import psycopg2
from psycopg2.extensions import make_dsn
from psycopg2.extras import RealDictCursor


class PostgresFixture:
    """Own a uniquely named schema in the isolated PostgreSQL test database."""

    def __init__(self):
        self.base = os.environ.get('TEST_DATABASE_URL', '')
        if not self.base:
            raise RuntimeError('TEST_DATABASE_URL must name an isolated PostgreSQL test server')
        self.schema = 'mtb_test_'+uuid.uuid4().hex
        with psycopg2.connect(self.base) as db:
            db.autocommit = True
            if db.info.dbname != 'musictoolbot_tests':
                raise RuntimeError('Tests require the isolated musictoolbot_tests database')
            with db.cursor() as c:
                c.execute('CREATE SCHEMA '+self.schema)
        self.dsn = make_dsn(self.base, options='-csearch_path='+self.schema)

    def close(self):
        """Remove only the schema created for this test."""
        with psycopg2.connect(self.base) as db:
            db.autocommit = True
            with db.cursor() as c:
                c.execute('DROP SCHEMA '+self.schema+' CASCADE')

    def connect(self):
        """Open a native dictionary-row PostgreSQL fixture connection."""
        return psycopg2.connect(self.dsn, cursor_factory=RealDictCursor)
