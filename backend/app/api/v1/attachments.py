"""
TaskTree 附件管理路由
====================
提供任务附件的上传、下载、删除等端点。
支持多种文件格式，包含文件类型和大小验证。
"""
import os
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.models import User, Task, TaskAttachment, Project, ProjectMember
from app.schemas import AttachmentResponse, AttachmentListResponse, MessageResponse
from app.api.v1.auth import get_current_user
from app.utils.file_utils import (
    validate_file_type,
    validate_file_size,
    generate_unique_filename
)

router = APIRouter(prefix="/attachments", tags=["attachments"])


async def get_task_with_access(task_id: int, db: AsyncSession, current_user: User) -> Task:
    """获取任务并验证当前用户是否有权限访问该任务所属项目。

    Raises:
        HTTPException 404: 任务不存在。
        HTTPException 403: 用户无权访问。
    """
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查项目权限：项目所有者或项目成员
    result = await db.execute(
        select(Project).where(Project.id == task.project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    if project.owner_id != current_user.id:
        result = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id == current_user.id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="没有权限访问此任务")

    return task


@router.post("/tasks/{task_id}/attachments", response_model=MessageResponse)
async def upload_attachment(
    task_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上传任务附件
    
    - 验证用户权限
    - 验证文件类型和大小
    - 生成唯一文件名
    - 保存文件到文件系统
    - 创建数据库记录
    """
    # 添加日志以便调试
    print(f"[DEBUG] Uploading file: {file.filename}, content_type: {file.content_type}")
    
    # Step 1: 验证任务访问权限
    task = await get_task_with_access(task_id, db, current_user)
    
    # Step 2: 验证文件类型
    is_valid_type, type_message = validate_file_type(file.filename)
    if not is_valid_type:
        print(f"[DEBUG] File type validation failed: {type_message}")
        raise HTTPException(status_code=400, detail=type_message)
    
    # Step 3: 读取文件内容以获取大小
    file_content = await file.read()
    file_size = len(file_content)
    
    print(f"[DEBUG] File size: {file_size} bytes")
    
    # Step 4: 验证文件大小
    is_valid_size, size_message = validate_file_size(file_size)
    if not is_valid_size:
        print(f"[DEBUG] File size validation failed: {size_message}")
        raise HTTPException(status_code=400, detail=size_message)
    
    # Step 5: 生成唯一文件名
    unique_filename = generate_unique_filename(file.filename)
    
    # Step 6: 创建目录结构
    upload_dir = Path(f"backend/uploads/attachments/{task_id}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 7: 保存文件到文件系统
    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Step 8: 创建数据库记录
    attachment = TaskAttachment(
        task_id=task_id,
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    
    # Step 9: 返回标准格式响应
    return MessageResponse(
        code=201,
        message="上传成功",
        data={
            "id": attachment.id,
            "task_id": attachment.task_id,
            "user_id": attachment.user_id,
            "filename": attachment.filename,
            "file_path": attachment.file_path,
            "file_size": attachment.file_size,
            "mime_type": attachment.mime_type,
            "created_at": attachment.created_at.isoformat()
        }
    )


@router.get("/tasks/{task_id}/attachments", response_model=MessageResponse)
async def get_task_attachments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    查询任务附件列表
    
    - 验证用户权限
    - 查询该任务的所有附件记录
    - 按创建时间降序排序
    - 返回附件列表和总数
    """
    # Step 1: 验证任务访问权限
    await get_task_with_access(task_id, db, current_user)
    
    # Step 2: 查询该任务的所有附件记录，按创建时间降序排序
    result = await db.execute(
        select(TaskAttachment)
        .where(TaskAttachment.task_id == task_id)
        .order_by(TaskAttachment.created_at.desc())
    )
    attachments = result.scalars().all()
    
    # Step 3: 构建响应
    attachment_list = [
        {
            "id": att.id,
            "task_id": att.task_id,
            "user_id": att.user_id,
            "filename": att.filename,
            "file_path": att.file_path,
            "file_size": att.file_size,
            "mime_type": att.mime_type,
            "created_at": att.created_at.isoformat()
        }
        for att in attachments
    ]
    
    return MessageResponse(
        data=attachment_list,
        message="获取成功"
    )


@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    下载附件
    
    - 查询附件记录并验证存在性
    - 通过附件的 task_id 调用 get_task_with_access() 验证用户权限
    - 验证物理文件存在
    - 使用 FileResponse 返回文件流
    - 设置 Content-Disposition header 为 "attachment; filename={encoded_filename}"
    - 设置正确的 MIME type
    """
    # Step 1: 查询附件记录
    result = await db.execute(
        select(TaskAttachment).where(TaskAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    
    # Step 2: 验证用户权限（通过任务访问权限）
    await get_task_with_access(attachment.task_id, db, current_user)
    
    # Step 3: 验证物理文件存在
    file_path = Path(attachment.file_path)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # Step 4: 返回文件流
    # 对文件名进行 URL 编码以支持中文和特殊字符
    encoded_filename = quote(attachment.filename)
    
    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{encoded_filename}"'
        }
    )


@router.delete("/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除附件
    
    - 查询附件记录并验证存在性
    - 通过附件的 task_id 调用 get_task_with_access() 验证用户权限
    - 删除物理文件（如果存在）
    - 删除数据库记录
    - 提交事务
    - 返回成功消息
    """
    # Step 1: 查询附件记录
    result = await db.execute(
        select(TaskAttachment).where(TaskAttachment.id == attachment_id)
    )
    attachment = result.scalar_one_or_none()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")
    
    # Step 2: 验证用户权限（通过任务访问权限）
    await get_task_with_access(attachment.task_id, db, current_user)
    
    # Step 3: 删除物理文件（如果存在）
    file_path = Path(attachment.file_path)
    if file_path.exists() and file_path.is_file():
        try:
            os.remove(file_path)
        except OSError as e:
            # 记录错误但继续删除数据库记录
            print(f"Warning: Failed to delete physical file {file_path}: {e}")
    
    # Step 4: 删除数据库记录
    await db.delete(attachment)
    
    # Step 5: 提交事务
    await db.commit()
    
    # Step 6: 返回标准格式响应
    return MessageResponse(message="附件删除成功")
