"""
项目接口单元测试
================
覆盖：项目 CRUD、归档、成员管理、权限校验。
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectMember


# ==================== 项目 CRUD ====================

class TestProjectCRUD:
    """项目增删改查测试用例"""

    @pytest.mark.asyncio
    async def test_create_project(self, client: AsyncClient, auth_headers):
        """正常创建项目"""
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "测试项目",
            "description": "项目描述"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["name"] == "测试项目"
        assert data["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_project_with_dates(self, client: AsyncClient, auth_headers):
        """创建带日期的项目"""
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "带日期项目",
            "start_date": "2026-04-01",
            "end_date": "2026-06-01"
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["start_date"] == "2026-04-01"
        assert data["end_date"] == "2026-06-01"

    @pytest.mark.asyncio
    async def test_create_project_missing_name(self, client: AsyncClient, auth_headers):
        """缺少项目名称应返回 422"""
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "description": "只有描述"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_projects(self, client: AsyncClient, auth_headers):
        """获取项目列表"""
        # 先创建一个项目
        await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "列表测试项目"
        })
        resp = await client.get("/api/v1/tasktree/projects", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_project_detail(self, client: AsyncClient, auth_headers):
        """获取项目详情"""
        # 创建项目
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "详情测试项目"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "详情测试项目"
        assert "task_count" in data
        assert "completed_count" in data

    @pytest.mark.asyncio
    async def test_update_project(self, client: AsyncClient, auth_headers):
        """更新项目"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "原始名称"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.put(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers, json={
            "name": "修改后名称"
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "更新成功"

    @pytest.mark.asyncio
    async def test_delete_project(self, client: AsyncClient, auth_headers):
        """删除项目"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "待删除项目"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers)
        assert resp.status_code == 200

        # 再次获取应返回 404
        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_project(self, client: AsyncClient, auth_headers):
        """获取不存在的项目应返回 404"""
        resp = await client.get("/api/v1/tasktree/projects/99999", headers=auth_headers)
        assert resp.status_code == 404


# ==================== 归档 ====================

class TestProjectArchive:
    """项目归档测试用例"""

    @pytest.mark.asyncio
    async def test_archive_project(self, client: AsyncClient, auth_headers):
        """归档项目"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "待归档项目"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.post(
            f"/api/v1/tasktree/projects/{project_id}/archive",
            headers=auth_headers,
            json={"archived": True}
        )
        assert resp.status_code == 200
        assert "归档成功" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_unarchive_project(self, client: AsyncClient, auth_headers):
        """取消归档"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "归档后取消项目"
        })
        project_id = create_resp.json()["data"]["id"]

        # 先归档
        await client.post(
            f"/api/v1/tasktree/projects/{project_id}/archive",
            headers=auth_headers,
            json={"archived": True}
        )
        # 再取消
        resp = await client.post(
            f"/api/v1/tasktree/projects/{project_id}/archive",
            headers=auth_headers,
            json={"archived": False}
        )
        assert resp.status_code == 200
        assert "取消归档" in resp.json()["message"]


# ==================== 权限 ====================

class TestProjectAccess:
    """项目权限测试用例"""

    @pytest.mark.asyncio
    async def test_access_denied_for_nonmember(self, client: AsyncClient, auth_headers, auth_headers2):
        """非成员访问项目应返回 403"""
        # 用户1创建项目
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "私有项目"
        })
        project_id = create_resp.json()["data"]["id"]

        # 用户2尝试访问
        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers2)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_nonowner_cannot_delete(self, client: AsyncClient, auth_headers, auth_headers2, db_session):
        """非所有者不能删除项目"""
        # 用户1创建项目
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "禁止删除项目"
        })
        project_id = create_resp.json()["data"]["id"]

        # 手动添加用户2为成员
        member = ProjectMember(project_id=project_id, user_id=2, role="member")
        db_session.add(member)
        await db_session.commit()

        # 用户2尝试删除
        resp = await client.delete(f"/api/v1/tasktree/projects/{project_id}", headers=auth_headers2)
        assert resp.status_code == 403


# ==================== 成员管理 ====================

class TestProjectMembers:
    """项目成员管理测试用例"""

    @pytest.mark.asyncio
    async def test_add_member(self, client: AsyncClient, auth_headers, test_user2):
        """添加成员"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "成员测试项目"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "test2@example.com", "role": "member"}
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 201

    @pytest.mark.asyncio
    async def test_add_nonexistent_member(self, client: AsyncClient, auth_headers):
        """添加不存在的用户应返回 404"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "成员测试项目2"
        })
        project_id = create_resp.json()["data"]["id"]

        resp = await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "ghost@example.com", "role": "viewer"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_members(self, client: AsyncClient, auth_headers, test_user2):
        """获取成员列表"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "成员列表项目"
        })
        project_id = create_resp.json()["data"]["id"]

        # 添加成员
        await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "test2@example.com", "role": "member"}
        )

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/members", headers=auth_headers)
        assert resp.status_code == 200
        members = resp.json()["data"]
        assert len(members) >= 1

    @pytest.mark.asyncio
    async def test_remove_member(self, client: AsyncClient, auth_headers, test_user2):
        """移除成员"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "移除成员项目"
        })
        project_id = create_resp.json()["data"]["id"]

        await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "test2@example.com", "role": "member"}
        )

        resp = await client.delete(
            f"/api/v1/tasktree/projects/{project_id}/members/{test_user2.id}",
            headers=auth_headers
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_add_duplicate_member(self, client: AsyncClient, auth_headers, test_user2):
        """重复添加成员应返回 400"""
        create_resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "重复成员项目"
        })
        project_id = create_resp.json()["data"]["id"]

        await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "test2@example.com", "role": "member"}
        )

        resp = await client.post(
            f"/api/v1/tasktree/projects/{project_id}/members",
            headers=auth_headers,
            json={"email": "test2@example.com", "role": "member"}
        )
        assert resp.status_code == 400
