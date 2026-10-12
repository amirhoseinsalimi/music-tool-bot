"""HTTP request handling for the optional read-only WSGI bridge."""

import hmac
import json
import logging
from typing import Any, Callable, Iterable
from urllib.parse import quote

from .exceptions import BridgeError
from .files import FileDownload
from .service import CoreRepository, connect_core
from .utils import parse_query_string, validate_telegram_id

StartResponse = Callable[[str, list[tuple[str, str]]], object]
WSGIApplication = Callable[[dict[str, Any], StartResponse], Iterable[bytes]]
HTTP_STATUS_LABELS = {
    200: 'OK',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    413: 'Content Too Large',
    503: 'Service Unavailable',
}
# Use the bot's logger hierarchy without importing Telegram helpers into the WSGI layer.
logger = logging.getLogger('music_tool_bot.admin_bridge')


def _validate_request(environ: dict[str, Any], token: str) -> tuple[str, dict[str, str]]:
    """Authenticates the bridge caller and validates the actor and query parameters."""
    supplied_token = environ.get('HTTP_AUTHORIZATION', '')
    expected_token = 'Bearer ' + token

    if not hmac.compare_digest(supplied_token.encode(), expected_token.encode()):
        raise BridgeError(status=401, message='Bridge authentication required')

    if environ.get('REQUEST_METHOD') != 'GET':
        raise BridgeError(status=405, message='Only read operations are supported')

    actor_id = validate_telegram_id(value=environ.get('HTTP_X_ADMIN_TELEGRAM_ID', ''))
    params = parse_query_string(query=environ.get('QUERY_STRING', ''))

    return actor_id, params


def create_app(token: str, repository: CoreRepository | None = None) -> WSGIApplication:
    """
    Creates the read-only bridge without starting a server or the polling bot.

    :param token: str: The shared bridge secret, containing at least 32 characters
    :param repository: CoreRepository | None: An optional repository for isolated tests
    :raises ValueError: The shared secret is missing or too short
    :return: WSGIApplication: The callable served by the separate bridge process
    """
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError('ADMIN_BRIDGE_TOKEN must have at least 32 characters')

    repository = repository or CoreRepository(connect=connect_core)

    def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        """Handles one authenticated read and returns a bounded JSON response."""
        try:
            actor_id, params = _validate_request(environ=environ, token=token)
            data = repository.dispatch(
                actor_id=actor_id,
                path=environ.get('PATH_INFO', ''),
                params=params,
            )
            if isinstance(data, FileDownload):
                headers = [
                    ('Content-Type', 'application/octet-stream'),
                    ('Content-Length', str(data.size)),
                    ('Content-Disposition', "attachment; filename*=UTF-8''" + quote(data.basename)),
                    ('Cache-Control', 'no-store'),
                    ('X-Content-Type-Options', 'nosniff'),
                ]

                try:
                    start_response('200 OK', headers)
                except BaseException:
                    data.close()
                    raise

                return data

            status = 200
        except BridgeError as error:
            status = error.status
            data = {'error': str(error)}
        except ValueError:
            status = 400
            data = {'error': 'Invalid query'}
        except Exception:  # pylint: disable=broad-exception-caught
            # The HTTP boundary must not disclose database errors or credentials.
            logger.error('Core bridge read failed')
            status = 503
            data = {'error': 'Core data unavailable'}

        payload = json.dumps(data, ensure_ascii=False).encode()
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(payload))),
            ('Cache-Control', 'no-store'),
        ]

        start_response(f'{status} {HTTP_STATUS_LABELS[status]}', headers)

        return [payload]

    return app
