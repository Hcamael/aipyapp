import sqlite3
import time
import json
import threading
import hashlib
import functools
from typing import Any, Optional, Callable, Union
from pathlib import Path
from .config import CONFIG_DIR

CACHE_FILE = CONFIG_DIR / "cache.db"


class KVCache:
    """基于SQLite的KV缓存类"""

    def __init__(self, db_path: str = "cache.db", default_ttl: int = 3600):
        """
        初始化缓存

        Args:
            db_path: SQLite数据库文件路径
            default_ttl: 默认过期时间（秒）
        """
        self.db_path = db_path
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    expire_time REAL,
                    created_time REAL
                )
            ''')
            conn.execute(
                'CREATE INDEX IF NOT EXISTS idx_expire_time ON cache(expire_time)'
            )
            conn.commit()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示使用默认TTL
        """
        with self._lock:
            current_time = time.time()
            expire_time = current_time + (ttl or self.default_ttl)

            # 序列化值
            try:
                serialized_value = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                raise ValueError(f"无法序列化值: {e}")

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    'INSERT OR REPLACE INTO cache (key, value, expire_time, created_time) VALUES (?, ?, ?, ?)',
                    (key, serialized_value, expire_time, current_time),
                )
                conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存

        Args:
            key: 缓存键
            default: 默认值

        Returns:
            缓存值或默认值
        """
        with self._lock:
            current_time = time.time()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT value, expire_time FROM cache WHERE key = ?', (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    return default

                value, expire_time = row
                if current_time > expire_time:
                    # 删除过期缓存
                    conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                    conn.commit()
                    return default

                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return default

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('DELETE FROM cache WHERE key = ?', (key,))
                conn.commit()
                return cursor.rowcount > 0

    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在且未过期

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        return self.get(key) is not None

    def expire(self, key: str, ttl: int) -> bool:
        """
        设置缓存过期时间

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        with self._lock:
            current_time = time.time()
            expire_time = current_time + ttl

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'UPDATE cache SET expire_time = ? WHERE key = ?', (expire_time, key)
                )
                conn.commit()
                return cursor.rowcount > 0

    def ttl(self, key: str) -> int:
        """
        获取缓存剩余过期时间

        Args:
            key: 缓存键

        Returns:
            剩余时间（秒），-1表示不存在，-2表示永不过期
        """
        with self._lock:
            current_time = time.time()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT expire_time FROM cache WHERE key = ?', (key,)
                )
                row = cursor.fetchone()

                if row is None:
                    return -1

                expire_time = row[0]
                if current_time > expire_time:
                    return -1

                return int(expire_time - current_time)

    def cleanup(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的缓存数量
        """
        with self._lock:
            current_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'DELETE FROM cache WHERE expire_time < ?', (current_time,)
                )
                conn.commit()
                return cursor.rowcount

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM cache')
                conn.commit()

    def size(self) -> int:
        """获取缓存数量"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM cache')
            return cursor.fetchone()[0]

    def keys(self) -> list:
        """获取所有有效缓存键"""
        with self._lock:
            current_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT key FROM cache WHERE expire_time > ?', (current_time,)
                )
                return [row[0] for row in cursor.fetchall()]

    def stats(self) -> dict:
        """获取缓存统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                '''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN expire_time > ? THEN 1 END) as valid,
                    COUNT(CASE WHEN expire_time <= ? THEN 1 END) as expired
                FROM cache
            ''',
                (time.time(), time.time()),
            )

            row = cursor.fetchone()
            return {'total': row[0], 'valid': row[1], 'expired': row[2]}


# 全局缓存实例
_default_cache = None


def get_default_cache() -> KVCache:
    """获取默认缓存实例"""
    global _default_cache
    if _default_cache is None:
        _default_cache = KVCache(str(CACHE_FILE))
    return _default_cache


def cache_key(*args, **kwargs) -> str:
    """生成缓存键"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
    cache_instance: Optional[KVCache] = None,
):
    """
    缓存装饰器

    Args:
        ttl: 缓存过期时间（秒）
        key_func: 自定义键生成函数
        cache_instance: 缓存实例，None表示使用默认实例
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取缓存实例
            cache = cache_instance or get_default_cache()

            # 生成缓存键
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__name__}"
                key = f"{func_name}:{cache_key(*args, **kwargs)}"

            # 尝试从缓存获取
            result = cache.get(key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        # 添加缓存操作方法
        setattr(
            wrapper,
            'cache_clear',
            lambda: cache_instance.clear()
            if cache_instance
            else get_default_cache().clear(),
        )
        setattr(
            wrapper,
            'cache_info',
            lambda: cache_instance.stats()
            if cache_instance
            else get_default_cache().stats(),
        )

        return wrapper

    return decorator


# 便捷函数
def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """设置缓存"""
    get_default_cache().set(key, value, ttl)


def get_cache(key: str, default: Any = None) -> Any:
    """获取缓存"""
    return get_default_cache().get(key, default)


def delete_cache(key: str) -> bool:
    """删除缓存"""
    return get_default_cache().delete(key)


def clear_cache() -> None:
    """清空缓存"""
    get_default_cache().clear()


def cache_exists(key: str) -> bool:
    """检查缓存是否存在"""
    return get_default_cache().exists(key)


def cache_ttl(key: str) -> int:
    """获取缓存TTL"""
    return get_default_cache().ttl(key)


def cleanup_cache() -> int:
    """清理过期缓存"""
    return get_default_cache().cleanup()


def cache_stats() -> dict:
    """获取缓存统计"""
    return get_default_cache().stats()


cleanup_cache()
