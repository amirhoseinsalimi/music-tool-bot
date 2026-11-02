"""Fail closed when the database has not reached the migrations in this release."""

from pathlib import Path

import psycopg2

from config.envs import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USERNAME


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / 'database' / 'migrations'


class SchemaGuardError(RuntimeError):
    """The database migration history cannot safely serve this bot release."""


def expected_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> set[str]:
    """Return the migration names shipped with this release."""
    names = {
        path.stem
        for path in migrations_dir.glob('*.py')
        if not path.name.startswith('_')
    }
    if not names:
        raise SchemaGuardError('No database migrations were found; refusing to start the bot.')
    return names


def pending_migrations(expected: set[str], applied: set[str]) -> list[str]:
    """Return release migrations not recorded by Masonite ORM."""
    return sorted(expected - applied)


def assert_database_schema_current(
        connection_factory=None,
        migrations_dir: Path = MIGRATIONS_DIR) -> None:
    """Check migration history with a read-only query before registering bot handlers."""
    expected = expected_migrations(migrations_dir)
    connect = connection_factory or psycopg2.connect
    connection = None
    try:
        connection = connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_DATABASE,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            connect_timeout=5,
            application_name='music-tool-bot-schema-check',
        )
        with connection.cursor() as cursor:
            cursor.execute('SELECT migration FROM migrations')
            applied = {row[0] for row in cursor.fetchall()}
    except psycopg2.Error:
        raise SchemaGuardError(
            'Could not verify the database migration history; refusing to start. '
            'Check database connectivity and run `make db-upgrade`.'
        ) from None
    finally:
        if connection is not None:
            connection.close()

    pending = pending_migrations(expected, applied)
    if pending:
        names = ', '.join(pending)
        raise SchemaGuardError(
            f'Database schema is behind this release; pending migrations: {names}. '
            'Run `make db-upgrade` before starting the bot.'
        )


def main() -> None:
    """CLI entry point used by `make db-schema-check`."""
    try:
        assert_database_schema_current()
    except SchemaGuardError as error:
        raise SystemExit(str(error)) from None
    print('Database schema is current.')


if __name__ == '__main__':
    main()
