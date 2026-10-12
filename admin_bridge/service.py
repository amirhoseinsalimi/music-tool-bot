"""Core-owned database reads for the optional administrative bridge."""

from contextlib import closing
from typing import Any, Callable, Mapping

import psycopg2
from psycopg2.extensions import (
    connection as PostgresConnection,
    cursor as PostgresCursor,
)
from psycopg2.extras import RealDictCursor

from .exceptions import BridgeError
from .utils import (
    parse_user_filters,
    serialize_user_profile,
    validate_telegram_id,
)

MAX_EXPORT_ROWS = 20000
USER_JOINS = (
    ' FROM users u'
    ' LEFT JOIN languages l ON l.id = u.language_id'
    ' LEFT JOIN user_statuses s ON s.id = u.user_status_id'
)
USER_COLUMNS = (
    'u.id, u.user_id, u.username, u.number_of_files_sent, '
    'u.created_at, u.updated_at, u.last_interaction_at, '
    'l.name AS language_name, l.iso AS language_iso, s.slug AS status_slug'
)


# Keep one public entry point so every read passes the same authorization gate.
class CoreRepository:  # pylint: disable=too-few-public-methods
    """Reads existing core records in transactions authorized by current admin membership."""

    def __init__(self, connect: Callable[[], PostgresConnection]) -> None:
        """
        Creates the repository with a connection factory.

        :param connect: Callable: Creates a core connection that this repository will close
        """
        self.connect = connect

    def dispatch(
        self,
        actor_id: str,
        path: str,
        params: Mapping[str, str],
    ) -> dict[str, Any]:
        """
        Authorizes the actor and performs one read in the same database transaction.

        :param actor_id: str: The verified Telegram ID supplied by the private API
        :param path: str: The requested v1 bridge endpoint
        :param params: Mapping[str, str]: The endpoint's query parameters
        :raises BridgeError: The actor is not an admin or the requested read is invalid
        :return: dict[str, Any]: The endpoint's JSON-compatible response
        """
        with closing(self.connect()) as connection:
            connection.set_session(readonly=True, isolation_level='REPEATABLE READ')

            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5000ms'")
                admin = self._get_admin(cursor=cursor, actor_id=actor_id)

                return self._dispatch_authorized(
                    cursor=cursor,
                    admin=admin,
                    path=path,
                    params=params,
                )

    @staticmethod
    def _get_admin(cursor: PostgresCursor, actor_id: str) -> dict[str, Any]:
        """Returns current admin membership or denies the read."""
        cursor.execute(
            'SELECT is_owner FROM admins WHERE admin_user_id = %s LIMIT 1',
            (int(actor_id),),
        )
        admin = cursor.fetchone()

        if admin is None:
            raise BridgeError(status=403, message='Admin access required')

        return {'telegramId': actor_id, 'isOwner': bool(admin['is_owner'])}

    def _dispatch_authorized(
        self,
        cursor: PostgresCursor,
        admin: Mapping[str, Any],
        path: str,
        params: Mapping[str, str],
    ) -> dict[str, Any]:
        """Routes an authorized read without opening another transaction."""
        if path == '/v1/session':
            return dict(admin)

        if path == '/v1/overview':
            return self._get_overview(cursor=cursor)

        if path in {'/v1/users', '/v1/users/export'}:
            return self._list_users(
                cursor=cursor,
                params=params,
                exporting=path.endswith('/export'),
            )

        if path.startswith('/v1/users/'):
            target_id = validate_telegram_id(value=path.removeprefix('/v1/users/'))

            return self._get_user_profile(cursor=cursor, telegram_id=target_id)

        raise BridgeError(status=404, message='Not found')

    @staticmethod
    def _get_overview(cursor: PostgresCursor) -> dict[str, Any]:
        """Returns current totals and language counts, without reconstructed activity history."""
        cursor.execute(
            'SELECT COUNT(*) AS total, '
            'COALESCE(SUM(u.number_of_files_sent), 0) AS audio' + USER_JOINS
        )
        counts = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) AS total" + USER_JOINS + " WHERE s.slug = 'active'")
        active_status_count = cursor.fetchone()['total']

        cursor.execute(
            "SELECT COALESCE(l.name, 'Not recorded') AS name, COUNT(*) AS count"
            + USER_JOINS
            + ' GROUP BY l.name ORDER BY count DESC, name'
        )

        return {
            'totalUsers': counts['total'],
            'activeStatus': active_status_count,
            'audioSubmissions': counts['audio'],
            'languages': list(cursor.fetchall()),
        }

    @staticmethod
    def _list_users(
        cursor: PostgresCursor,
        params: Mapping[str, str],
        exporting: bool,
    ) -> dict[str, Any]:
        """Returns a filtered user page or a bounded collection for Excel export."""
        conditions, values, page, page_size = parse_user_filters(params=params)

        cursor.execute('SELECT COUNT(*) AS total' + USER_JOINS + conditions, values)
        total = cursor.fetchone()['total']

        if exporting and total > MAX_EXPORT_ROWS:
            raise BridgeError(
                status=413,
                message='Export exceeds 20000 rows; narrow the filters',
            )

        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        limit = MAX_EXPORT_ROWS if exporting else page_size
        offset = 0 if exporting else (page - 1) * page_size

        cursor.execute(
            'SELECT ' + USER_COLUMNS + USER_JOINS + conditions
            + ' ORDER BY u.created_at DESC, u.id DESC LIMIT %s OFFSET %s',
            [*values, limit, offset],
        )
        users = [serialize_user_profile(row=row) for row in cursor.fetchall()]

        cursor.execute('SELECT iso, name FROM languages ORDER BY id')

        return {
            'users': users,
            'total': total,
            'page': page,
            'pageSize': page_size,
            'languages': list(cursor.fetchall()),
        }

    @staticmethod
    def _get_user_profile(cursor: PostgresCursor, telegram_id: str) -> dict[str, Any]:
        """Returns one available core profile or reports that the user was not found."""
        cursor.execute(
            'SELECT ' + USER_COLUMNS + USER_JOINS + ' WHERE u.user_id = %s',
            (int(telegram_id),),
        )
        row = cursor.fetchone()

        if row is None:
            raise BridgeError(status=404, message='User not found')

        return serialize_user_profile(row=row)


def connect_core() -> PostgresConnection:
    """
    Opens a core PostgreSQL connection using the bot's existing database configuration.

    Configuration is imported when a connection is needed, without initializing polling.

    :return: PostgresConnection: A connection with a five-second establishment timeout
    """
    from config.envs import (  # pylint: disable=import-outside-toplevel
        DB_DATABASE,
        DB_HOST,
        DB_PASSWORD,
        DB_PORT,
        DB_USERNAME,
    )

    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_DATABASE,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        connect_timeout=5,
    )
