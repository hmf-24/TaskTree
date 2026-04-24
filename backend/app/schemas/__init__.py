from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, Any
from datetime import datetime, date
from app.core.constants import TaskStatus, TaskPriority


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

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('密码长度至少8位')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含数字')
        if not any(c.isalpha() for c in v):
            raise ValueError('密码必须包含字母')
        return v


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
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_time: Optional[int] = None

    @field_validator('start_date', 'due_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None or isinstance(v, date):
            return v
        # 支持 YYYY-MM-DD 和 YYYY/MM/DD 格式
        s = str(v).strip()
        if '/' in s:
            return datetime.strptime(s, '%Y/%m/%d').date()
        return datetime.strptime(s, '%Y-%m-%d').date()

    @field_validator('priority', mode='before')
    @classmethod
    def normalize_priority(cls, v):
        if v is None:
            return 'medium'
        return str(v).lower()


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    estimated_time: Optional[int] = Field(default=None, ge=0)
    actual_time: Optional[int] = Field(default=None, ge=0)

    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        # 尝试从字符串转换
        try:
            return TaskStatus(v.lower())
        except ValueError:
            raise ValueError(f'无效的状态值: {v}')

    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v):
        if v is None:
            return v
        try:
            return TaskPriority(v.lower())
        except ValueError:
            raise ValueError(f'无效的优先级: {v}')

    @field_validator('start_date', 'due_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None or isinstance(v, date):
            return v
        s = str(v).strip()
        if '/' in s:
            return datetime.strptime(s, '%Y/%m/%d').date()
        return datetime.strptime(s, '%Y-%m-%d').date()


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


class AttachmentListResponse(BaseModel):
    """附件列表响应"""
    attachments: list[AttachmentResponse]
    total: int


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
    rules: Optional[Any] = None
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
    """通用消息响应"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


# ========== 钉钉相关 Schema ==========

class ParseResultSchema(BaseModel):
    """进度解析结果 Schema"""
    progress_type: str = Field(..., description="进度类型: completed/in_progress/problem/extend/query")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    keywords: list[str] = Field(default=[], description="提取的关键词")
    progress_value: int = Field(default=0, ge=0, le=100, description="进度百分比")
    problem_description: str = Field(default="", description="问题描述")
    extend_days: int = Field(default=0, ge=0, description="延期天数")
    raw_message: str = Field(..., description="原始消息")


class ProgressFeedbackCreate(BaseModel):
    """创建进度反馈请求"""
    task_id: int = Field(..., description="任务 ID")
    message_content: str = Field(..., description="消息内容")
    parsed_result: Optional[ParseResultSchema] = Field(None, description="解析结果")


class ProgressFeedbackResponse(BaseModel):
    """进度反馈响应"""
    id: int
    user_id: int
    task_id: int
    message_content: str
    parsed_result: Optional[dict]
    feedback_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DingtalkCallbackRequest(BaseModel):
    """钉钉回调请求 Schema"""
    msgtype: str = Field(..., description="消息类型")
    text: Optional[dict] = Field(None, description="文本消息")
    senderId: str = Field(..., description="发送者 ID")
    createAt: int = Field(..., description="创建时间戳")
    conversationId: Optional[str] = Field(None, description="会话 ID")


class DingtalkUserMappingCreate(BaseModel):
    """钉钉用户映射创建请求"""
    dingtalk_user_id: str = Field(..., description="钉钉用户 ID")
    dingtalk_name: str = Field(..., description="钉钉用户昵称")


class DingtalkUserMappingResponse(BaseModel):
    """钉钉用户映射响应"""
    user_id: int
    dingtalk_user_id: str
    dingtalk_name: str
    bound_at: datetime

    class Config:
        from_attributes = True


# ========== LLM 智能创建任务相关 ==========

class AIChatMessage(BaseModel):
    role: str
    content: str


class ClarifyTaskRequest(BaseModel):
    project_id: int
    messages: list[AIChatMessage]


class DecomposeTaskRequest(BaseModel):
    project_id: int
    requirement: str


class SubTaskItem(BaseModel):
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_time: Optional[int] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None


class TaskWithSubtasksCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[int] = None
    subtasks: list[SubTaskItem] = []


# ========== AI 对话记忆相关 ==========

class MessageSchema(BaseModel):
    """消息 Schema"""
    role: str = Field(..., description="角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    actions: Optional[list[dict[str, Any]]] = Field(None, description="可执行操作")


class ConversationCreate(BaseModel):
    """创建对话请求"""
    project_id: int = Field(..., description="项目 ID")
    conversation_type: str = Field(..., description="对话类型: create/analyze/modify/plan")
    task_id: Optional[int] = Field(None, description="任务 ID (修改模式)")
    initial_message: Optional[str] = Field(None, description="初始消息")


class ConversationResponse(BaseModel):
    """对话响应"""
    id: int
    user_id: int
    project_id: int
    task_id: Optional[int]
    conversation_type: str
    title: Optional[str]
    messages: list[MessageSchema]
    context_data: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """发送消息请求"""
    content: str = Field(..., description="消息内容")


class AIMessageResponse(BaseModel):
    """AI 对话消息响应"""
    reply: str = Field(..., description="AI 回复")
    conversation_id: int = Field(..., description="对话 ID")
    message_count: int = Field(..., description="消息总数")
    actions: Optional[list[dict[str, Any]]] = Field(None, description="可执行操作")


class AnalyzeRequest(BaseModel):
    """任务分析请求"""
    focus_areas: Optional[list[str]] = Field(None, description="关注领域")


class ModifyRequest(BaseModel):
    """任务修改请求"""
    modification: dict[str, Any] = Field(..., description="修改操作")


class PlanRequest(BaseModel):
    """项目规划请求"""
    planning_goal: Optional[str] = Field(None, description="规划目标")


# 更新前向引用
MemberResponse.model_rebuild()
CommentResponse.model_rebuild()
TaskDetailResponse.model_rebuild()