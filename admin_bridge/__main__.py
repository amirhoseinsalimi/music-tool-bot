"""Local development entry point for the optional administrative bridge."""

from wsgiref.simple_server import make_server

from config.envs import ADMIN_BRIDGE_PORT, ADMIN_BRIDGE_TOKEN
from utils.logging import configure_logging, get_logger

from .app import create_app

logger = get_logger(name=__name__)


def main() -> None:
    """Starts the loopback bridge using the bot's environment and logging conventions."""
    configure_logging()

    application = create_app(token=ADMIN_BRIDGE_TOKEN)
    port = int(ADMIN_BRIDGE_PORT)

    if not 1 <= port <= 65535:
        raise ValueError('ADMIN_BRIDGE_PORT must be between 1 and 65535')

    logger.info('Starting the administrative bridge on 127.0.0.1:%s', port)

    with make_server(host='127.0.0.1', port=port, app=application) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
