"""
缓存服务测试
===========
测试缓存系统的功能和性能
"""
import pytest
import time
from app.services.cache_service import (
    SimpleCache,
    CacheEntry,
    DingtalkUserMappingCache,
    UserTaskListCache,
    dingtalk_user_mapping_cache,
    user_task_list_cache
)


class TestCacheEntry:
    """缓存条目测试"""
    
    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry("test_value", ttl=60)
        assert entry.value == "test_value"
        assert entry.ttl == 60
        assert entry.timestamp > 0
    
    def test_cache_entry_not_expired(self):
        """测试缓存条目未过期"""
        entry = CacheEntry("test_value", ttl=60)
        assert entry.is_expired() is False
    
    def test_cache_entry_expired(self):
        """测试缓存条目已过期"""
        entry = CacheEntry("test_value", ttl=1)
        time.sleep(1.1)
        assert entry.is_expired() is True


class TestSimpleCache:
    """简单缓存测试"""
    
    def test_cache_initialization(self):
        """测试缓存初始化"""
        cache = SimpleCache(ttl=300)
        assert cache.ttl == 300
        assert len(cache.cache) == 0
    
    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = SimpleCache(ttl=60)
        cache.set("key1", "value1")
        
        value = cache.get("key1")
        assert value == "value1"
    
    def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        cache = SimpleCache(ttl=60)
        value = cache.get("nonexistent")
        assert value is None
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        cache = SimpleCache(ttl=1)
        cache.set("key1", "value1")
        
        # 立即获取应该成功
        value = cache.get("key1")
        assert value == "value1"
        
        # 等待过期
        time.sleep(1.1)
        
        # 过期后应该返回 None
        value = cache.get("key1")
        assert value is None
    
    def test_cache_delete(self):
        """测试缓存删除"""
        cache = SimpleCache(ttl=60)
        cache.set("key1", "value1")
        
        # 删除前应该存在
        assert cache.get("key1") == "value1"
        
        # 删除
        cache.delete("key1")
        
        # 删除后应该不存在
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """测试清空缓存"""
        cache = SimpleCache(ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # 清空前应该有 2 个条目
        assert len(cache.cache) == 2
        
        # 清空
        cache.clear()
        
        # 清空后应该为空
        assert len(cache.cache) == 0
    
    def test_cache_cleanup(self):
        """测试清理过期缓存"""
        cache = SimpleCache(ttl=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=60)
        
        # 等待 key1 过期
        time.sleep(1.1)
        
        # 清理前应该有 2 个条目
        assert len(cache.cache) == 2
        
        # 清理
        cache.cleanup()
        
        # 清理后应该只有 1 个条目
        assert len(cache.cache) == 1
        assert cache.get("key2") == "value2"
    
    def test_cache_stats(self):
        """测试缓存统计"""
        cache = SimpleCache(ttl=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=60)
        
        # 等待 key1 过期
        time.sleep(1.1)
        
        stats = cache.get_stats()
        assert stats["total"] == 2
        assert stats["expired"] == 1
        assert stats["active"] == 1
    
    def test_cache_custom_ttl(self):
        """测试自定义 TTL"""
        cache = SimpleCache(ttl=60)
        cache.set("key1", "value1", ttl=1)
        
        # 立即获取应该成功
        assert cache.get("key1") == "value1"
        
        # 等待过期
        time.sleep(1.1)
        
        # 过期后应该返回 None
        assert cache.get("key1") is None


class TestDingtalkUserMappingCache:
    """钉钉用户映射缓存测试"""
    
    def test_user_mapping_cache_initialization(self):
        """测试用户映射缓存初始化"""
        cache = DingtalkUserMappingCache(ttl=300)
        assert cache.cache.ttl == 300
    
    def test_set_and_get_user_id(self):
        """测试设置和获取用户 ID"""
        cache = DingtalkUserMappingCache(ttl=60)
        cache.set_user_id("dingtalk_123", 456)
        
        user_id = cache.get_user_id("dingtalk_123")
        assert user_id == 456
    
    def test_get_nonexistent_user_id(self):
        """测试获取不存在的用户 ID"""
        cache = DingtalkUserMappingCache(ttl=60)
        user_id = cache.get_user_id("nonexistent")
        assert user_id is None
    
    def test_delete_user_id(self):
        """测试删除用户 ID"""
        cache = DingtalkUserMappingCache(ttl=60)
        cache.set_user_id("dingtalk_123", 456)
        
        # 删除前应该存在
        assert cache.get_user_id("dingtalk_123") == 456
        
        # 删除
        cache.delete_user_id("dingtalk_123")
        
        # 删除后应该不存在
        assert cache.get_user_id("dingtalk_123") is None
    
    def test_clear_user_mapping_cache(self):
        """测试清空用户映射缓存"""
        cache = DingtalkUserMappingCache(ttl=60)
        cache.set_user_id("dingtalk_123", 456)
        cache.set_user_id("dingtalk_789", 101)
        
        # 清空
        cache.clear()
        
        # 清空后应该都不存在
        assert cache.get_user_id("dingtalk_123") is None
        assert cache.get_user_id("dingtalk_789") is None


class TestUserTaskListCache:
    """用户任务列表缓存测试"""
    
    def test_task_list_cache_initialization(self):
        """测试任务列表缓存初始化"""
        cache = UserTaskListCache(ttl=60)
        assert cache.cache.ttl == 60
    
    def test_set_and_get_tasks(self):
        """测试设置和获取任务列表"""
        cache = UserTaskListCache(ttl=60)
        tasks = [{"id": 1, "name": "Task 1"}, {"id": 2, "name": "Task 2"}]
        cache.set_tasks(123, tasks)
        
        cached_tasks = cache.get_tasks(123)
        assert cached_tasks == tasks
    
    def test_get_nonexistent_tasks(self):
        """测试获取不存在的任务列表"""
        cache = UserTaskListCache(ttl=60)
        tasks = cache.get_tasks(999)
        assert tasks is None
    
    def test_delete_tasks(self):
        """测试删除任务列表"""
        cache = UserTaskListCache(ttl=60)
        tasks = [{"id": 1, "name": "Task 1"}]
        cache.set_tasks(123, tasks)
        
        # 删除前应该存在
        assert cache.get_tasks(123) == tasks
        
        # 删除
        cache.delete_tasks(123)
        
        # 删除后应该不存在
        assert cache.get_tasks(123) is None
    
    def test_clear_task_list_cache(self):
        """测试清空任务列表缓存"""
        cache = UserTaskListCache(ttl=60)
        cache.set_tasks(123, [{"id": 1}])
        cache.set_tasks(456, [{"id": 2}])
        
        # 清空
        cache.clear()
        
        # 清空后应该都不存在
        assert cache.get_tasks(123) is None
        assert cache.get_tasks(456) is None


class TestGlobalCacheInstances:
    """全局缓存实例测试"""
    
    def test_global_user_mapping_cache_config(self):
        """测试全局用户映射缓存配置"""
        assert dingtalk_user_mapping_cache.cache.ttl == 300  # 5 分钟
    
    def test_global_task_list_cache_config(self):
        """测试全局任务列表缓存配置"""
        assert user_task_list_cache.cache.ttl == 60  # 1 分钟


class TestCachePerformance:
    """缓存性能测试"""
    
    def test_cache_set_performance(self):
        """测试缓存设置性能"""
        cache = SimpleCache(ttl=60)
        
        start_time = time.time()
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        elapsed_time = time.time() - start_time
        
        # 1000 次设置应该在 100ms 内完成
        assert elapsed_time < 0.1
    
    def test_cache_get_performance(self):
        """测试缓存获取性能"""
        cache = SimpleCache(ttl=60)
        
        # 先设置 1000 个条目
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        
        start_time = time.time()
        for i in range(1000):
            cache.get(f"key_{i}")
        elapsed_time = time.time() - start_time
        
        # 1000 次获取应该在 100ms 内完成
        assert elapsed_time < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
