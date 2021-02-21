import os
from orator import DatabaseManager

from dotenv import load_dotenv

load_dotenv(verbose=True)

DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else 'localhost'
DB_PORT = int(os.getenv("DB_PORT")) if int(os.getenv("DB_PORT")) else 3306
DB_USERNAME = os.getenv("DB_USERNAME") if os.getenv("DB_USERNAME") else ''
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else ''
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else ''

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

db = DatabaseManager(DATABASES)
