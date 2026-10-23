"""Validation and serialization helpers for the administrative bridge."""

from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.parse import parse_qs

from .exceptions import BridgeError

MAX_TELEGRAM_ID = 9223372036854775807
MAX_QUERY_LENGTH = 1024
MAX_QUERY_FIELDS = 10
MAX_SEARCH_LENGTH = 80
MAX_PAGE_NUMBER = 100000
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 10
USER_FILTER_NAMES = {'q', 'status', 'language', 'page', 'pageSize', 'sort', 'direction'}
USER_STATUS_SLUGS = {'active', 'blocked', 'deleted'}
USER_DISPLAY_NAME_SQL = 'u.display_name'
USER_SORT_COLUMNS = {
    'displayName', 'username', 'telegramId', 'language', 'status', 'audioSubmissions',
    'lastInteractionAt', 'createdAt',
}
FILE_SORT_COLUMNS = {'basename', 'telegramId', 'bytes', 'modifiedAt'}


def parse_sort(params: Mapping[str, str], columns: set[str]) -> tuple[str, str]:
    """Validates an allowlisted sort key and direction, defaulting to no override."""
    sort = params.get('sort', '')
    direction = params.get('direction', '')
    if not sort and not direction:
        return '', ''
    if sort not in columns or direction not in {'asc', 'desc'}:
        raise BridgeError(status=400, message='Invalid sorting')
    return sort, direction


def validate_basename(value: str) -> str:
    """
    Validates one stored filename, excluding paths and header control characters.

    :param value: str: The exact basename from a retained file listing
    :raises BridgeError: The name is empty, unsafe or not valid UTF-8 text
    :return: str: The unchanged safe basename
    """
    if not value or value in {'.', '..'} or any(
        character in '/\\' or ord(character) < 32 or ord(character) == 127
        for character in value
    ):
        raise BridgeError(status=400, message='Invalid stored basename')

    try:
        if len(value.encode('utf-8')) > 255:
            raise BridgeError(status=400, message='Invalid stored basename')
    except UnicodeError as error:
        raise BridgeError(status=400, message='Invalid stored basename') from error

    return value


def parse_file_filters(params: Mapping[str, str]) -> tuple[str, str, int, int, str, str]:
    """
    Validates filesystem search, an exact owner filter and bounded pagination.

    :param params: Mapping[str, str]: Search, Telegram ID, page and page size
    :raises BridgeError: A filter is unknown, malformed or outside supported bounds
    :return: tuple[str, str, int, int]: Casefolded search, owner ID, page and page size
    """
    if set(params) - {'q', 'telegramId', 'page', 'pageSize', 'sort', 'direction'}:
        raise BridgeError(status=400, message='Unknown filter')

    query = params.get('q', '').strip()
    telegram_id = params.get('telegramId', '')

    if len(query) > MAX_SEARCH_LENGTH:
        raise BridgeError(status=400, message='Invalid file search')

    if telegram_id:
        telegram_id = validate_telegram_id(value=telegram_id)

    try:
        page = int(params.get('page', '1'))
        page_size = int(params.get('pageSize', str(DEFAULT_PAGE_SIZE)))
    except ValueError as error:
        raise BridgeError(status=400, message='Invalid pagination') from error

    if not 1 <= page <= MAX_PAGE_NUMBER or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise BridgeError(status=400, message='Invalid pagination')

    sort, direction = parse_sort(params=params, columns=FILE_SORT_COLUMNS)
    return query.casefold(), telegram_id, page, page_size, sort, direction


def validate_telegram_id(value: str) -> str:
    """
    Validates and normalizes a positive Telegram ID for a core lookup.

    :param value: str: The Telegram ID supplied by the trusted caller
    :raises BridgeError: The ID is malformed or outside the supported integer range
    :return: str: The normalized ID, retained as text across the JSON boundary
    """
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise BridgeError(status=400, message='Invalid Telegram ID')

    number = int(value)

    if not 0 < number <= MAX_TELEGRAM_ID:
        raise BridgeError(status=400, message='Invalid Telegram ID')

    return str(number)


def parse_query_string(query: str) -> dict[str, str]:
    """
    Parses a bounded query string and rejects duplicate filter values.

    :param query: str: The raw WSGI query string
    :raises BridgeError: The query is too long or contains duplicate filter values
    :raises ValueError: The query contains too many fields
    :return: dict[str, str]: One value per query parameter
    """
    if len(query) > MAX_QUERY_LENGTH:
        raise BridgeError(status=400, message='Query is too long')

    parsed = parse_qs(
        qs=query,
        keep_blank_values=True,
        max_num_fields=MAX_QUERY_FIELDS,
    )

    if any(len(values) != 1 for values in parsed.values()):
        raise BridgeError(status=400, message='Duplicate filters')

    return {key: values[0] for key, values in parsed.items()}


def parse_user_filters(params: Mapping[str, str]) -> tuple[str, list[str], int, int, str, str]:
    """
    Validates user filters and creates parameterized SQL conditions.

    :param params: Mapping[str, str]: Search, status, language and pagination parameters
    :raises BridgeError: A filter is unknown, malformed or outside the supported range
    :return: tuple: SQL conditions, bindings, page, page size, allowlisted sort key and direction
    """
    if set(params) - USER_FILTER_NAMES:
        raise BridgeError(status=400, message='Unknown filter')

    query = params.get('q', '').strip().lstrip('@')
    status = params.get('status', '')
    language = params.get('language', '')

    if len(query) > MAX_SEARCH_LENGTH or (status and status not in USER_STATUS_SLUGS):
        raise BridgeError(status=400, message='Invalid filter')

    if len(language) > 10 or (language and not language.isascii()):
        raise BridgeError(status=400, message='Invalid language')

    try:
        page = int(params.get('page', '1'))
        page_size = int(params.get('pageSize', str(DEFAULT_PAGE_SIZE)))
    except ValueError as error:
        raise BridgeError(status=400, message='Invalid pagination') from error

    if not 1 <= page <= MAX_PAGE_NUMBER or not 1 <= page_size <= MAX_PAGE_SIZE:
        raise BridgeError(status=400, message='Invalid pagination')

    clauses: list[str] = []
    values: list[str] = []

    if query:
        # SQL LIKE wildcards are escaped so a search remains literal text.
        escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        clauses.append(
            f'(u.username ILIKE %s OR {USER_DISPLAY_NAME_SQL} ILIKE %s '
            'OR CAST(u.user_id AS TEXT) LIKE %s)'
        )
        values.extend([f'%{escaped}%'] * 3)

    if status:
        clauses.append('s.slug = %s')
        values.append(status)

    if language:
        clauses.append('l.iso = %s')
        values.append(language)

    conditions = ' WHERE ' + ' AND '.join(clauses) if clauses else ''

    sort, direction = parse_sort(params=params, columns=USER_SORT_COLUMNS)
    return conditions, values, page, page_size, sort, direction


def serialize_timestamp(value: datetime | str | None) -> str | None:
    """
    Serializes a core timestamp with an explicit UTC offset.

    Naive values use the core ORM's UTC convention. Historical database timestamps
    must be checked when connecting an existing deployment.

    :param value: datetime | str | None: The recorded timestamp, if available
    :return: str | None: An ISO timestamp in UTC, or ``None`` when not recorded
    """
    if value is None:
        return None

    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value))

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).isoformat()


def serialize_user_profile(row: Mapping[str, Any]) -> dict[str, Any]:
    """
    Serializes the available core user fields without inventing missing history.

    :param row: Mapping[str, Any]: The user record joined with its language and status
    :return: dict[str, Any]: The existing v1 profile response used by the private API
    """
    return {
        'id': row['id'],
        'telegramId': str(row['user_id']),
        'displayName': row['display_name'] or None,
        'username': row['username'],
        'language': row['language_name'] or 'Not recorded',
        'languageIso': row['language_iso'],
        'status': row['status_slug'],
        'audioSubmissions': row['number_of_files_sent'],
        'createdAt': serialize_timestamp(value=row['created_at']),
        'updatedAt': serialize_timestamp(value=row['updated_at']),
        'lastInteractionAt': serialize_timestamp(value=row['last_interaction_at']),
    }
