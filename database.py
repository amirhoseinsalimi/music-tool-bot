import os
import env
import mysql.connector
from sqlalchemy import create_engine, MetaData, Table, Integer, String, Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import time

DB_HOST = os.getenv("DB_HOST") if os.getenv("DB_HOST") else 'localhost'
DB_PORT = int(os.getenv("DB_PORT")) if int(os.getenv("DB_PORT")) else 3306
DB_USERNAME = os.getenv("DB_USERNAME") if os.getenv("DB_USERNAME") else ''
DB_PASSWORD = os.getenv("DB_PASSWORD") if os.getenv("DB_PASSWORD") else ''
DB_NAME = os.getenv("DB_NAME") if os.getenv("DB_NAME") else ''

OWNER_USER_ID = os.getenv("ADMIN_USER_ID") if os.getenv("OWNER_USER_ID") else 0
OWNER_USER_ID = int(OWNER_USER_ID)
print(type(OWNER_USER_ID))

CONNECTION_STRING = f"mysql://{DB_USERNAME}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    CONNECTION_STRING,
    pool_size=20,
    dialect='mysql',
    echo=True
)

MetaData().create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column('id', Integer, primary_key=True, unique=True, nullable=False)
    user_id = Column('user_id', Integer, unique=True, nullable=False)
    number_of_files_sent = Column('number_of_files_sent', Integer, default=0, nullable=False)

    def __init__(self, user_id: int, number_of_files_sent: int = 0):
        self.user_id = user_id
        self.number_of_files_sent = number_of_files_sent


class Admin(Base):
    __tablename__ = 'admins'

    id = Column('id', Integer, primary_key=True, unique=True, autoincrement=True, nullable=False)
    admin_id = Column('admin_id', Integer, unique=True, nullable=False)

    def __init__(self, admin_id):
        self.admin_id = admin_id


owner = session.query(Admin) \
    .filter(Admin.admin_id == OWNER_USER_ID) \
    .first()

if owner:
    print('A')
    print(owner)
else:
    print('B')
    admin = Admin(OWNER_USER_ID)
    session.add(admin)

session.commit()
session.close()
