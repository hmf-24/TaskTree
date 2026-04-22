from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any
from datetime import datetime


# ========== 用户相关 ==========

class UserBase(BaseModel):
    email: EmailStr
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含字母')
        return v


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


# ========== 项目相关 ==========

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    status: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    task_count: int = 0
    completed_count: int = 0


class ProjectArchiveRequest(BaseModel):
    archived: bool


# ========== 项目成员相关 ==========

class MemberCreate(BaseModel):
    email: EmailStr
    role: str = "viewer"


class MemberUpdate(BaseModel):
    role: str


class MemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    created_at: datetime
    user: "UserResponse"


# ========== 任务相关 ==========

class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: str = "medium"
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_time: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    progress: Optional[int] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    estimated_time: Optional[int] = None
    actual_time: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    project_id: int
    status: str
    progress: int
    actual_time: Optional[int]
    sort_order: int
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(TaskResponse):
    children: list["TaskResponse"] = []
    tags: list = []
    dependencies: list = []


class TaskMoveRequest(BaseModel):
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class TaskDeleteQuery(BaseModel):
    delete_children: bool = False


class BatchTaskCreate(BaseModel):
    tasks: list[TaskCreate]


# ========== 依赖关系相关 ==========

class DependencyCreate(BaseModel):
    dependent_task_id: int


class DependencyResponse(BaseModel):
    id: int
    task_id: int
    dependent_task_id: int
    created_at: datetime


class DependencyCheckResponse(BaseModel):
    can_start: bool
    blocked_by: list[dict] = []


# ========== 标签相关 ==========

class TagBase(BaseModel):
    name: str
    color: Optional[str] = None


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


class TagResponse(TagBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskTagsRequest(BaseModel):
    tag_ids: list[int]


# ========== 评论相关 ==========

class CommentCreate(BaseModel):
    content: str
    mentions: Optional[list[int]] = None


class CommentResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime
    user: "UserResponse"

    class Config:
        from_attributes = True


# ========== 附件相关 ==========

class AttachmentResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    filename: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 通知相关 ==========

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: Optional[str]
    content: Optional[str]
    related_id: Optional[int]
    related_type: Optional[str]
    is_read: bool
    created_at: datetime


class NotificationReadRequest(BaseModel):
    is_read: bool = True


# ========== 智能提醒设置 ==========

class ReminderRule(BaseModel):
    """提醒规则"""
    id: str
    name: str
    enabled: bool = True
    condition: str  # due_date_remind, progress_stalled, dependency_unblocked, overdue_tasks
    hours_before: Optional[int] = None
    threshold_days: Optional[int] = None
    repeat: list[str] = []  # ["08:00", "20:00"] 或 ["immediate"]


class UserNotificationSettingsBase(BaseModel):
    dingtalk_webhook: Optional[str] = None
    dingtalk_secret: Optional[str] = None
    # 大模型配置
    llm_provider: Optional[str] = "minmax"  # minmax, openai, anthropic
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None  # 模型名称
    llm_group_id: Optional[str] = None  # Minmax Group ID
    # 分析维度配置
    analysis_config: Optional[dict] = None  # {"overdue": True, "progress_stalled": True, ...}
    rules: Optional[list[ReminderRule]] = None
    enabled: bool = True
    daily_limit: int = 5


class UserNotificationSettingsCreate(UserNotificationSettingsBase):
    pass


class UserNotificationSettingsUpdate(BaseModel):
    dingtalk_webhook: Optional[str] = None
    dingtalk_secret: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_group_id: Optional[str] = None
    rules: Optional[list[ReminderRule]] = None
    enabled: Optional[bool] = None
    daily_limit: Optional[int] = None


class UserNotificationSettingsResponse(UserNotificationSettingsBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ========== 通用响应 ==========

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class MessageResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


# 更新前向引用
MemberResponse.model_rebuild()
CommentResponse.model_rebuild()
TaskDetailResponse.model_rebuild()