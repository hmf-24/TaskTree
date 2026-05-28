from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.models import Base

class AgentRoutine(Base):
    """
    智能自动化常规任务 (Agentic Automated Routines) 模型。
    驱动系统的定时调度器将自然语言指令投递给 Agent 执行。
    """
    __tablename__ = "agent_routines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, index=True, nullable=False, comment="关联的用户 ID")
    app_source = Column(String(50), nullable=False, comment="所属上下文 (readhub 或 tasktree)")
    name = Column(String(100), nullable=False, comment="任务名称，如 'ReadHub 早间简报'")
    schedule_cron = Column(String(50), nullable=False, comment="Cron 表达式，如 '0 9 * * *'")
    prompt_template = Column(Text, nullable=False, comment="发送给 Agent 的自然语言指令")
    is_active = Column(Boolean, default=True, comment="任务是否激活")
    last_run_at = Column(DateTime(timezone=True), nullable=True, comment="上次成功执行时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
