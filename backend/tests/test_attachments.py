"""
TaskTree 附件功能测试
====================
测试任务附件的上传、查询、下载和删除功能。
"""
import pytest
import io
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User, Project, Task


@pytest.mark.asyncio
async def test_upload_attachment_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试成功上传附件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 创建测试文件
    file_content = b"This is a test file content"
    file_data = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    # 上传附件
    response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应数据
    assert data["task_id"] == task.id
    assert data["user_id"] == test_user.id
    assert data["filename"] == "test.txt"
    assert data["file_size"] == len(file_content)
    assert data["mime_type"] == "text/plain"
    assert "id" in data
    assert "file_path" in data
    assert "created_at" in data
    
    # 验证文件已保存
    file_path = Path(data["file_path"])
    assert file_path.exists()
    
    # 清理测试文件
    if file_path.exists():
        file_path.unlink()
        # 清理目录
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_upload_attachment_invalid_file_type(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试上传不支持的文件类型"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 创建不支持的文件类型
    file_content = b"Malicious content"
    file_data = {
        "file": ("malicious.exe", io.BytesIO(file_content), "application/x-msdownload")
    }
    
    # 尝试上传
    response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    
    assert response.status_code == 400
    assert "不支持的文件类型" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_attachment_file_too_large(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试上传超过大小限制的文件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 创建超大文件 (51MB)
    file_content = b"x" * (51 * 1024 * 1024)
    file_data = {
        "file": ("large.txt", io.BytesIO(file_content), "text/plain")
    }
    
    # 尝试上传
    response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    
    assert response.status_code == 400
    assert "文件大小超过限制" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_attachment_task_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """测试上传附件到不存在的任务"""
    file_content = b"Test content"
    file_data = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    response = await client.post(
        "/api/v1/attachments/tasks/99999/attachments",
        headers=auth_headers,
        files=file_data
    )
    
    assert response.status_code == 404
    assert "任务不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_attachment_no_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user2: User,
    auth_headers2: dict
):
    """测试上传附件到无权限访问的任务"""
    # 创建测试项目和任务（属于 test_user）
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 使用 test_user2 的认证头尝试上传
    file_content = b"Test content"
    file_data = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers2,
        files=file_data
    )
    
    assert response.status_code == 403
    assert "没有权限访问此任务" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_attachment_with_chinese_filename(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试上传中文文件名的附件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 创建中文文件名的文件
    file_content = b"Chinese filename test"
    file_data = {
        "file": ("测试文档.txt", io.BytesIO(file_content), "text/plain")
    }
    
    # 上传附件
    response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证原始文件名保留
    assert data["filename"] == "测试文档.txt"
    
    # 清理测试文件
    file_path = Path(data["file_path"])
    if file_path.exists():
        file_path.unlink()
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_get_task_attachments_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试成功查询任务附件列表"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 上传多个附件
    file_paths = []
    for i in range(3):
        file_content = f"Test file {i}".encode()
        file_data = {
            "file": (f"test{i}.txt", io.BytesIO(file_content), "text/plain")
        }
        
        response = await client.post(
            f"/api/v1/attachments/tasks/{task.id}/attachments",
            headers=auth_headers,
            files=file_data
        )
        assert response.status_code == 200
        file_paths.append(Path(response.json()["file_path"]))
    
    # 查询附件列表
    response = await client.get(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应结构
    assert "attachments" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["attachments"]) == 3
    
    # 验证附件按创建时间降序排列（最新的在前）
    attachments = data["attachments"]
    assert attachments[0]["filename"] == "test2.txt"
    assert attachments[1]["filename"] == "test1.txt"
    assert attachments[2]["filename"] == "test0.txt"
    
    # 验证每个附件包含所有必需字段
    for attachment in attachments:
        assert "id" in attachment
        assert "task_id" in attachment
        assert "user_id" in attachment
        assert "filename" in attachment
        assert "file_path" in attachment
        assert "file_size" in attachment
        assert "mime_type" in attachment
        assert "created_at" in attachment
        assert attachment["task_id"] == task.id
        assert attachment["user_id"] == test_user.id
    
    # 清理测试文件
    for file_path in file_paths:
        if file_path.exists():
            file_path.unlink()
    try:
        file_paths[0].parent.rmdir()
    except OSError:
        pass


@pytest.mark.asyncio
async def test_get_task_attachments_empty_list(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试查询没有附件的任务"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 查询附件列表
    response = await client.get(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回空列表
    assert data["attachments"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_task_attachments_task_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """测试查询不存在的任务的附件"""
    response = await client.get(
        "/api/v1/attachments/tasks/99999/attachments",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "任务不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_task_attachments_no_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user2: User,
    auth_headers2: dict
):
    """测试查询无权限访问的任务的附件"""
    # 创建测试项目和任务（属于 test_user）
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 使用 test_user2 的认证头尝试查询
    response = await client.get(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers2
    )
    
    assert response.status_code == 403
    assert "没有权限访问此任务" in response.json()["detail"]



@pytest.mark.asyncio
async def test_download_attachment_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试成功下载附件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 上传附件
    file_content = b"This is test file content for download"
    file_data = {
        "file": ("download_test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    upload_response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    assert upload_response.status_code == 200
    attachment_data = upload_response.json()
    attachment_id = attachment_data["id"]
    file_path = Path(attachment_data["file_path"])
    
    # 下载附件
    download_response = await client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers=auth_headers
    )
    
    assert download_response.status_code == 200
    
    # 验证响应内容
    assert download_response.content == file_content
    
    # 验证响应头
    assert "content-disposition" in download_response.headers
    content_disposition = download_response.headers["content-disposition"]
    assert "attachment" in content_disposition
    assert "download_test.txt" in content_disposition
    
    # 验证 MIME type
    assert download_response.headers["content-type"] == "text/plain; charset=utf-8"
    
    # 清理测试文件
    if file_path.exists():
        file_path.unlink()
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_download_attachment_with_chinese_filename(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试下载中文文件名的附件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 上传中文文件名的附件
    file_content = b"Chinese filename download test"
    file_data = {
        "file": ("测试下载.txt", io.BytesIO(file_content), "text/plain")
    }
    
    upload_response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    assert upload_response.status_code == 200
    attachment_data = upload_response.json()
    attachment_id = attachment_data["id"]
    file_path = Path(attachment_data["file_path"])
    
    # 下载附件
    download_response = await client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers=auth_headers
    )
    
    assert download_response.status_code == 200
    assert download_response.content == file_content
    
    # 验证 Content-Disposition header 包含编码后的文件名
    content_disposition = download_response.headers["content-disposition"]
    assert "attachment" in content_disposition
    # URL 编码后的中文文件名应该存在
    from urllib.parse import quote
    encoded_filename = quote("测试下载.txt")
    assert encoded_filename in content_disposition
    
    # 清理测试文件
    if file_path.exists():
        file_path.unlink()
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_download_attachment_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """测试下载不存在的附件"""
    response = await client.get(
        "/api/v1/attachments/99999/download",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "附件不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_download_attachment_no_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user2: User,
    auth_headers: dict,
    auth_headers2: dict
):
    """测试下载无权限访问的附件"""
    # 创建测试项目和任务（属于 test_user）
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 使用 test_user 上传附件
    file_content = b"Test content"
    file_data = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    upload_response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    assert upload_response.status_code == 200
    attachment_data = upload_response.json()
    attachment_id = attachment_data["id"]
    file_path = Path(attachment_data["file_path"])
    
    # 使用 test_user2 的认证头尝试下载
    download_response = await client.get(
        f"/api/v1/attachments/{attachment_id}/download",
        headers=auth_headers2
    )
    
    assert download_response.status_code == 403
    assert "没有权限访问此任务" in download_response.json()["detail"]
    
    # 清理测试文件
    if file_path.exists():
        file_path.unlink()
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_download_attachment_file_missing(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试下载物理文件已删除的附件"""
    from app.models import TaskAttachment
    
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 直接在数据库中创建附件记录（不创建物理文件）
    attachment = TaskAttachment(
        task_id=task.id,
        user_id=test_user.id,
        filename="missing.txt",
        file_path="backend/uploads/attachments/nonexistent/missing.txt",
        file_size=100,
        mime_type="text/plain"
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)
    
    # 尝试下载
    response = await client.get(
        f"/api/v1/attachments/{attachment.id}/download",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "文件不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_attachment_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试成功删除附件"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 上传附件
    file_content = b"This is test file content for deletion"
    file_data = {
        "file": ("delete_test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    upload_response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    assert upload_response.status_code == 200
    attachment_data = upload_response.json()
    attachment_id = attachment_data["id"]
    file_path = Path(attachment_data["file_path"])
    
    # 验证文件存在
    assert file_path.exists()
    
    # 删除附件
    delete_response = await client.delete(
        f"/api/v1/attachments/{attachment_id}",
        headers=auth_headers
    )
    
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["message"] == "附件删除成功"
    
    # 验证物理文件已删除
    assert not file_path.exists()
    
    # 验证数据库记录已删除
    from sqlalchemy import select
    from app.models import TaskAttachment
    result = await db_session.execute(
        select(TaskAttachment).where(TaskAttachment.id == attachment_id)
    )
    assert result.scalar_one_or_none() is None
    
    # 清理目录
    try:
        file_path.parent.rmdir()
    except OSError:
        pass


@pytest.mark.asyncio
async def test_delete_attachment_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """测试删除不存在的附件"""
    response = await client.delete(
        "/api/v1/attachments/99999",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "附件不存在" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_attachment_no_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_user2: User,
    auth_headers: dict,
    auth_headers2: dict
):
    """测试删除无权限访问的附件"""
    # 创建测试项目和任务（属于 test_user）
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 使用 test_user 上传附件
    file_content = b"Test content"
    file_data = {
        "file": ("test.txt", io.BytesIO(file_content), "text/plain")
    }
    
    upload_response = await client.post(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers,
        files=file_data
    )
    assert upload_response.status_code == 200
    attachment_data = upload_response.json()
    attachment_id = attachment_data["id"]
    file_path = Path(attachment_data["file_path"])
    
    # 使用 test_user2 的认证头尝试删除
    delete_response = await client.delete(
        f"/api/v1/attachments/{attachment_id}",
        headers=auth_headers2
    )
    
    assert delete_response.status_code == 403
    assert "没有权限访问此任务" in delete_response.json()["detail"]
    
    # 验证文件仍然存在
    assert file_path.exists()
    
    # 清理测试文件
    if file_path.exists():
        file_path.unlink()
        try:
            file_path.parent.rmdir()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_delete_attachment_file_already_deleted(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试删除物理文件已不存在的附件（应该仍然删除数据库记录）"""
    from app.models import TaskAttachment
    
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 直接在数据库中创建附件记录（不创建物理文件）
    attachment = TaskAttachment(
        task_id=task.id,
        user_id=test_user.id,
        filename="missing.txt",
        file_path="backend/uploads/attachments/nonexistent/missing.txt",
        file_size=100,
        mime_type="text/plain"
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)
    attachment_id = attachment.id
    
    # 删除附件
    delete_response = await client.delete(
        f"/api/v1/attachments/{attachment_id}",
        headers=auth_headers
    )
    
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["message"] == "附件删除成功"
    
    # 验证数据库记录已删除
    from sqlalchemy import select
    result = await db_session.execute(
        select(TaskAttachment).where(TaskAttachment.id == attachment_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_attachment_and_verify_list_updated(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict
):
    """测试删除附件后列表正确更新"""
    # 创建测试项目和任务
    project = Project(
        name="测试项目",
        owner_id=test_user.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    
    task = Task(
        project_id=project.id,
        name="测试任务",
        status="pending"
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    # 上传多个附件
    file_paths = []
    attachment_ids = []
    for i in range(3):
        file_content = f"Test file {i}".encode()
        file_data = {
            "file": (f"test{i}.txt", io.BytesIO(file_content), "text/plain")
        }
        
        response = await client.post(
            f"/api/v1/attachments/tasks/{task.id}/attachments",
            headers=auth_headers,
            files=file_data
        )
        assert response.status_code == 200
        data = response.json()
        file_paths.append(Path(data["file_path"]))
        attachment_ids.append(data["id"])
    
    # 查询附件列表，应该有 3 个
    list_response = await client.get(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 3
    
    # 删除中间的附件
    delete_response = await client.delete(
        f"/api/v1/attachments/{attachment_ids[1]}",
        headers=auth_headers
    )
    assert delete_response.status_code == 200
    
    # 再次查询附件列表，应该只有 2 个
    list_response = await client.get(
        f"/api/v1/attachments/tasks/{task.id}/attachments",
        headers=auth_headers
    )
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["total"] == 2
    
    # 验证剩余的附件是正确的
    remaining_ids = [att["id"] for att in data["attachments"]]
    assert attachment_ids[0] in remaining_ids
    assert attachment_ids[1] not in remaining_ids
    assert attachment_ids[2] in remaining_ids
    
    # 清理测试文件
    for i, file_path in enumerate(file_paths):
        if i != 1 and file_path.exists():  # 跳过已删除的
            file_path.unlink()
    try:
        file_paths[0].parent.rmdir()
    except OSError:
        pass
