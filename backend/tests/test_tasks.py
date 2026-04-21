"""
任务接口单元测试
================
覆盖：任务 CRUD、状态流转、拖拽移动、批量创建、依赖关系、标签、评论。
"""
import pytest
from httpx import AsyncClient


# ==================== 辅助函数 ====================

async def create_project(client: AsyncClient, headers: dict, name: str = "测试项目") -> int:
    """创建项目并返回项目 ID"""
    resp = await client.post("/api/v1/tasktree/projects", headers=headers, json={"name": name})
    return resp.json()["data"]["id"]


async def create_task(client: AsyncClient, headers: dict, project_id: int, name: str = "测试任务", **kwargs) -> int:
    """创建任务并返回任务 ID"""
    data = {"name": name, **kwargs}
    resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=headers, json=data)
    return resp.json()["data"]["id"]


# ==================== 任务 CRUD ====================

class TestTaskCRUD:
    """任务增删改查测试用例"""

    @pytest.mark.asyncio
    async def test_create_task(self, client: AsyncClient, auth_headers):
        """正常创建任务"""
        project_id = await create_project(client, auth_headers)
        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=auth_headers, json={
            "name": "新任务",
            "description": "任务描述",
            "priority": "high"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["name"] == "新任务"
        assert data["data"]["status"] == "pending"
        assert data["data"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_create_child_task(self, client: AsyncClient, auth_headers):
        """创建子任务"""
        project_id = await create_project(client, auth_headers)
        parent_id = await create_task(client, auth_headers, project_id, "父任务")

        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=auth_headers, json={
            "name": "子任务",
            "parent_id": parent_id
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["parent_id"] == parent_id

    @pytest.mark.asyncio
    async def test_create_task_invalid_parent(self, client: AsyncClient, auth_headers):
        """父任务不存在应返回 400"""
        project_id = await create_project(client, auth_headers)
        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=auth_headers, json={
            "name": "孤儿任务",
            "parent_id": 99999
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_task_tree(self, client: AsyncClient, auth_headers):
        """获取任务树"""
        project_id = await create_project(client, auth_headers)
        parent_id = await create_task(client, auth_headers, project_id, "根任务")
        await create_task(client, auth_headers, project_id, "子任务A", parent_id=parent_id)
        await create_task(client, auth_headers, project_id, "子任务B", parent_id=parent_id)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/tasks/tree", headers=auth_headers)
        assert resp.status_code == 200
        tree = resp.json()["data"]
        assert len(tree) == 1  # 1个根任务
        assert len(tree[0]["children"]) == 2  # 2个子任务

    @pytest.mark.asyncio
    async def test_get_task_detail(self, client: AsyncClient, auth_headers):
        """获取任务详情"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id, "详情任务")

        resp = await client.get(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "详情任务"
        assert "children" in data
        assert "tags" in data
        assert "dependencies" in data

    @pytest.mark.asyncio
    async def test_list_tasks(self, client: AsyncClient, auth_headers):
        """获取任务列表（分页）"""
        project_id = await create_project(client, auth_headers)
        for i in range(5):
            await create_task(client, auth_headers, project_id, f"任务{i}")

        resp = await client.get(
            f"/api/v1/tasktree/projects/{project_id}/tasks",
            headers=auth_headers,
            params={"page": 1, "page_size": 3}
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["items"]) == 3

    @pytest.mark.asyncio
    async def test_update_task(self, client: AsyncClient, auth_headers):
        """更新任务"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id, "原名称")

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={
            "name": "新名称",
            "priority": "low",
            "progress": 50
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_task(self, client: AsyncClient, auth_headers):
        """删除任务"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id, "待删除任务")

        resp = await client.delete(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_task_with_children_blocked(self, client: AsyncClient, auth_headers):
        """有子任务时不传 delete_children 应阻止删除"""
        project_id = await create_project(client, auth_headers)
        parent_id = await create_task(client, auth_headers, project_id, "父任务")
        await create_task(client, auth_headers, project_id, "子任务", parent_id=parent_id)

        resp = await client.delete(f"/api/v1/tasktree/tasks/{parent_id}", headers=auth_headers)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_task_with_children_allowed(self, client: AsyncClient, auth_headers):
        """传 delete_children=true 应允许级联删除"""
        project_id = await create_project(client, auth_headers)
        parent_id = await create_task(client, auth_headers, project_id, "父任务")
        await create_task(client, auth_headers, project_id, "子任务", parent_id=parent_id)

        resp = await client.delete(
            f"/api/v1/tasktree/tasks/{parent_id}",
            headers=auth_headers,
            params={"delete_children": True}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, client: AsyncClient, auth_headers):
        """获取不存在的任务应返回 404"""
        resp = await client.get("/api/v1/tasktree/tasks/99999", headers=auth_headers)
        assert resp.status_code == 404


# ==================== 状态流转 ====================

class TestStatusTransition:
    """任务状态流转测试用例"""

    @pytest.mark.asyncio
    async def test_valid_transition_pending_to_in_progress(self, client: AsyncClient, auth_headers):
        """合法状态转换: pending → in_progress"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={
            "status": "in_progress"
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_valid_transition_in_progress_to_completed(self, client: AsyncClient, auth_headers):
        """合法状态转换: in_progress → completed"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        # pending → in_progress
        await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={"status": "in_progress"})
        # in_progress → completed
        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={"status": "completed"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_transition_pending_to_completed(self, client: AsyncClient, auth_headers):
        """非法状态转换: pending → completed 应返回 400"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={
            "status": "completed"
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_transition_completed_to_in_progress(self, client: AsyncClient, auth_headers):
        """非法状态转换: completed → in_progress 应返回 400"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={"status": "in_progress"})
        await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={"status": "completed"})

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={
            "status": "in_progress"
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_same_status_no_error(self, client: AsyncClient, auth_headers):
        """相同状态提交不应报错"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}", headers=auth_headers, json={
            "status": "pending"
        })
        assert resp.status_code == 200


# ==================== 拖拽移动 ====================

class TestTaskMove:
    """任务移动测试用例"""

    @pytest.mark.asyncio
    async def test_move_task_sort_order(self, client: AsyncClient, auth_headers):
        """移动任务排序"""
        project_id = await create_project(client, auth_headers)
        task1 = await create_task(client, auth_headers, project_id, "任务A")
        task2 = await create_task(client, auth_headers, project_id, "任务B")

        resp = await client.put(f"/api/v1/tasktree/tasks/{task2}/move", headers=auth_headers, json={
            "sort_order": 0
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_move_to_self_blocked(self, client: AsyncClient, auth_headers):
        """不能将任务移动到自身"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id, "自引用任务")

        resp = await client.put(f"/api/v1/tasktree/tasks/{task_id}/move", headers=auth_headers, json={
            "parent_id": task_id
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_move_circular_blocked(self, client: AsyncClient, auth_headers):
        """不能创建循环引用"""
        project_id = await create_project(client, auth_headers)
        parent = await create_task(client, auth_headers, project_id, "父任务")
        child = await create_task(client, auth_headers, project_id, "子任务", parent_id=parent)

        resp = await client.put(f"/api/v1/tasktree/tasks/{parent}/move", headers=auth_headers, json={
            "parent_id": child
        })
        assert resp.status_code == 400


# ==================== 批量创建 ====================

class TestBatchCreate:
    """批量创建任务测试用例"""

    @pytest.mark.asyncio
    async def test_batch_create(self, client: AsyncClient, auth_headers):
        """批量创建多个任务"""
        project_id = await create_project(client, auth_headers)
        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks/batch", headers=auth_headers, json={
            "tasks": [
                {"name": "批量任务1"},
                {"name": "批量任务2"},
                {"name": "批量任务3"},
            ]
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["count"] == 3


# ==================== 依赖关系 ====================

class TestDependency:
    """任务依赖关系测试用例"""

    @pytest.mark.asyncio
    async def test_create_dependency(self, client: AsyncClient, auth_headers):
        """创建依赖关系"""
        project_id = await create_project(client, auth_headers)
        task_a = await create_task(client, auth_headers, project_id, "前置任务")
        task_b = await create_task(client, auth_headers, project_id, "后续任务")

        resp = await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 201

    @pytest.mark.asyncio
    async def test_create_duplicate_dependency(self, client: AsyncClient, auth_headers):
        """重复创建依赖应返回 400"""
        project_id = await create_project(client, auth_headers)
        task_a = await create_task(client, auth_headers, project_id, "前置")
        task_b = await create_task(client, auth_headers, project_id, "后续")

        await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })
        resp = await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_dependency(self, client: AsyncClient, auth_headers):
        """删除依赖关系"""
        project_id = await create_project(client, auth_headers)
        task_a = await create_task(client, auth_headers, project_id, "前置")
        task_b = await create_task(client, auth_headers, project_id, "后续")

        await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })
        resp = await client.delete(f"/api/v1/tasktree/tasks/{task_a}/dependencies/{task_b}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_check_dependency_blocked(self, client: AsyncClient, auth_headers):
        """前置任务未完成时 can_start 应为 False"""
        project_id = await create_project(client, auth_headers)
        task_a = await create_task(client, auth_headers, project_id, "前置")
        task_b = await create_task(client, auth_headers, project_id, "后续")

        await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })

        resp = await client.get(f"/api/v1/tasktree/tasks/{task_b}/dependencies/check", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["can_start"] is False
        assert len(data["blocked_by"]) == 1

    @pytest.mark.asyncio
    async def test_check_dependency_unblocked(self, client: AsyncClient, auth_headers):
        """前置任务完成后 can_start 应为 True"""
        project_id = await create_project(client, auth_headers)
        task_a = await create_task(client, auth_headers, project_id, "前置")
        task_b = await create_task(client, auth_headers, project_id, "后续")

        await client.post(f"/api/v1/tasktree/tasks/{task_a}/dependencies", headers=auth_headers, json={
            "dependent_task_id": task_b
        })

        # 把前置任务标记为已完成
        await client.put(f"/api/v1/tasktree/tasks/{task_a}", headers=auth_headers, json={"status": "in_progress"})
        await client.put(f"/api/v1/tasktree/tasks/{task_a}", headers=auth_headers, json={"status": "completed"})

        resp = await client.get(f"/api/v1/tasktree/tasks/{task_b}/dependencies/check", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["can_start"] is True


# ==================== 标签 ====================

class TestTags:
    """标签管理测试用例"""

    @pytest.mark.asyncio
    async def test_create_tag(self, client: AsyncClient, auth_headers):
        """创建标签"""
        project_id = await create_project(client, auth_headers)
        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers, json={
            "name": "紧急",
            "color": "#f5222d"
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 201

    @pytest.mark.asyncio
    async def test_list_tags(self, client: AsyncClient, auth_headers):
        """获取标签列表"""
        project_id = await create_project(client, auth_headers)
        await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers, json={
            "name": "标签A", "color": "#1890ff"
        })
        await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers, json={
            "name": "标签B", "color": "#52c41a"
        })

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    @pytest.mark.asyncio
    async def test_add_tags_to_task(self, client: AsyncClient, auth_headers):
        """为任务设置标签"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        # 创建标签
        tag_resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers, json={
            "name": "重要", "color": "#f5222d"
        })
        tag_id = tag_resp.json()["data"]["id"]

        resp = await client.post(f"/api/v1/tasktree/tasks/{task_id}/tags", headers=auth_headers, json={
            "tag_ids": [tag_id]
        })
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_tag(self, client: AsyncClient, auth_headers):
        """删除标签"""
        project_id = await create_project(client, auth_headers)
        tag_resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=auth_headers, json={
            "name": "临时", "color": "#999"
        })
        tag_id = tag_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/tasktree/tags/{tag_id}", headers=auth_headers)
        assert resp.status_code == 200


# ==================== 评论 ====================

class TestComments:
    """评论测试用例"""

    @pytest.mark.asyncio
    async def test_create_comment(self, client: AsyncClient, auth_headers):
        """创建评论"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        resp = await client.post(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers, json={
            "content": "这是一条测试评论"
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 201

    @pytest.mark.asyncio
    async def test_list_comments(self, client: AsyncClient, auth_headers):
        """获取评论列表"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        await client.post(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers, json={
            "content": "评论1"
        })
        await client.post(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers, json={
            "content": "评论2"
        })

        resp = await client.get(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    @pytest.mark.asyncio
    async def test_delete_comment(self, client: AsyncClient, auth_headers):
        """删除评论"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        create_resp = await client.post(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers, json={
            "content": "待删除评论"
        })
        comment_id = create_resp.json()["data"]["id"]

        resp = await client.delete(f"/api/v1/tasktree/comments/{comment_id}", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_create_comment_with_mentions(self, client: AsyncClient, auth_headers, test_user2):
        """创建带 @提及 的评论"""
        project_id = await create_project(client, auth_headers)
        task_id = await create_task(client, auth_headers, project_id)

        resp = await client.post(f"/api/v1/tasktree/tasks/{task_id}/comments", headers=auth_headers, json={
            "content": "请 @test2 看一下",
            "mentions": [test_user2.id]
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 201
