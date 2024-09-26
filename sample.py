import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
redis_client.flushdb()
print(redis_client.hgetall('current_prices'))
