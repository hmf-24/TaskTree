"""
频率限制服务
===========
实现基于用户的频率限制，防止滥用
"""
import time
from typing import Dict, Tuple
from collections import defaultdict


class RateLimiter:
    """频率限制器 - 基于内存的简单实现"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        初始化频率限制器
        
        Args:
            max_requests: 时间窗口内最多请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # 存储格式: {user_id: [(timestamp, count), ...]}
        self.requests: Dict[int, list] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Dict]:
        """
        检查用户是否允许发送请求
        
        Args:
            user_id: 用户 ID
            
        Returns:
            (是否允许, 限制信息字典)
        """
        now = time.time()
        
        # 清理过期的请求记录
        if user_id in self.requests:
            self.requests[user_id] = [
                (ts, count) for ts, count in self.requests[user_id]
                if now - ts < self.window_seconds
            ]
        
        # 获取当前窗口内的请求数
        current_count = sum(count for _, count in self.requests[user_id])
        
        # 检查是否超过限制
        if current_count >= self.max_requests:
            # 计算重置时间
            oldest_request = self.requests[user_id][0][0] if self.requests[user_id] else now
            reset_time = int(oldest_request + self.window_seconds)
            
            return False, {
                "limit": self.max_requests,
                "remaining": 0,
                "reset": reset_time,
                "retry_after": max(1, reset_time - int(now))
            }
        
        # 记录新请求
        if not self.requests[user_id]:
            self.requests[user_id].append((now, 1))
        else:
            # 检查是否在同一秒内
            last_ts, last_count = self.requests[user_id][-1]
            if now - last_ts < 1:
                self.requests[user_id][-1] = (last_ts, last_count + 1)
            else:
                self.requests[user_id].append((now, 1))
        
        # 重新计算当前计数
        current_count = sum(count for _, count in self.requests[user_id])
        
        return True, {
            "limit": self.max_requests,
            "remaining": self.max_requests - current_count,
            "reset": int(self.requests[user_id][0][0] + self.window_seconds),
            "retry_after": None
        }
    
    def get_status(self, user_id: int) -> Dict:
        """获取用户的限制状态"""
        now = time.time()
        
        # 清理过期的请求记录
        if user_id in self.requests:
            self.requests[user_id] = [
                (ts, count) for ts, count in self.requests[user_id]
                if now - ts < self.window_seconds
            ]
        
        current_count = sum(count for _, count in self.requests[user_id])
        
        if self.requests[user_id]:
            reset_time = int(self.requests[user_id][0][0] + self.window_seconds)
        else:
            reset_time = int(now + self.window_seconds)
        
        return {
            "limit": self.max_requests,
            "remaining": max(0, self.max_requests - current_count),
            "reset": reset_time,
            "current": current_count
        }
    
    def reset(self, user_id: int):
        """重置用户的限制"""
        if user_id in self.requests:
            del self.requests[user_id]


# 全局频率限制器实例
# 钉钉回调: 每分钟 10 次
dingtalk_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

# 绑定操作: 每分钟 5 次
bind_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)

# 测试消息: 每分钟 3 次
test_message_rate_limiter = RateLimiter(max_requests=3, window_seconds=60)
