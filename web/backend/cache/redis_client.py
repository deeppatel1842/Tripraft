import redis

class RedisClient:
    def __init__(self):
        self._client = None

    def init_app(self, app):
        url = app.config.get('REDIS_URL')
        self._client = redis.from_url(url)

    def get_client(self):
        if self._client is None:
            raise RuntimeError('Redis client not initialized')
        return self._client

    def get(self, key):
        return self.get_client().get(key)

    def set(self, key, value, ex=None):
        return self.get_client().set(key, value, ex=ex)


redis_client = RedisClient()
