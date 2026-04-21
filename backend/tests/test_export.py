"""
导入导出接口单元测试
====================
覆盖：JSON/Markdown/Excel 导出、JSON 导入。
"""
import json
import pytest
from httpx import AsyncClient


# ==================== 辅助函数 ====================

async def create_project_with_tasks(client: AsyncClient, headers: dict) -> int:
    """创建包含任务的项目，返回项目 ID"""
    resp = await client.post("/api/v1/tasktree/projects", headers=headers, json={
        "name": "导出测试项目",
        "description": "这是一个用于测试导出功能的项目"
    })
    project_id = resp.json()["data"]["id"]

    # 创建根任务
    task1 = await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=headers, json={
        "name": "根任务1", "priority": "high"
    })
    task1_id = task1.json()["data"]["id"]

    # 创建子任务
    await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=headers, json={
        "name": "子任务1A", "parent_id": task1_id
    })
    await client.post(f"/api/v1/tasktree/projects/{project_id}/tasks", headers=headers, json={
        "name": "根任务2", "priority": "low"
    })

    # 创建标签
    await client.post(f"/api/v1/tasktree/projects/{project_id}/tags", headers=headers, json={
        "name": "紧急", "color": "#f5222d"
    })

    return project_id


# ==================== JSON 导出 ====================

class TestExportJSON:
    """JSON 导出测试用例"""

    @pytest.mark.asyncio
    async def test_export_json(self, client: AsyncClient, auth_headers):
        """导出 JSON 格式"""
        project_id = await create_project_with_tasks(client, auth_headers)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/export/json", headers=auth_headers)
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

        data = resp.json()
        assert data["project_name"] == "导出测试项目"
        assert len(data["tasks"]) >= 2  # 至少2个根任务
        assert len(data["tags"]) == 1
        assert "exported_at" in data

    @pytest.mark.asyncio
    async def test_export_json_tree_structure(self, client: AsyncClient, auth_headers):
        """导出的 JSON 应包含正确的树形结构"""
        project_id = await create_project_with_tasks(client, auth_headers)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/export/json", headers=auth_headers)
        data = resp.json()

        # 找到 "根任务1"，它应该有子任务
        root1 = next((t for t in data["tasks"] if t["name"] == "根任务1"), None)
        assert root1 is not None
        assert len(root1["children"]) == 1
        assert root1["children"][0]["name"] == "子任务1A"


# ==================== Markdown 导出 ====================

class TestExportMarkdown:
    """Markdown 导出测试用例"""

    @pytest.mark.asyncio
    async def test_export_markdown(self, client: AsyncClient, auth_headers):
        """导出 Markdown 格式"""
        project_id = await create_project_with_tasks(client, auth_headers)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/export/markdown", headers=auth_headers)
        assert resp.status_code == 200
        content = resp.text
        assert "导出测试项目" in content
        assert "根任务1" in content


# ==================== Excel 导出 ====================

class TestExportExcel:
    """Excel 导出测试用例"""

    @pytest.mark.asyncio
    async def test_export_excel(self, client: AsyncClient, auth_headers):
        """导出 Excel 格式"""
        project_id = await create_project_with_tasks(client, auth_headers)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/export/excel", headers=auth_headers)
        assert resp.status_code == 200
        # 检查 content-type 为 Excel MIME
        assert "spreadsheet" in resp.headers.get("content-type", "")


# ==================== JSON 导入 ====================

class TestImportJSON:
    """JSON 导入测试用例"""

    @pytest.mark.asyncio
    async def test_import_json(self, client: AsyncClient, auth_headers):
        """从 JSON 导入任务"""
        # 创建目标项目
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "导入目标项目"
        })
        project_id = resp.json()["data"]["id"]

        # 构造导入数据
        import_data = {
            "project_name": "外部项目",
            "tasks": [
                {
                    "name": "导入任务A",
                    "status": "pending",
                    "priority": "high",
                    "children": [
                        {"name": "导入子任务A1", "status": "pending", "priority": "medium", "children": []}
                    ]
                },
                {"name": "导入任务B", "status": "in_progress", "priority": "low", "children": []}
            ],
            "tags": [
                {"name": "导入标签", "color": "#722ed1"}
            ]
        }

        # 使用 multipart/form-data 上传
        import io
        file_content = json.dumps(import_data, ensure_ascii=False).encode("utf-8")
        files = {"file": ("import.json", io.BytesIO(file_content), "application/json")}

        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/import/json", headers=auth_headers, files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["task_count"] == 3  # 2个根 + 1个子
        assert data["data"]["tag_count"] == 1

    @pytest.mark.asyncio
    async def test_import_invalid_json(self, client: AsyncClient, auth_headers):
        """导入无效 JSON 文件应返回 400"""
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "导入目标项目2"
        })
        project_id = resp.json()["data"]["id"]

        import io
        files = {"file": ("bad.json", io.BytesIO(b"not valid json {{{"), "application/json")}

        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/import/json", headers=auth_headers, files=files)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_import_empty_tasks(self, client: AsyncClient, auth_headers):
        """导入空任务列表应返回 400"""
        resp = await client.post("/api/v1/tasktree/projects", headers=auth_headers, json={
            "name": "导入目标项目3"
        })
        project_id = resp.json()["data"]["id"]

        import io
        data = json.dumps({"tasks": []}).encode("utf-8")
        files = {"file": ("empty.json", io.BytesIO(data), "application/json")}

        resp = await client.post(f"/api/v1/tasktree/projects/{project_id}/import/json", headers=auth_headers, files=files)
        assert resp.status_code == 400


# ==================== 权限 ====================

class TestExportAccess:
    """导出权限测试"""

    @pytest.mark.asyncio
    async def test_export_unauthorized(self, client: AsyncClient, auth_headers, auth_headers2):
        """非成员导出应返回 403"""
        project_id = await create_project_with_tasks(client, auth_headers)

        resp = await client.get(f"/api/v1/tasktree/projects/{project_id}/export/json", headers=auth_headers2)
        assert resp.status_code == 403
