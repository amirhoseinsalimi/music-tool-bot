"""Local development entry point; the bot continues to run separately."""
from wsgiref.simple_server import make_server

from config.envs import get_env
from .app import create_app


if __name__ == "__main__":
    application = create_app(get_env("ADMIN_BRIDGE_TOKEN", ""))
    with make_server("127.0.0.1", int(get_env("ADMIN_BRIDGE_PORT", "5001")), application) as server:
        server.serve_forever()
