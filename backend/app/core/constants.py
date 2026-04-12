"""
TaskTree 业务常量定义
====================
定义任务状态、优先级、项目状态、成员角色等枚举及对应的
中文标签映射、状态流转规则。
"""
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """任务优先级枚举"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemberRole(str, Enum):
    """项目成员角色枚举（与前端 constants/index.ts 保持一致）"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


# ---- 中文标签映射 ----

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

# ---- 状态流转规则 ----
# 定义每个状态允许转换到的目标状态列表。
# 在 tasks.py 的 update_task 中应调用 validate_status_transition() 校验。
VALID_STATUS_TRANSITIONS = {
    TaskStatus.PENDING: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
    TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.PENDING, TaskStatus.CANCELLED],
    TaskStatus.COMPLETED: [TaskStatus.PENDING],
    TaskStatus.CANCELLED: [TaskStatus.PENDING],
}