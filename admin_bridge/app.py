"""HTTP request handling for the optional read-only WSGI bridge."""

import hmac
import json
import logging
import os
from typing import Any, Callable, Iterable
from urllib.parse import quote

from runtime_controls import ControlsStore, ControlError

from .health import observation
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
    409: 'Conflict',
    413: 'Content Too Large',
    503: 'Service Unavailable',
}
# Use the bot's logger hierarchy without importing Telegram helpers into the WSGI layer.
logger = logging.getLogger('music_tool_bot.admin_bridge')


def _validate_request(
    environ: dict[str, Any], token: str, allow_control_write: bool = False,
) -> tuple[str, dict[str, str]]:
    """Authenticates the bridge caller and validates the actor and query parameters."""
    supplied_token = environ.get('HTTP_AUTHORIZATION', '')
    expected_token = 'Bearer ' + token

    if not hmac.compare_digest(supplied_token.encode(), expected_token.encode()):
        raise BridgeError(status=401, message='Bridge authentication required')

    method = environ.get('REQUEST_METHOD')
    if method != 'GET' and not (allow_control_write and method == 'POST'):
        raise BridgeError(status=405, message='Only read operations are supported')

    actor_id = validate_telegram_id(value=environ.get('HTTP_X_ADMIN_TELEGRAM_ID', ''))
    params = parse_query_string(query=environ.get('QUERY_STRING', ''))

    return actor_id, params


def _control_payload(environ):
    """Read one small, exact-length JSON control command."""
    try:
        length = int(environ.get('CONTENT_LENGTH', '0'))
        is_json = environ.get('CONTENT_TYPE', '').startswith('application/json')
        if not 0 < length <= 4096 or not is_json:
            raise ValueError()
        payload = environ['wsgi.input'].read(length)
        if len(payload) != length:
            raise ValueError()
        return json.loads(payload)
    except (ValueError, KeyError):
        raise BridgeError(400, 'invalid_control') from None


def _dispatch_request(environ, actor_id, params, repository, control_settings):
    """Authorize current membership before health/control observations or changes."""
    controls, control_token = control_settings
    path = environ.get('PATH_INFO', '')
    if path not in {'/v1/health', '/v1/controls', '/v1/controls/audit'}:
        return repository.dispatch(actor_id=actor_id, path=path, params=params)
    allowed_params = {'page'} if path.endswith('/audit') else set()
    if set(params) - allowed_params:
        raise BridgeError(400, 'invalid_request')
    membership = repository.dispatch(actor_id, '/v1/session', {})
    if path == '/v1/health':
        return observation()
    if controls is None:
        raise BridgeError(503, 'controls_unavailable')
    if path.endswith('/audit'):
        return controls.audit(params.get('page', '1'))
    if environ.get('REQUEST_METHOD') == 'POST':
        if not membership['isOwner']:
            raise BridgeError(403, 'owner_required')
        result, created = controls.change(actor_id, _control_payload(environ))
        return {'change': result, 'created': created}
    data = controls.read()
    data['canChange'] = membership['isOwner'] and bool(control_token)
    data['retention'] = {
        'days': None, 'runtimeMutable': False, 'source': 'Sweeper deployment configuration',
    }
    return data


def create_app(
    token: str, repository: CoreRepository | None = None,
    controls: ControlsStore | None = None, control_token: str | None = None,
) -> WSGIApplication:
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
    control_token = control_token or os.getenv('ADMIN_CONTROL_TOKEN', '')
    if control_token and (len(control_token) < 32 or control_token == token):
        raise ValueError('Use a separate control token of at least 32 characters')
    control_path = os.getenv('BOT_CONTROL_DATABASE_URL', '')
    controls = controls or (ControlsStore(control_path) if control_path else None)

    def app(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
        """Handles one authenticated read and returns a bounded JSON response."""
        try:
            writing = environ.get(
                'PATH_INFO') == '/v1/controls' and environ.get('REQUEST_METHOD') == 'POST'
            if writing and not control_token:
                raise BridgeError(503, 'controls_unavailable')
            actor_id, params = _validate_request(
                environ=environ, token=control_token if writing else token,
                allow_control_write=writing)
            data = _dispatch_request(environ, actor_id, params,
                                     repository, (controls, control_token))
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
        except ControlError as error:
            status = error.status
            data = {'error': error.code}
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
