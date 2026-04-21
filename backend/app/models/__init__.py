"""
TaskTree 数据库模型定义
======================
本模块定义了 TaskTree 系统的所有 SQLAlchemy ORM 模型。
包含 10 张核心表：users, projects, project_members, tasks,
task_dependencies, task_tags, task_tag_relations, task_comments,
task_attachments, notifications, operation_logs。

Base 在此处统一定义，其他模块（如 database.py）从此处导入，
避免多次创建 Base 实例导致 mapper 关联失效。
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类（2.0 风格）"""
    pass


class User(Base):
    """用户表 - 存储系统注册用户的基本信息和凭证。"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True, comment="登录邮箱，全局唯一")
    password_hash = Column(String(255), nullable=False, comment="bcrypt 加密后的密码哈希")
    nickname = Column(String(100), comment="用户昵称，用于界面展示")
    avatar = Column(String(500), comment="头像 URL 或路径")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    owned_projects = relationship('Project', back_populates='owner')
    assigned_tasks = relationship('Task', back_populates='assignee')
    comments = relationship('TaskComment', back_populates='user')
    notifications = relationship('Notification', back_populates='user')


class Project(Base):
    """项目表 - 任务树的顶层组织单位，每个项目可包含多个任务树。"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="项目名称")
    description = Column(Text, comment="项目描述")
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="项目所有者用户 ID")
    start_date = Column(Date, comment="项目开始日期")
    end_date = Column(Date, comment="项目截止日期")
    status = Column(String(20), default='active', index=True, comment="项目状态: active / archived / deleted")
    is_archived = Column(Boolean, default=False, comment="是否已归档")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    owner = relationship('User', back_populates='owned_projects')
    members = relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    tasks = relationship('Task', back_populates='project', cascade='all, delete-orphan')
    tags = relationship('TaskTag', back_populates='project', cascade='all, delete-orphan')


class ProjectMember(Base):
    """项目成员表 - 记录项目与用户的多对多关系及角色。"""
    __tablename__ = 'project_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), default='viewer', comment="成员角色: owner / admin / member / viewer")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('project_id', 'user_id'),)

    project = relationship('Project', back_populates='members')
    user = relationship('User')


class Task(Base):
    """任务表 - 核心数据模型，支持无限层级的树形结构（通过 parent_id 自引用）。"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), index=True, comment="父任务 ID，NULL 表示根任务")
    name = Column(String(255), nullable=False, comment="任务名称")
    description = Column(Text, comment="任务描述")
    assignee_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True, comment="负责人用户 ID")
    status = Column(String(20), default='pending', index=True, comment="任务状态: pending / in_progress / completed / cancelled")
    priority = Column(String(10), default='medium', comment="优先级: high / medium / low")
    progress = Column(Integer, default=0, comment="进度百分比 0-100")
    estimated_time = Column(Integer, comment="预计耗时（分钟）")
    actual_time = Column(Integer, comment="实际耗时（分钟）")
    start_date = Column(Date, comment="开始日期")
    due_date = Column(Date, comment="截止日期")
    sort_order = Column(Integer, default=0, index=True, comment="同级任务排序序号，数值越小越靠前")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    project = relationship('Project', back_populates='tasks')
    parent = relationship('Task', remote_side=[id], backref='children')
    assignee = relationship('User', back_populates='assigned_tasks')
    dependencies_from = relationship('TaskDependency', foreign_keys='TaskDependency.task_id', back_populates='task')
    dependencies_to = relationship('TaskDependency', foreign_keys='TaskDependency.dependent_task_id', back_populates='dependent_task')
    comments = relationship('TaskComment', back_populates='task', cascade='all, delete-orphan')
    attachments = relationship('TaskAttachment', back_populates='task', cascade='all, delete-orphan')
    tag_relations = relationship('TaskTagRelation', back_populates='task', cascade='all, delete-orphan')


class TaskDependency(Base):
    """任务依赖关系表 - 记录任务间的前置依赖（A 完成后 B 才能开始）。"""
    __tablename__ = 'task_dependencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True, comment="前置任务 ID（被依赖方）")
    dependent_task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True, comment="后续任务 ID（依赖方）")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('task_id', 'dependent_task_id'),)

    task = relationship('Task', foreign_keys=[task_id], back_populates='dependencies_from')
    dependent_task = relationship('Task', foreign_keys=[dependent_task_id], back_populates='dependencies_to')


class TaskTag(Base):
    """任务标签表 - 项目级别的彩色标签定义。"""
    __tablename__ = 'task_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(50), nullable=False, comment="标签名称")
    color = Column(String(20), comment="标签颜色（HEX 格式如 #f5222d）")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('project_id', 'name'),)

    project = relationship('Project', back_populates='tags')
    relations = relationship('TaskTagRelation', back_populates='tag')


class TaskTagRelation(Base):
    """任务-标签关联表 - 多对多关联（复合主键）。"""
    __tablename__ = 'task_tag_relations'

    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('task_tags.id', ondelete='CASCADE'), primary_key=True)

    task = relationship('Task', back_populates='tag_relations')
    tag = relationship('TaskTag', back_populates='relations')


class TaskComment(Base):
    """任务评论表 - 存储任务下的讨论和评论内容。"""
    __tablename__ = 'task_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False, comment="评论文本内容")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship('Task', back_populates='comments')
    user = relationship('User', back_populates='comments')


class TaskAttachment(Base):
    """任务附件表 - 存储上传文件的元数据（文件本身存储在文件系统中）。"""
    __tablename__ = 'task_attachments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="服务器存储路径")
    file_size = Column(Integer, comment="文件大小（字节）")
    mime_type = Column(String(100), comment="MIME 类型如 image/png")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship('Task', back_populates='attachments')


class Notification(Base):
    """通知表 - 存储用户的系统通知（任务变更、评论、@提及等）。"""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    type = Column(String(50), nullable=False, comment="通知类型: task_status / task_assign / comment / mention")
    title = Column(String(255), comment="通知标题")
    content = Column(Text, comment="通知正文")
    related_id = Column(Integer, comment="关联对象 ID（如任务 ID）")
    related_type = Column(String(50), comment="关联对象类型: task / project / comment")
    is_read = Column(Boolean, default=False, comment="是否已读")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship('User', back_populates='notifications')


class OperationLog(Base):
    """操作日志表 - 记录用户对项目/任务的所有变更操作，用于审计追踪。"""
    __tablename__ = 'operation_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="操作者用户 ID")
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), index=True, comment="关联项目 ID")
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='SET NULL'), index=True, comment="关联任务 ID")
    action = Column(String(50), nullable=False, comment="操作类型: create / update / delete / move 等")
    old_value = Column(Text, comment="变更前的值（JSON 格式）")
    new_value = Column(Text, comment="变更后的值（JSON 格式）")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship('User')


class UserNotificationSettings(Base):
    """用户通知设置表 - 存储用户的钉钉Webhook和自定义规则。"""
    __tablename__ = 'user_notification_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    dingtalk_webhook = Column(String(500), comment="钉钉Webhook URL")
    dingtalk_secret = Column(String(100), comment="钉钉签名密钥")
    # 大模型配置
    llm_provider = Column(String(20), comment="大模型提供商: minmax/openai/anthropic"
    llm_api_key = Column(String(200), comment="大模型API Key"
    llm_model = Column(String(50), comment="大模型名称"
    llm_group_id = Column(String(100), comment="Minimax Group ID"
    rules = Column(Text, comment="JSON格式的自定义规则")
    enabled = Column(Boolean, default=True, comment="是否启用智能提醒")
    daily_limit = Column(Integer, default=5, comment="每日提醒上限")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship('User', backref='notification_settings')


class NotificationLog(Base):
    """通知发送记录表 - 记录每次钉钉推送，用于已读回执。"""
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='SET NULL'), index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), index=True)
    message_id = Column(String(100), comment="钉钉返回的消息ID")
    message_content = Column(Text, comment="消息内容摘要")
    is_read = Column(Boolean, default=False, comment="是否已读")
    read_at = Column(DateTime, comment="阅读时间")
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), comment="发送时间")

    user = relationship('User')
    task = relationship('Task')
    project = relationship('Project')