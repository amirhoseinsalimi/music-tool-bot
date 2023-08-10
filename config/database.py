from masoniteorm.connections import ConnectionResolver
from config.envs import DB_HOST, DB_PORT, DB_USERNAME, DB_NAME, DB_PASSWORD

DATABASES = {
    'default': 'mysql',
    'mysql': {
        'driver': 'mysql',
        'host': DB_HOST,
        'port': DB_PORT,
        'user': DB_USERNAME,
        'password': DB_PASSWORD,
        'database': DB_NAME,
        'prefix': ''
    }
}

DB = ConnectionResolver().set_connection_details(DATABASES)