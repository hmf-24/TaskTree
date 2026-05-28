"""
TaskTree 调度器服务
==================
基于 APScheduler，管理全局后台定时自动化任务 (Routines)。
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_session_maker
from app.models.routine import AgentRoutine

logger = logging.getLogger(__name__)

class SchedulerService:
    """Agentic 自动化常规任务调度服务"""

    _scheduler = None

    @classmethod
    def start(cls):
        """启动全局调度器"""
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
            cls._scheduler.start()
            logger.info("✅ APScheduler 调度器已启动 (Agent Routines)")

    @classmethod
    def stop(cls):
        """停止调度器"""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
            logger.info("🛑 APScheduler 调度器已停止")

    @classmethod
    async def reload_user_routine(cls, routine_id: int):
        """重载/添加指定的 Routine 任务"""
        job_id = f"routine_{routine_id}"

        if cls._scheduler.get_job(job_id):
            cls._scheduler.remove_job(job_id)
            logger.info(f"[Scheduler] 移除旧的 Routine 任务 {job_id}")

        async with get_session_maker()() as db:
            result = await db.execute(
                select(AgentRoutine).where(AgentRoutine.id == routine_id)
            )
            routine = result.scalar_one_or_none()

        if routine and routine.is_active:
            try:
                # 解析 Cron 表达式
                trigger = CronTrigger.from_crontab(routine.schedule_cron)
                
                cls._scheduler.add_job(
                    cls._execute_routine,
                    trigger=trigger,
                    args=[routine.id, routine.user_id, routine.app_source, routine.prompt_template],
                    id=job_id,
                    name=routine.name,
                    replace_existing=True,
                )
                logger.info(f"✅ [Scheduler] 成功加载 Routine '{routine.name}' ({job_id}), Cron: {routine.schedule_cron}")
            except Exception as e:
                logger.error(f"❌ [Scheduler] 加载 Routine {routine_id} 失败: Cron 表达式错误? {e}")

    @classmethod
    async def reload_all_jobs(cls):
        """服务启动时，加载所有激活的 Routines"""
        if not cls._scheduler:
            cls.start()
            
        # 这里同时也为了兼容之前的 RSS 自动拉取（如果需要），但现在我们统一用 Routine
        
        async with get_session_maker()() as db:
            result = await db.execute(
                select(AgentRoutine).where(AgentRoutine.is_active == True)
            )
            routines = result.scalars().all()

        count = 0
        for r in routines:
            await cls.reload_user_routine(r.id)
            count += 1
            
        logger.info(f"✅ [Scheduler] 初始化完成，共加载 {count} 个 Agent Routines")

    @staticmethod
    async def _execute_routine(routine_id: int, user_id: int, app_source: str, prompt_template: str):
        """实际执行 Routine，投递给 Agent"""
        logger.info(f"🕒 [Scheduler] 开始后台执行 Routine #{routine_id}...")
        try:
            from app.api.v1.dingtalk import process_dingtalk_message
            from app.models import UserNotificationSettings
            from app.models.rss import ReadHubSettings
            
            # 由于是系统调度，dingtalk_user_id 必须从数据库查出，否则无法发送结果
            async with get_session_maker()() as db:
                dingtalk_user_id = None
                if app_source == "readhub":
                    res = await db.execute(select(ReadHubSettings).where(ReadHubSettings.user_id == user_id))
                    settings = res.scalar_one_or_none()
                    # 如果 readhub 设置没有 dingtalk_user_id，从全局通知设置里找
                    # 这里假设 user_notification_settings 有 dingtalk_user_id
                
                # 统一从 UserNotificationSettings 获取 dingtalk_user_id
                notif_res = await db.execute(select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id))
                notif_settings = notif_res.scalar_one_or_none()
                if notif_settings and notif_settings.dingtalk_user_id:
                    dingtalk_user_id = notif_settings.dingtalk_user_id
                    
                if not dingtalk_user_id:
                    logger.warning(f"⚠️ [Scheduler] Routine #{routine_id} 无法执行，未找到用户 {user_id} 的 dingtalk_user_id")
                    return
                
                # 更新 last_run_at
                await db.execute(
                    update(AgentRoutine).where(AgentRoutine.id == routine_id).values(last_run_at=datetime.now(timezone.utc))
                )
                await db.commit()

            # 将 Routine 丢给 async_task_queue 或者直接调用
            # 为保证事务独立，我们在当前方法调用 process_dingtalk_message
            from app.services.async_task_queue import run_in_background
            
            async with get_session_maker()() as db2:
                # 给大模型强烈的上下文提示：这是自动化执行
                automated_prompt = f"【系统自动化任务触发】\n当前时间已到设定计划。\n您的任务目标是：\n{prompt_template}"
                
                await process_dingtalk_message(
                    user_id=user_id,
                    dingtalk_user_id=dingtalk_user_id,
                    message_content=automated_prompt,
                    db=db2,
                    app_source=app_source
                )
            
            logger.info(f"✅ [Scheduler] Routine #{routine_id} 执行指令已投递")
        except Exception as e:
            logger.error(f"❌ [Scheduler] Routine #{routine_id} 执行失败: {e}")
            import traceback
            traceback.print_exc()

# 单例
scheduler_service = SchedulerService()
