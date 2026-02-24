from masoniteorm.connections import ConnectionResolver

from config.envs import (
    DB_DATABASE,
    DB_HOST,
    DB_PASSWORD,
    DB_PORT,
    DB_USERNAME,
)

DATABASES = {
    'default': 'postgres',
    'postgres': {
        'driver': 'postgres',
        'host': DB_HOST,
        'port': DB_PORT,
        'database': DB_DATABASE,
        'user': DB_USERNAME,
        'password': DB_PASSWORD,
    },
}

DB = ConnectionResolver().set_connection_details(DATABASES)
