from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Base 统一在 app.models.__init__ 中定义，避免重复创建

# 引擎和会话工厂将在 settings 加载后初始化
_engine = None
_async_session_maker = None


def get_engine():
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
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_maker


async def get_db():
    async with get_session_maker() as session:
        yield session


async def init_db():
    from app.models import Base
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)