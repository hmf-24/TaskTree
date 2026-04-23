"""
TaskTree 测试配置
=================
提供异步测试客户端、内存数据库和测试夹具。
所有测试用例共享此配置，每个测试函数使用独立的数据库事务并自动回滚。
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models import Base, User
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.main import app


# ---- 测试用内存数据库 ----
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """为整个测试会话创建一个事件循环。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """每个测试前重建数据库表，测试后清理。"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    """覆盖 FastAPI 的数据库依赖，使用测试数据库。"""
    async with TestSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# 覆盖应用的数据库依赖
app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    """提供异步 HTTP 测试客户端。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """提供数据库会话用于手动操作测试数据。"""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """创建一个测试用户并返回。"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        nickname="测试用户"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(db_session: AsyncSession):
    """创建第二个测试用户（用于权限测试）。"""
    user = User(
        email="test2@example.com",
        password_hash=get_password_hash("password123"),
        nickname="测试用户2"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User):
    """返回带有 JWT Token 的认证请求头。"""
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers2(test_user2: User):
    """返回第二个用户的认证请求头。"""
    token = create_access_token({"sub": str(test_user2.id), "email": test_user2.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_token(test_user: User):
    """返回测试用户的 JWT Token。"""
    token = create_access_token({"sub": str(test_user.id), "email": test_user.email})
    return token
