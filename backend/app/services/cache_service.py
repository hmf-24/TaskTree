"""
缓存服务
=======
实现用户身份映射和任务列表的缓存
"""
import time
from typing import Optional, List, Dict, Any
from collections import defaultdict


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, value: Any, ttl: int):
        """
        初始化缓存条目
        
        Args:
            value: 缓存的值
            ttl: 生存时间（秒）
        """
        self.value = value
        self.timestamp = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.timestamp > self.ttl


class SimpleCache:
    """简单的内存缓存实现"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 默认生存时间（秒）
        """
        self.ttl = ttl
        self.cache: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回 None
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # 检查是否过期
        if entry.is_expired():
            del self.cache[key]
            return None
        
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），如果为 None 则使用默认值
        """
        if ttl is None:
            ttl = self.ttl
        
        self.cache[key] = CacheEntry(value, ttl)
    
    def delete(self, key: str):
        """
        删除缓存
        
        Args:
            key: 缓存键
        """
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()
    
    def cleanup(self):
        """清理过期的缓存条目"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
    
    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        total = len(self.cache)
        expired = sum(1 for entry in self.cache.values() if entry.is_expired())
        
        return {
            "total": total,
            "active": total - expired,
            "expired": expired
        }


class DingtalkUserMappingCache:
    """钉钉用户身份映射缓存"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 生存时间（秒），默认 5 分钟
        """
        self.cache = SimpleCache(ttl=ttl)
    
    def get_user_id(self, dingtalk_user_id: str) -> Optional[int]:
        """
        获取系统用户 ID
        
        Args:
            dingtalk_user_id: 钉钉用户 ID
            
        Returns:
            系统用户 ID，如果不存在则返回 None
        """
        key = f"dingtalk_user:{dingtalk_user_id}"
        return self.cache.get(key)
    
    def set_user_id(self, dingtalk_user_id: str, user_id: int):
        """
        设置用户 ID 映射
        
        Args:
            dingtalk_user_id: 钉钉用户 ID
            user_id: 系统用户 ID
        """
        key = f"dingtalk_user:{dingtalk_user_id}"
        self.cache.set(key, user_id)
    
    def delete_user_id(self, dingtalk_user_id: str):
        """
        删除用户 ID 映射
        
        Args:
            dingtalk_user_id: 钉钉用户 ID
        """
        key = f"dingtalk_user:{dingtalk_user_id}"
        self.cache.delete(key)
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()


class UserTaskListCache:
    """用户任务列表缓存"""
    
    def __init__(self, ttl: int = 60):
        """
        初始化缓存
        
        Args:
            ttl: 生存时间（秒），默认 1 分钟
        """
        self.cache = SimpleCache(ttl=ttl)
    
    def get_tasks(self, user_id: int) -> Optional[List[Any]]:
        """
        获取用户任务列表
        
        Args:
            user_id: 用户 ID
            
        Returns:
            任务列表，如果不存在则返回 None
        """
        key = f"user_tasks:{user_id}"
        return self.cache.get(key)
    
    def set_tasks(self, user_id: int, tasks: List[Any]):
        """
        设置用户任务列表
        
        Args:
            user_id: 用户 ID
            tasks: 任务列表
        """
        key = f"user_tasks:{user_id}"
        self.cache.set(key, tasks)
    
    def delete_tasks(self, user_id: int):
        """
        删除用户任务列表缓存
        
        Args:
            user_id: 用户 ID
        """
        key = f"user_tasks:{user_id}"
        self.cache.delete(key)
    
    def clear(self):
        """清空所有缓存"""
        self.cache.clear()


# 全局缓存实例
dingtalk_user_mapping_cache = DingtalkUserMappingCache(ttl=300)  # 5 分钟
user_task_list_cache = UserTaskListCache(ttl=60)  # 1 分钟
