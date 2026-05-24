"""
TaskTree 调度器服务
==================
基于 APScheduler，管理全局后台定时任务（如自动拉取 RSS）。
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_maker

logger = logging.getLogger(__name__)

class SchedulerService:
    """动态定时任务调度服务"""

    _scheduler = None

    @classmethod
    def start(cls):
        """启动全局调度器"""
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
            cls._scheduler.start()
            logger.info("✅ APScheduler 调度器已启动")

    @classmethod
    def stop(cls):
        """停止调度器"""
        if cls._scheduler and cls._scheduler.running:
            cls._scheduler.shutdown(wait=False)
            logger.info("🛑 APScheduler 调度器已停止")

    @classmethod
    async def reload_user_rss_job(cls, user_id: int):
        """重载某个用户的 RSS 拉取任务"""
        from app.models.rss import ReadHubSettings

        job_id = f"rss_fetch_user_{user_id}"

        # 1. 无论如何先尝试移除旧任务
        if cls._scheduler.get_job(job_id):
            cls._scheduler.remove_job(job_id)
            logger.info(f"[Scheduler] 移除用户 {user_id} 的旧 RSS 任务")

        # 2. 读取用户最新配置
        async with get_session_maker()() as db:
            result = await db.execute(
                select(ReadHubSettings).where(ReadHubSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()

        # 3. 如果开启，添加新任务
        if settings and settings.auto_fetch_enabled and settings.auto_fetch_interval:
            interval_minutes = settings.auto_fetch_interval
            # 最小限制 5 分钟，防止过载
            if interval_minutes < 5:
                interval_minutes = 5

            cls._scheduler.add_job(
                cls._execute_rss_fetch,
                trigger=IntervalTrigger(minutes=interval_minutes),
                args=[user_id],
                id=job_id,
                name=f"RSS Fetch for User {user_id}",
                replace_existing=True,
            )
            logger.info(f"✅ [Scheduler] 为用户 {user_id} 添加 RSS 拉取任务，间隔: {interval_minutes} 分钟")

    @classmethod
    async def reload_all_jobs(cls):
        """服务启动时，加载所有开启了自动拉取的用户任务"""
        from app.models.rss import ReadHubSettings

        if not cls._scheduler:
            cls.start()

        async with get_session_maker()() as db:
            result = await db.execute(
                select(ReadHubSettings).where(ReadHubSettings.auto_fetch_enabled == True)
            )
            all_settings = result.scalars().all()

        count = 0
        for settings in all_settings:
            await cls.reload_user_rss_job(settings.user_id)
            count += 1
            
        logger.info(f"✅ [Scheduler] 初始化完成，共加载 {count} 个 RSS 自动拉取任务")

    @staticmethod
    async def _execute_rss_fetch(user_id: int):
        """实际执行 RSS 拉取的任务（包装成独立的 DB 会话）"""
        from app.apps.readhub.service import RssService
        
        logger.info(f"🕒 [Scheduler] 开始执行用户 {user_id} 的后台 RSS 拉取...")
        try:
            async with get_session_maker()() as db:
                result = await RssService.fetch_feeds(db, user_id)
                # fetch_feeds 内部会调用 Dingtalk 推送，详见 service.py
                logger.info(f"✅ [Scheduler] 用户 {user_id} RSS 拉取完成: {result}")
        except Exception as e:
            logger.error(f"❌ [Scheduler] 用户 {user_id} RSS 拉取失败: {e}")

# 单例
scheduler_service = SchedulerService()
