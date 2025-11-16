



class CacheManager():
    def __init__(self):
        self.redis_cli = redis_cli

    def get_cache(self, key: str):
        return self.redis_cli.get(key)

    def set_cache(self, key: str, value: any):
        return self.redis_cli.set(key, value)

    def delete_cache(self, key: str):
        return self.redis_cli.delete(key)