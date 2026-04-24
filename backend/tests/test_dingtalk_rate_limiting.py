"""
钉钉 API 频率限制和权限验证测试
==============================
测试频率限制、权限验证和安全性保障
"""
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rate_limiter import (
    RateLimiter,
    dingtalk_rate_limiter,
    bind_rate_limiter,
    test_message_rate_limiter
)


class TestRateLimiter:
    """频率限制器单元测试"""
    
    def test_rate_limiter_initialization(self):
        """测试频率限制器初始化"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.max_requests == 10
        assert limiter.window_seconds == 60
        assert len(limiter.requests) == 0
    
    def test_single_request_allowed(self):
        """测试单个请求被允许"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        user_id = 1
        
        is_allowed, info = limiter.is_allowed(user_id)
        
        assert is_allowed is True
        assert info["limit"] == 10
        assert info["remaining"] == 9
        assert info["retry_after"] is None
    
    def test_multiple_requests_within_limit(self):
        """测试多个请求在限制内"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        user_id = 1
        
        for i in range(5):
            is_allowed, info = limiter.is_allowed(user_id)
            assert is_allowed is True
            assert info["remaining"] == 4 - i
    
    def test_request_exceeds_limit(self):
        """测试请求超过限制"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        user_id = 1
        
        # 发送 3 个请求（达到限制）
        for i in range(3):
            is_allowed, info = limiter.is_allowed(user_id)
            assert is_allowed is True
        
        # 第 4 个请求应该被拒绝
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] is not None
        assert info["retry_after"] > 0
    
    def test_rate_limit_reset_after_window(self):
        """测试时间窗口后限制重置"""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        user_id = 1
        
        # 发送 2 个请求
        for i in range(2):
            is_allowed, info = limiter.is_allowed(user_id)
            assert is_allowed is True
        
        # 第 3 个请求被拒绝
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is False
        
        # 等待窗口过期
        time.sleep(1.1)
        
        # 现在应该允许新请求
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is True
    
    def test_different_users_independent_limits(self):
        """测试不同用户的限制独立"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # 用户 1 发送 2 个请求
        for i in range(2):
            is_allowed, info = limiter.is_allowed(1)
            assert is_allowed is True
        
        # 用户 1 的第 3 个请求被拒绝
        is_allowed, info = limiter.is_allowed(1)
        assert is_allowed is False
        
        # 用户 2 应该能发送请求
        is_allowed, info = limiter.is_allowed(2)
        assert is_allowed is True
        
        is_allowed, info = limiter.is_allowed(2)
        assert is_allowed is True
        
        # 用户 2 的第 3 个请求也被拒绝
        is_allowed, info = limiter.is_allowed(2)
        assert is_allowed is False
    
    def test_get_status(self):
        """测试获取限制状态"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        user_id = 1
        
        # 发送 2 个请求
        for i in range(2):
            limiter.is_allowed(user_id)
        
        status = limiter.get_status(user_id)
        
        assert status["limit"] == 5
        assert status["remaining"] == 3
        assert status["current"] == 2
        assert status["reset"] > 0
    
    def test_reset_user_limit(self):
        """测试重置用户限制"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        user_id = 1
        
        # 发送 2 个请求
        for i in range(2):
            limiter.is_allowed(user_id)
        
        # 第 3 个请求被拒绝
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is False
        
        # 重置限制
        limiter.reset(user_id)
        
        # 现在应该允许新请求
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is True
    
    def test_concurrent_requests_same_second(self):
        """测试同一秒内的并发请求"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        user_id = 1
        
        # 模拟同一秒内的多个请求
        for i in range(5):
            is_allowed, info = limiter.is_allowed(user_id)
            assert is_allowed is True
        
        status = limiter.get_status(user_id)
        assert status["current"] == 5
        assert status["remaining"] == 5


class TestGlobalRateLimiters:
    """全局频率限制器测试"""
    
    def test_dingtalk_rate_limiter_config(self):
        """测试钉钉回调频率限制器配置"""
        assert dingtalk_rate_limiter.max_requests == 10
        assert dingtalk_rate_limiter.window_seconds == 60
    
    def test_bind_rate_limiter_config(self):
        """测试绑定操作频率限制器配置"""
        assert bind_rate_limiter.max_requests == 5
        assert bind_rate_limiter.window_seconds == 60
    
    def test_test_message_rate_limiter_config(self):
        """测试消息频率限制器配置"""
        assert test_message_rate_limiter.max_requests == 3
        assert test_message_rate_limiter.window_seconds == 60


class TestRateLimitingProperties:
    """频率限制属性测试"""
    
    def test_property_rate_limit_enforcement(self):
        """
        属性 11: 频率限制的强制性
        
        对于任何用户，在一分钟内超过 10 次请求应该被拒绝。
        """
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        user_id = 1
        
        # 发送 10 个请求（应该全部被允许）
        for i in range(10):
            is_allowed, info = limiter.is_allowed(user_id)
            assert is_allowed is True, f"请求 {i+1} 应该被允许"
        
        # 第 11 个请求应该被拒绝
        is_allowed, info = limiter.is_allowed(user_id)
        assert is_allowed is False, "第 11 个请求应该被拒绝"
        assert info["remaining"] == 0
        assert info["retry_after"] is not None
    
    def test_property_rate_limit_consistency(self):
        """
        属性: 频率限制的一致性
        
        对于同一用户，限制状态应该始终一致。
        """
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        user_id = 1
        
        # 发送 3 个请求
        for i in range(3):
            limiter.is_allowed(user_id)
        
        # 多次获取状态应该返回相同的结果
        status1 = limiter.get_status(user_id)
        status2 = limiter.get_status(user_id)
        
        assert status1["current"] == status2["current"]
        assert status1["remaining"] == status2["remaining"]
        assert status1["limit"] == status2["limit"]
    
    def test_property_rate_limit_isolation(self):
        """
        属性: 用户隔离
        
        一个用户的限制不应该影响其他用户。
        """
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # 用户 1 达到限制
        for i in range(2):
            limiter.is_allowed(1)
        
        is_allowed, _ = limiter.is_allowed(1)
        assert is_allowed is False
        
        # 用户 2 应该不受影响
        is_allowed, _ = limiter.is_allowed(2)
        assert is_allowed is True
        
        is_allowed, _ = limiter.is_allowed(2)
        assert is_allowed is True
        
        is_allowed, _ = limiter.is_allowed(2)
        assert is_allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
