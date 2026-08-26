from __future__ import annotations

import json
import time
from typing import Any, Optional


class SimpleCache:
    """
    简单的内存缓存实现
    用于存储AI模型响应和岗位数据
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600) -> None:
        """
        初始化缓存
        max_size: 缓存最大容量
        ttl: 缓存过期时间（秒）
        """
        self.cache: dict[str, tuple[Any, float]] = {}
        self.max_size = max_size
        self.ttl = ttl
    
    def _is_expired(self, timestamp: float) -> bool:
        """
        检查缓存是否过期
        """
        return time.time() - timestamp > self.ttl
    
    def _clean_expired(self) -> None:
        """
        清理过期缓存
        """
        expired_keys = [k for k, (_, ts) in self.cache.items() if self._is_expired(ts)]
        for k in expired_keys:
            del self.cache[k]
    
    def _ensure_space(self) -> None:
        """
        确保缓存有足够空间
        """
        if len(self.cache) >= self.max_size:
            # 清理过期缓存
            self._clean_expired()
            # 如果还是满的，删除最早的缓存
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
                del self.cache[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        """
        self._clean_expired()
        if key in self.cache:
            value, _ = self.cache[key]
            return value
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存
        """
        self._ensure_space()
        self.cache[key] = (value, time.time())
    
    def delete(self, key: str) -> None:
        """
        删除缓存
        """
        if key in self.cache:
            del self.cache[key]
    
    def clear(self) -> None:
        """
        清空缓存
        """
        self.cache.clear()


# 创建全局缓存实例
cache = SimpleCache(max_size=2000, ttl=7200)  # 2小时过期


def get_cache_key(prefix: str, *args) -> str:
    """
    生成缓存键
    """
    parts = [prefix] + [str(arg) for arg in args]
    return "_".join(parts)


def cache_ai_response(prompt: str, response: Any) -> None:
    """
    缓存AI响应
    """
    key = get_cache_key("ai_response", prompt)
    cache.set(key, response)


def get_cached_ai_response(prompt: str) -> Optional[Any]:
    """
    获取缓存的AI响应
    """
    key = get_cache_key("ai_response", prompt)
    return cache.get(key)


def cache_job_profile(job_id: int, profile: dict[str, Any]) -> None:
    """
    缓存岗位画像
    """
    key = get_cache_key("job_profile", job_id)
    cache.set(key, profile)


def get_cached_job_profile(job_id: int) -> Optional[dict[str, Any]]:
    """
    获取缓存的岗位画像
    """
    key = get_cache_key("job_profile", job_id)
    return cache.get(key)


def cache_match_result(student_id: int, job_id: int, result: dict[str, Any]) -> None:
    """
    缓存匹配结果
    """
    key = get_cache_key("match_result", student_id, job_id)
    cache.set(key, result)


def get_cached_match_result(student_id: int, job_id: int) -> Optional[dict[str, Any]]:
    """
    获取缓存的匹配结果
    """
    key = get_cache_key("match_result", student_id, job_id)
    return cache.get(key)


def cache_learning_plan(student_id: int, job_id: int, plan: dict[str, Any]) -> None:
    """
    缓存学习计划
    """
    key = get_cache_key("learning_plan", student_id, job_id)
    cache.set(key, plan)


def get_cached_learning_plan(student_id: int, job_id: int) -> Optional[dict[str, Any]]:
    """
    获取缓存的学习计划
    """
    key = get_cache_key("learning_plan", student_id, job_id)
    return cache.get(key)