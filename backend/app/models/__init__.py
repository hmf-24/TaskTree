from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100))
    avatar = Column(String(500))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    owned_projects = relationship('Project', back_populates='owner')
    assigned_tasks = relationship('Task', back_populates='assignee')
    comments = relationship('TaskComment', back_populates='user')
    notifications = relationship('Notification', back_populates='user')


class Project(Base):
    """项目表"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default='active', index=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    owner = relationship('User', back_populates='owned_projects')
    members = relationship('ProjectMember', back_populates='project', cascade='all, delete-orphan')
    tasks = relationship('Task', back_populates='project', cascade='all, delete-orphan')
    tags = relationship('TaskTag', back_populates='project', cascade='all, delete-orphan')


class ProjectMember(Base):
    """项目成员表"""
    __tablename__ = 'project_members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(20), default='viewer')
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('project_id', 'user_id'),)

    project = relationship('Project', back_populates='members')
    user = relationship('User')


class Task(Base):
    """任务表"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    assignee_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), index=True)
    status = Column(String(20), default='pending', index=True)
    priority = Column(String(10), default='medium')
    progress = Column(Integer, default=0)
    estimated_time = Column(Integer)
    actual_time = Column(Integer)
    start_date = Column(Date)
    due_date = Column(Date)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    project = relationship('Project', back_populates='tasks')
    parent = relationship('Task', remote_side=[id], backref='children')
    assignee = relationship('User', back_populates='assigned_tasks')
    dependencies_from = relationship('TaskDependency', foreign_keys='TaskDependency.task_id', back_populates='task')
    dependencies_to = relationship('TaskDependency', foreign_keys='TaskDependency.dependent_task_id', back_populates='dependent_task')
    comments = relationship('TaskComment', back_populates='task', cascade='all, delete-orphan')
    attachments = relationship('TaskAttachment', back_populates='task', cascade='all, delete-orphan')
    tag_relations = relationship('TaskTagRelation', back_populates='task', cascade='all, delete-orphan')


class TaskDependency(Base):
    """任务依赖关系表"""
    __tablename__ = 'task_dependencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    dependent_task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('task_id', 'dependent_task_id'),)

    task = relationship('Task', foreign_keys=[task_id], back_populates='dependencies_from')
    dependent_task = relationship('Task', foreign_keys=[dependent_task_id], back_populates='dependencies_to')


class TaskTag(Base):
    """任务标签表"""
    __tablename__ = 'task_tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    color = Column(String(20))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint('project_id', 'name'),)

    project = relationship('Project', back_populates='tags')
    relations = relationship('TaskTagRelation', back_populates='tag')


class TaskTagRelation(Base):
    """任务标签关联表"""
    __tablename__ = 'task_tag_relations'

    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('task_tags.id', ondelete='CASCADE'), primary_key=True)

    task = relationship('Task', back_populates='tag_relations')
    tag = relationship('TaskTag', back_populates='relations')


class TaskComment(Base):
    """任务评论表"""
    __tablename__ = 'task_comments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship('Task', back_populates='comments')
    user = relationship('User', back_populates='comments')


class TaskAttachment(Base):
    """任务附件表"""
    __tablename__ = 'task_attachments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task = relationship('Task', back_populates='attachments')


class Notification(Base):
    """通知表"""
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(255))
    content = Column(Text)
    related_id = Column(Integer)
    related_type = Column(String(50))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship('User', back_populates='notifications')


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = 'operation_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete='SET NULL'), index=True)
    task_id = Column(Integer, ForeignKey('tasks.id', ondelete='SET NULL'), index=True)
    action = Column(String(50), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship('User')