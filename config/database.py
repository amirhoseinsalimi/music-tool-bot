from masoniteorm.connections import ConnectionResolver

from config.envs import DB_NAME

DATABASES = {
    'default': 'sqlite',
    'sqlite': {
        'driver': 'sqlite',
        'database': DB_NAME,
    }
}

DB = ConnectionResolver().set_connection_details(DATABASES)
