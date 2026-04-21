"""
认证接口单元测试
================
覆盖：注册、登录、获取用户信息、修改信息、修改密码。
"""
import pytest
from httpx import AsyncClient


# ==================== 注册 ====================

class TestRegister:
    """用户注册测试用例"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """正常注册"""
        resp = await client.post("/api/v1/tasktree/auth/register", json={
            "email": "new@example.com",
            "password": "password123",
            "nickname": "新用户"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["email"] == "new@example.com"
        assert data["data"]["nickname"] == "新用户"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user):
        """邮箱重复注册应返回 400"""
        resp = await client.post("/api/v1/tasktree/auth/register", json={
            "email": "test@example.com",  # 已在 test_user fixture 中创建
            "password": "password123",
            "nickname": "重复用户"
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """无效邮箱格式应返回 422"""
        resp = await client.post("/api/v1/tasktree/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "nickname": "测试"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password(self, client: AsyncClient):
        """缺少密码字段应返回 422"""
        resp = await client.post("/api/v1/tasktree/auth/register", json={
            "email": "test3@example.com",
            "nickname": "测试"
        })
        assert resp.status_code == 422


# ==================== 登录 ====================

class TestLogin:
    """用户登录测试用例"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """正常登录"""
        resp = await client.post("/api/v1/tasktree/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "登录成功"
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """密码错误应返回 401"""
        resp = await client.post("/api/v1/tasktree/auth/login", json={
            "email": "test@example.com",
            "password": "wrong_password"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """用户不存在应返回 401"""
        resp = await client.post("/api/v1/tasktree/auth/login", json={
            "email": "ghost@example.com",
            "password": "password123"
        })
        assert resp.status_code == 401


# ==================== 当前用户 ====================

class TestCurrentUser:
    """当前用户信息测试用例"""

    @pytest.mark.asyncio
    async def test_get_me(self, client: AsyncClient, auth_headers, test_user):
        """获取当前用户信息"""
        resp = await client.get("/api/v1/tasktree/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "test@example.com"
        assert data["nickname"] == "测试用户"

    @pytest.mark.asyncio
    async def test_get_me_unauthorized(self, client: AsyncClient):
        """无 Token 应返回 403（HTTPBearer 缺少凭证）"""
        resp = await client.get("/api/v1/tasktree/auth/me")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self, client: AsyncClient):
        """无效 Token 应返回 401"""
        resp = await client.get(
            "/api/v1/tasktree/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_me(self, client: AsyncClient, auth_headers):
        """更新用户信息"""
        resp = await client.put("/api/v1/tasktree/auth/me", headers=auth_headers, json={
            "nickname": "新昵称"
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["nickname"] == "新昵称"


# ==================== 修改密码 ====================

class TestChangePassword:
    """修改密码测试用例"""

    @pytest.mark.asyncio
    async def test_change_password_success(self, client: AsyncClient, auth_headers):
        """正常修改密码"""
        resp = await client.put("/api/v1/tasktree/auth/password", headers=auth_headers, json={
            "old_password": "password123",
            "new_password": "newpassword456"
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "密码修改成功"

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, client: AsyncClient, auth_headers):
        """旧密码错误应返回 400"""
        resp = await client.put("/api/v1/tasktree/auth/password", headers=auth_headers, json={
            "old_password": "wrong_old_password",
            "new_password": "newpassword456"
        })
        assert resp.status_code == 400
