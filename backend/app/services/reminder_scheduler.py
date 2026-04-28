"""
TaskTree 智能提醒定时任务服务
=============================
定时检查用户任务并发送钉钉提醒。
"""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker
from app.models import User, Task, Project, UserNotificationSettings, NotificationLog, SchedulerState


class ReminderScheduler:
    """智能提醒调度器"""

    STATE_KEY = "last_run_at"

    def __init__(self):
        self._session_maker = None
        self.is_running = False

    @property
    def session_maker(self):
        """延迟获取会话工厂，避免模块导入时触发数据库引擎创建。"""
        if self._session_maker is None:
            self._session_maker = get_session_maker()
        return self._session_maker

    async def _save_state(self, db: AsyncSession):
        """保存调度状态"""
        result = await db.execute(
            select(SchedulerState).where(SchedulerState.key == self.STATE_KEY)
        )
        state = result.scalar_one_or_none()
        if state:
            state.value = datetime.now(timezone.utc).isoformat()
        else:
            state = SchedulerState(key=self.STATE_KEY, value=datetime.now(timezone.utc).isoformat())
            db.add(state)
        await db.commit()

    async def _load_state(self, db: AsyncSession) -> Optional[datetime]:
        """加载调度状态"""
        result = await db.execute(
            select(SchedulerState).where(SchedulerState.key == self.STATE_KEY)
        )
        state = result.scalar_one_or_none()
        if state and state.value:
            return datetime.fromisoformat(state.value)
        return None

    async def start(self, interval_minutes: int = 30):
        """启动定时任务

        Args:
            interval_minutes: 检查间隔（分钟）
        """
        self.is_running = True
        print(f"🚀 智能提醒服务已启动，每 {interval_minutes} 分钟检查一次")

        while self.is_running:
            try:
                async with self.session_maker() as db:
                    last_run = await self._load_state(db)
                    if last_run:
                        print(f"📌 从上次位置继续: {last_run.isoformat()}")
                await self.check_and_send_reminders()
                async with self.session_maker() as db:
                    await self._save_state(db)
            except Exception as e:
                print(f"❌ 提醒任务执行失败: {e}")

            await asyncio.sleep(interval_minutes * 60)

    async def stop(self):
        """停止定时任务"""
        self.is_running = False
        print("🛑 智能提醒服务已停止")

    async def check_and_send_reminders(self):
        """检查并发送提醒"""
        async with self.session_maker() as db:
            # 获取所有启用了智能提醒的用户
            result = await db.execute(
                select(UserNotificationSettings).where(
                    UserNotificationSettings.enabled == True,
                    UserNotificationSettings.dingtalk_webhook.isnot(None)
                )
            )
            settings_list = result.scalars().all()

            print(f"📋 正在检查 {len(settings_list)} 位用户的任务...")

            for settings in settings_list:
                try:
                    await self.check_user_notifications(settings, db)
                except Exception as e:
                    print(f"❌ 用户 {settings.user_id} 提醒失败: {e}")

    async def check_user_notifications(
        self,
        settings: UserNotificationSettings,
        db: AsyncSession,
        is_manual: bool = False
    ):
        """检查单个用户的任务并发送提醒

        Args:
            settings: 用户通知设置
            db: 数据库会话
            is_manual: 是否手动触发（手动触发不计入每日配额）
        """
        # 获取用户的今日发送记录
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # 自动提醒才检查配额，手动触发直接通过
        if not is_manual:
            result = await db.execute(
                select(NotificationLog).where(
                    and_(
                        NotificationLog.user_id == settings.user_id,
                        NotificationLog.is_manual == False,
                        NotificationLog.sent_at >= today_start
                    )
                )
            )
            today_count = len(result.scalars().all())

            if today_count >= settings.daily_limit:
                print(f"⏭️ 用户 {settings.user_id} 今日已达上限 ({today_count}/{settings.daily_limit})")
                return False

        # 消息去重：检查最近6小时内是否已发送过
        six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
        result = await db.execute(
            select(NotificationLog).where(
                and_(
                    NotificationLog.user_id == settings.user_id,
                    NotificationLog.sent_at >= six_hours_ago,
                    NotificationLog.is_manual == is_manual
                )
            )
        )
        recent_logs = result.scalars().all()
        recent_task_ids = {log.task_id for log in recent_logs if log.task_id}
        print(f"📋 最近6小时已发送任务: {recent_task_ids}")

        # 解析规则
        rules = json.loads(settings.rules) if settings.rules else []

        # 获取用户参与的项目
        result = await db.execute(
            select(Project).where(Project.owner_id == settings.user_id)
        )
        projects = result.scalars().all()

        # 获取所有任务（排除已完成和最近已提醒的）
        all_tasks = []
        for project in projects:
            result = await db.execute(
                select(Task).where(
                    and_(
                        Task.project_id == project.id,
                        Task.status != "completed"
                    )
                )
            )
            tasks = result.scalars().all()

            for task in tasks:
                # 跳过6小时内已发送过的任务
                if task.id in recent_task_ids:
                    continue
                all_tasks.append({
                    "id": task.id,
                    "project_id": task.project_id,
                    "project_name": project.name,
                    "name": task.name,
                    "status": task.status,
                    "priority": task.priority,
                    "progress": task.progress,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None
                })

        if not all_tasks:
            return True  # 无任务，不算失败

        # 解析分析配置
        config = {}
        if settings.analysis_config:
            try:
                config = json.loads(settings.analysis_config)
            except:
                pass

        # 使用用户配置的大模型
        from app.services.llm_service import LLMService
        from app.core.crypto import decrypt_api_key

        # 解密API Key
        api_key = decrypt_api_key(settings.llm_api_key_encrypted) if settings.llm_api_key_encrypted else None

        llm_service = LLMService(
            provider=settings.llm_provider or "minmax",
            api_key=api_key,
            model=settings.llm_model,
            group_id=settings.llm_group_id
        )

        project_name = projects[0].name if projects else "多项目"

        # 传递分析配置
        analysis = await llm_service.analyze_tasks(all_tasks, project_name, config)

        if not analysis.get("need_remind"):
            return None  # 不需要提醒

        # 检查是否已发送过类似消息（避免重复）
        task_ids = analysis.get("tasks_to_remind", [])
        if not task_ids:
            return None  # 没有需要提醒的任务

        # 发送钉钉通知
        from app.services.dingtalk_service import DingtalkService

        service = DingtalkService(
            webhook_url=settings.dingtalk_webhook,
            secret=settings.dingtalk_secret
        )

        message = analysis.get("message", "您有任务需要关注")
        plan = analysis.get("plan", "")

        # 构建提醒内容，包含规划建议
        content = f"## 🔔 任务提醒\n\n{message}\n"
        if plan:
            content += f"\n📋 **规划建议**\n{plan}\n"
        content += "\n---\n*来自 TaskTree 智能助手*"

        result = await service.send_message(
            content=content,
            title="TaskTree 智能提醒",
            msg_type="markdown"
        )

        if result.get("success"):
            # 记录发送日志
            for task_id in task_ids:
                log = NotificationLog(
                    user_id=settings.user_id,
                    task_id=task_id,
                    message_id=result.get("message_id"),
                    message_content=message[:200],
                    is_manual=is_manual
                )
                db.add(log)

            await db.commit()
            print(f"✅ 用户 {settings.user_id} 提醒发送成功")
            return True  # 发送成功


# 全局调度器实例
reminder_scheduler = ReminderScheduler()


async def start_scheduler(interval_minutes: int = 30):
    """启动调度器（供 main.py 调用）"""
    await reminder_scheduler.start(interval_minutes)