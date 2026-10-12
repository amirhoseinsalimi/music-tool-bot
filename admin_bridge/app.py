"""WSGI application with no new bot dependencies or polling side effects."""
import hmac
import json
import logging
from urllib.parse import parse_qs

from .service import BridgeError, CoreRepository, connect_core, telegram_id


def create_app(token, repository=None):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("ADMIN_BRIDGE_TOKEN must have at least 32 characters")
    repository = repository or CoreRepository(connect_core)

    def app(environ, start_response):
        try:
            supplied = environ.get("HTTP_AUTHORIZATION", "")
            if not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
                raise BridgeError(401, "Bridge authentication required")
            if environ.get("REQUEST_METHOD") != "GET":
                raise BridgeError(405, "Only read operations are supported")
            actor = telegram_id(environ.get("HTTP_X_ADMIN_TELEGRAM_ID", ""))
            query = environ.get("QUERY_STRING", "")
            if len(query) > 1024:
                raise BridgeError(400, "Query is too long")
            parsed = parse_qs(query, keep_blank_values=True, max_num_fields=10)
            if any(len(values) != 1 for values in parsed.values()):
                raise BridgeError(400, "Duplicate filters")
            data = repository.dispatch(actor, environ.get("PATH_INFO", ""), {key: value[0] for key, value in parsed.items()})
            status = 200
        except BridgeError as error:
            status, data = error.status, {"error": str(error)}
        except ValueError:
            status, data = 400, {"error": "Invalid query"}
        except Exception:
            logging.getLogger(__name__).error("Core bridge read failed")
            status, data = 503, {"error": "Core data unavailable"}
        payload = json.dumps(data, ensure_ascii=False).encode()
        labels = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 413: "Content Too Large", 503: "Service Unavailable"}
        start_response(f"{status} {labels[status]}", [("Content-Type", "application/json; charset=utf-8"),
                       ("Content-Length", str(len(payload))), ("Cache-Control", "no-store")])
        return [payload]
    return app
