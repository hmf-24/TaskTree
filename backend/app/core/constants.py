"""
TaskTree 常量定义
"""
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# 状态标签映射
STATUS_LABELS = {
    TaskStatus.PENDING: "待办",
    TaskStatus.IN_PROGRESS: "进行中",
    TaskStatus.COMPLETED: "已完成",
    TaskStatus.CANCELLED: "已取消",
}

PRIORITY_LABELS = {
    TaskPriority.HIGH: "高",
    TaskPriority.MEDIUM: "中",
    TaskPriority.LOW: "低",
}

# 允许的状态流转
VALID_STATUS_TRANSITIONS = {
    TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.PENDING, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [TaskStatus.PENDING],
    TaskStatus.CANCELLED: [TaskStatus.PENDING],
}