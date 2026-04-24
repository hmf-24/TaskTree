"""
安全日志服务
===========
记录所有安全相关的事件，包括验证失败、异常请求等
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class SecurityEventType(Enum):
    """安全事件类型"""
    SIGNATURE_VERIFICATION_FAILED = "signature_verification_failed"
    TIMESTAMP_EXPIRED = "timestamp_expired"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    PERMISSION_DENIED = "permission_denied"
    INVALID_REQUEST = "invalid_request"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    AUTHENTICATION_FAILED = "authentication_failed"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


class SecurityLogger:
    """安全日志记录器"""
    
    def __init__(self):
        """初始化安全日志记录器"""
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # 如果没有处理器，添加一个
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[int] = None,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "WARNING"
    ):
        """
        记录安全事件
        
        Args:
            event_type: 事件类型
            user_id: 用户 ID（如果已知）
            dingtalk_user_id: 钉钉用户 ID（如果已知）
            ip_address: IP 地址
            details: 事件详情
            severity: 严重程度（INFO, WARNING, ERROR, CRITICAL）
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "dingtalk_user_id": dingtalk_user_id,
            "ip_address": ip_address,
            "details": details or {}
        }
        
        log_message = self._format_log_message(log_data)
        
        # 根据严重程度记录日志
        if severity == "INFO":
            self.logger.info(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        elif severity == "ERROR":
            self.logger.error(log_message)
        elif severity == "CRITICAL":
            self.logger.critical(log_message)
    
    def _format_log_message(self, log_data: Dict[str, Any]) -> str:
        """格式化日志消息"""
        parts = [f"[{log_data['event_type']}]"]
        
        if log_data.get('user_id'):
            parts.append(f"user_id={log_data['user_id']}")
        
        if log_data.get('dingtalk_user_id'):
            parts.append(f"dingtalk_user_id={log_data['dingtalk_user_id']}")
        
        if log_data.get('ip_address'):
            parts.append(f"ip={log_data['ip_address']}")
        
        if log_data.get('details'):
            details_str = ", ".join([f"{k}={v}" for k, v in log_data['details'].items()])
            parts.append(f"details=({details_str})")
        
        return " | ".join(parts)
    
    def log_signature_verification_failed(
        self,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        """记录签名验证失败"""
        self.log_event(
            event_type=SecurityEventType.SIGNATURE_VERIFICATION_FAILED,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details={"timestamp": timestamp},
            severity="WARNING"
        )
    
    def log_timestamp_expired(
        self,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        timestamp: Optional[str] = None,
        age_seconds: Optional[float] = None
    ):
        """记录时间戳过期"""
        self.log_event(
            event_type=SecurityEventType.TIMESTAMP_EXPIRED,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details={"timestamp": timestamp, "age_seconds": age_seconds},
            severity="WARNING"
        )
    
    def log_rate_limit_exceeded(
        self,
        user_id: Optional[int] = None,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        limit: Optional[int] = None,
        retry_after: Optional[int] = None
    ):
        """记录频率限制超出"""
        self.log_event(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details={"limit": limit, "retry_after": retry_after},
            severity="WARNING"
        )
    
    def log_permission_denied(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None
    ):
        """记录权限拒绝"""
        self.log_event(
            event_type=SecurityEventType.PERMISSION_DENIED,
            user_id=user_id,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action
            },
            severity="WARNING"
        )
    
    def log_invalid_request(
        self,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        error: Optional[str] = None
    ):
        """记录无效请求"""
        self.log_event(
            event_type=SecurityEventType.INVALID_REQUEST,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details={"error": error},
            severity="INFO"
        )
    
    def log_suspicious_activity(
        self,
        user_id: Optional[int] = None,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        activity: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录可疑活动"""
        log_details = {"activity": activity}
        if details:
            log_details.update(details)
        
        self.log_event(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details=log_details,
            severity="ERROR"
        )
    
    def log_authentication_failed(
        self,
        dingtalk_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """记录认证失败"""
        self.log_event(
            event_type=SecurityEventType.AUTHENTICATION_FAILED,
            dingtalk_user_id=dingtalk_user_id,
            ip_address=ip_address,
            details={"reason": reason},
            severity="WARNING"
        )
    
    def log_unauthorized_access(
        self,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        """记录未授权访问"""
        self.log_event(
            event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            severity="ERROR"
        )


# 全局安全日志记录器实例
security_logger = SecurityLogger()
