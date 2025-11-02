# redis_client.py
import json
import logging
from typing import Any, Optional, Union, List, Dict
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

logger = logging.getLogger(__name__)

class RedisClient:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 20,
        socket_timeout: int = 5,
        retry_on_timeout: bool = True,
        decode_responses: bool = True,
    ):
        if self._client is not None:
            return  # 避免重复初始化

        try:
            pool = redis.ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                retry_on_timeout=retry_on_timeout,
                decode_responses=decode_responses,
                encoding="utf-8"
            )
            self._client = redis.Redis(connection_pool=pool)
            # 测试连接
            self._client.ping()
            logger.info("✅ Redis connected successfully")
        except RedisError as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

    @property
    def client(self) -> redis.Redis:
        """获取原始 Redis 客户端（用于高级操作）"""
        return self._client

    # ======================
    # 基础键值操作
    # ======================

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置字符串值（自动 JSON 序列化非字符串类型）
        :param key: 键
        :param value: 值（支持 dict/list 等）
        :param ex: 过期时间（秒）
        """
        try:
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            self._client.set(key, value, ex=ex)
            return True
        except RedisError as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """获取值（自动反序列化 JSON）"""
        try:
            value = self._client.get(key)
            if value is None:
                return None
            # 尝试反序列化 JSON，失败则返回原字符串
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def delete(self, *keys: str) -> int:
        """删除一个或多个键"""
        try:
            return self._client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        try:
            return bool(self._client.expire(key, seconds))
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    # ======================
    # Hash 操作
    # ======================

    def hset(self, name: str, key: str, value: Any) -> bool:
        """设置 hash 字段"""
        try:
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            self._client.hset(name, key, value)
            return True
        except RedisError as e:
            logger.error(f"Redis HSET error: {e}")
            return False

    def hget(self, name: str, key: str) -> Optional[Any]:
        """获取 hash 字段"""
        try:
            value = self._client.hget(name, key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Redis HGET error: {e}")
            return None

    def hgetall(self, name: str) -> Dict[str, Any]:
        """获取整个 hash（自动反序列化）"""
        try:
            data = self._client.hgetall(name)
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            return result
        except RedisError as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    # ======================
    # List 操作
    # ======================

    def lpush(self, name: str, *values: Any) -> int:
        """从左侧插入列表"""
        serialized = []
        for v in values:
            serialized.append(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
        try:
            return self._client.lpush(name, *serialized)
        except RedisError as e:
            logger.error(f"Redis LPUSH error: {e}")
            return 0

    def rpop(self, name: str) -> Optional[Any]:
        """从右侧弹出列表元素"""
        try:
            value = self._client.rpop(name)
            if value is None:
                return None
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Redis RPOP error: {e}")
            return None

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            values = self._client.lrange(name, start, end)
            result = []
            for v in values:
                try:
                    result.append(json.loads(v))
                except (json.JSONDecodeError, TypeError):
                    result.append(v)
            return result
        except RedisError as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []

    # ======================
    # Set 操作
    # ======================

    def sadd(self, name: str, *values: Any) -> int:
        """向集合添加元素"""
        serialized = []
        for v in values:
            serialized.append(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
        try:
            return self._client.sadd(name, *serialized)
        except RedisError as e:
            logger.error(f"Redis SADD error: {e}")
            return 0

    def smembers(self, name: str) -> set:
        """获取集合所有成员"""
        try:
            members = self._client.smembers(name)
            result = set()
            for m in members:
                try:
                    result.add(json.loads(m))
                except (json.JSONDecodeError, TypeError):
                    result.add(m)
            return result
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    # ======================
    # 实用方法
    # ======================

    def get_or_set(self, key: str, default_func, ex: Optional[int] = None) -> Any:
        """
        缓存穿透防护：先读缓存，不存在则调用函数生成并写入
        :param key: 缓存键
        :param default_func: 无缓存时调用的函数（无参）
        :param ex: 过期时间
        """
        value = self.get(key)
        if value is not None:
            return value
        try:
            value = default_func()
            self.set(key, value, ex=ex)
            return value
        except Exception as e:
            logger.error(f"Failed to generate default value: {e}")
            return None

    def ping(self) -> bool:
        """检查 Redis 是否可用"""
        try:
            return self._client.ping()
        except RedisError:
            return False
        

# 创建 Redis 连接客户端
redis_cli = RedisClient(
    host="127.0.0.1",
    port=6379,
    db=0,
    password=None,
    max_connections=30
)