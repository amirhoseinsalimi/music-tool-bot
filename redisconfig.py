import os
import redis
import env
from redispersistence.persistence import RedisPersistence

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=os.getenv("REDIS_PORT"),
    db=1,
    client_name=os.getenv("APP_NAME"),
    password=os.getenv("REDIS_PASSWORD")
)
persistence = RedisPersistence(redis_client)
