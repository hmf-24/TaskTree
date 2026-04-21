"""
通知接口单元测试
================
覆盖：通知列表、标记已读、全部已读。
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


# ==================== 辅助函数 ====================

async def create_test_notifications(db_session: AsyncSession, user_id: int, count: int = 5):
    """批量创建测试通知"""
    for i in range(count):
        n = Notification(
            user_id=user_id,
            type="task_status",
            title=f"测试通知 {i + 1}",
            content=f"通知内容 {i + 1}",
            related_id=i + 1,
            related_type="task",
            is_read=(i >= 3),  # 前3条未读，后2条已读
        )
        db_session.add(n)
    await db_session.commit()


# ==================== 通知列表 ====================

class TestNotificationList:
    """通知列表测试用例"""

    @pytest.mark.asyncio
    async def test_list_notifications(self, client: AsyncClient, auth_headers, test_user, db_session):
        """获取通知列表"""
        await create_test_notifications(db_session, test_user.id)

        resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_list_unread_notifications(self, client: AsyncClient, auth_headers, test_user, db_session):
        """筛选未读通知"""
        await create_test_notifications(db_session, test_user.id)

        resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers, params={"is_read": False})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 3  # 前3条未读

    @pytest.mark.asyncio
    async def test_list_read_notifications(self, client: AsyncClient, auth_headers, test_user, db_session):
        """筛选已读通知"""
        await create_test_notifications(db_session, test_user.id)

        resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers, params={"is_read": True})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2  # 后2条已读

    @pytest.mark.asyncio
    async def test_list_notifications_pagination(self, client: AsyncClient, auth_headers, test_user, db_session):
        """通知分页"""
        await create_test_notifications(db_session, test_user.id, count=10)

        resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers, params={
            "page": 1, "page_size": 3
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 10
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_empty_notifications(self, client: AsyncClient, auth_headers):
        """无通知时返回空列表"""
        resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 0
        assert len(data["items"]) == 0


# ==================== 标记已读 ====================

class TestMarkRead:
    """标记通知已读测试用例"""

    @pytest.mark.asyncio
    async def test_mark_single_read(self, client: AsyncClient, auth_headers, test_user, db_session):
        """标记单条通知已读"""
        await create_test_notifications(db_session, test_user.id)

        # 获取通知列表中的第一条未读通知
        list_resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers, params={"is_read": False})
        first_unread = list_resp.json()["data"]["items"][0]

        resp = await client.put(
            f"/api/v1/tasktree/notifications/{first_unread['id']}/read",
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "标记已读"

    @pytest.mark.asyncio
    async def test_mark_nonexistent_notification(self, client: AsyncClient, auth_headers):
        """标记不存在的通知应返回 404"""
        resp = await client.put("/api/v1/tasktree/notifications/99999/read", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_other_users_notification(self, client: AsyncClient, auth_headers2, test_user, db_session):
        """不能标记别人的通知"""
        await create_test_notifications(db_session, test_user.id)

        # 用户2尝试标记用户1的通知
        list_resp = await client.get("/api/v1/tasktree/notifications", headers=auth_headers2)
        # 用户2没有通知，所以直接尝试标记用户1的通知ID
        n = Notification(
            user_id=test_user.id, type="test", title="用户1的通知", is_read=False
        )
        db_session.add(n)
        await db_session.commit()
        await db_session.refresh(n)

        resp = await client.put(f"/api/v1/tasktree/notifications/{n.id}/read", headers=auth_headers2)
        assert resp.status_code == 404  # 查询时 where user_id = current_user.id，所以找不到


# ==================== 全部已读 ====================

class TestMarkAllRead:
    """全部标记已读测试用例"""

    @pytest.mark.asyncio
    async def test_mark_all_read(self, client: AsyncClient, auth_headers, test_user, db_session):
        """全部标记已读"""
        await create_test_notifications(db_session, test_user.id)

        resp = await client.put("/api/v1/tasktree/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        assert "3" in resp.json()["message"]  # 3条未读被标记

        # 验证全部已读
        check = await client.get("/api/v1/tasktree/notifications", headers=auth_headers, params={"is_read": False})
        assert check.json()["data"]["total"] == 0

    @pytest.mark.asyncio
    async def test_mark_all_read_when_none_unread(self, client: AsyncClient, auth_headers):
        """无未读通知时全部已读应正常返回"""
        resp = await client.put("/api/v1/tasktree/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        assert "0" in resp.json()["message"]
