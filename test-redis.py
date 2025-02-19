import redis
r = redis.Redis(host='localhost', port=6379, db=0)
try:
    r.ping()
    print("Redis connection successful!")
except redis.ConnectionError:
    print("Redis connection failed!")