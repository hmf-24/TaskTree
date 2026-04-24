"""
钉钉用户身份映射服务
===================
提供钉钉用户 ID 与系统用户 ID 的映射管理功能。

功能：
- 创建用户绑定（绑定钉钉 ID 和系统用户）
- 查询用户映射（通过钉钉 ID 查找系统用户）
- 解除用户绑定
- 缓存机制（5 分钟 TTL）
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone

from app.models import User, UserNotificationSettings
from app.services.cache_service import SimpleCache


class DingtalkUserMappingService:
    """钉钉用户身份映射服务"""

    def __init__(self, db: Session):
        self.db = db
        self.cache = SimpleCache(ttl=300)  # 5 分钟

    def bind_user(
        self,
        user_id: int,
        dingtalk_user_id: str,
        dingtalk_name: Optional[str] = None
    ) -> bool:
        """
        绑定钉钉用户和系统用户
        
        Args:
            user_id: 系统用户 ID
            dingtalk_user_id: 钉钉用户 ID
            dingtalk_name: 钉钉用户昵称（可选）
            
        Returns:
            bool: 绑定是否成功
            
        Raises:
            ValueError: 如果钉钉 ID 已被其他用户绑定
        """
        # 检查钉钉 ID 是否已被绑定
        existing = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.dingtalk_user_id == dingtalk_user_id
            )
        ).scalar_one_or_none()
        
        if existing and existing.user_id != user_id:
            raise ValueError(f"钉钉用户 ID {dingtalk_user_id} 已被其他用户绑定")
        
        # 获取或创建用户通知设置
        settings = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        ).scalar_one_or_none()
        
        if not settings:
            settings = UserNotificationSettings(user_id=user_id)
            self.db.add(settings)
        
        # 更新钉钉信息
        settings.dingtalk_user_id = dingtalk_user_id
        settings.dingtalk_name = dingtalk_name
        settings.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        # 更新缓存
        cache_key = f"dingtalk_user_mapping:{dingtalk_user_id}"
        self.cache.set(cache_key, user_id)
        
        return True

    def get_user_id(self, dingtalk_user_id: str) -> Optional[int]:
        """
        通过钉钉用户 ID 查找系统用户 ID
        
        Args:
            dingtalk_user_id: 钉钉用户 ID
            
        Returns:
            Optional[int]: 系统用户 ID，未找到返回 None
        """
        # 先查缓存
        cache_key = f"dingtalk_user_mapping:{dingtalk_user_id}"
        cached_user_id = self.cache.get(cache_key)
        
        if cached_user_id is not None:
            return cached_user_id
        
        # 缓存未命中，查数据库
        settings = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.dingtalk_user_id == dingtalk_user_id
            )
        ).scalar_one_or_none()
        
        if settings:
            user_id = settings.user_id
            # 写入缓存
            self.cache.set(cache_key, user_id)
            return user_id
        
        return None

    def get_dingtalk_info(self, user_id: int) -> Optional[dict]:
        """
        获取用户的钉钉绑定信息
        
        Args:
            user_id: 系统用户 ID
            
        Returns:
            Optional[dict]: 钉钉信息字典，包含 dingtalk_user_id 和 dingtalk_name
        """
        settings = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        ).scalar_one_or_none()
        
        if settings and settings.dingtalk_user_id:
            return {
                "dingtalk_user_id": settings.dingtalk_user_id,
                "dingtalk_name": settings.dingtalk_name
            }
        
        return None

    def unbind_user(self, user_id: int) -> bool:
        """
        解除用户的钉钉绑定
        
        Args:
            user_id: 系统用户 ID
            
        Returns:
            bool: 解除绑定是否成功
        """
        settings = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        ).scalar_one_or_none()
        
        if not settings or not settings.dingtalk_user_id:
            return False
        
        # 清除缓存
        cache_key = f"dingtalk_user_mapping:{settings.dingtalk_user_id}"
        self.cache.delete(cache_key)
        
        # 清除钉钉信息
        settings.dingtalk_user_id = None
        settings.dingtalk_name = None
        settings.updated_at = datetime.now(timezone.utc)
        
        self.db.commit()
        
        return True

    def is_bound(self, user_id: int) -> bool:
        """
        检查用户是否已绑定钉钉
        
        Args:
            user_id: 系统用户 ID
            
        Returns:
            bool: 是否已绑定
        """
        settings = self.db.execute(
            select(UserNotificationSettings).where(
                UserNotificationSettings.user_id == user_id
            )
        ).scalar_one_or_none()
        
        return bool(settings and settings.dingtalk_user_id)
