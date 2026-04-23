"""
TaskTree 数据库引擎与会话管理
============================
采用 SQLAlchemy 2.0 异步引擎 (aiosqlite)。
引擎和会话工厂使用延迟初始化模式，首次调用时自动创建。
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Base 统一在 app.models.__init__ 中定义，避免重复创建

# 引擎和会话工厂使用模块级全局变量，延迟初始化
_engine = None
_async_session_maker = None


def get_engine():
    """获取数据库异步引擎（单例延迟初始化）。"""
    global _engine
    if _engine is None:
        from app.core.config import settings
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True
        )
    return _engine


def get_session_maker():
    """获取异步会话工厂（单例延迟初始化）。"""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_maker


async def get_db():
    """FastAPI 依赖注入：提供数据库会话。

    在 yield 后自动管理会话生命周期，异常时自动回滚。
    用法::

        @router.get("/example")
        async def handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_session_maker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """应用启动时初始化数据库：创建所有未存在的表结构。"""
    from app.models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)