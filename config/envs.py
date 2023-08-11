import os

from dotenv import load_dotenv

load_dotenv(verbose=True)

BOT_USERNAME = os.getenv('BOT_USERNAME')
BOT_TOKEN = os.getenv('BOT_TOKEN')

OWNER_USER_ID = os.getenv("OWNER_USER_ID") if os.getenv("OWNER_USER_ID") else 0
OWNER_USER_ID_INT = int(OWNER_USER_ID)

DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else 'localhost'
DB_PORT = int(os.getenv("DB_PORT")) if int(os.getenv("DB_PORT")) else 3306
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else ''
DB_USERNAME = os.getenv("DB_USERNAME") if os.getenv("DB_USERNAME") else ''
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else ''
