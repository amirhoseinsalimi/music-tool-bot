import os
import env
import mysql.connector

DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else 'localhost'
DB_PORT = int(os.getenv("DB_PORT")) if int(os.getenv("DB_PORT")) else 3306
DB_USERNAME = os.getenv("DB_USERNAME") if os.getenv("DB_USERNAME") else ''
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else ''
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else ''

OWNER_USER_ID = os.getenv("ADMIN_USER_ID") if os.getenv("OWNER_USER_ID") else ''

connection = mysql.connector.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USERNAME,
    password=DB_PASSWORD,
    database=DB_NAME
)

cursor = connection.cursor(buffered=True)

cursor.execute("CREATE TABLE IF NOT EXISTS `users` (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT UNIQUE)")
cursor.execute("CREATE TABLE IF NOT EXISTS `admins` "
               "(id INT AUTO_INCREMENT PRIMARY KEY, user_id INT UNIQUE, is_owner boolean DEFAULT false)")

if OWNER_USER_ID:
    cursor.execute(f"INSERT IGNORE INTO `admins` (`user_id`, `is_owner`) VALUES ({OWNER_USER_ID}, true)")
