"""
TaskTree 任务路由
================
提供任务 CRUD、拖拽移动、批量创建、依赖关系、标签、评论等全部任务相关端点。
状态流转会进行合法性校验（基于 VALID_STATUS_TRANSITIONS）。
关键操作会自动创建通知记录。
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.constants import VALID_STATUS_TRANSITIONS, TaskStatus
from app.models import (
    User, Project, Task, TaskDependency, TaskTag, TaskTagRelation,
    TaskComment, ProjectMember, Notification
)
from app.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, TaskDetailResponse,
    TaskMoveRequest, TaskDeleteQuery, BatchTaskCreate,
    DependencyCreate, DependencyResponse, DependencyCheckResponse,
    TagCreate, TagUpdate, TagResponse, TaskTagsRequest,
    CommentCreate, CommentResponse, MessageResponse
)
from app.api.v1.auth import get_current_user

router = APIRouter()


async def get_task_with_access(task_id: int, db: AsyncSession, current_user: User) -> Task:
    """获取任务并验证当前用户是否有权限访问该任务所属项目。

    Raises:
        HTTPException 404: 任务不存在。
        HTTPException 403: 用户无权访问。
    """
    result = await db.execute(
        select(Task).options(selectinload(Task.project)).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查项目权限：项目所有者或项目成员
    project = task.project
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


async def create_notification(
    db: AsyncSession,
    user_id: int,
    type: str,
    title: str,
    content: str = "",
    related_id: int | None = None,
    related_type: str | None = None,
):
    """创建一条通知记录并写入数据库（不单独 commit，由调用方统一 commit）。"""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
        related_type=related_type,
    )
    db.add(notification)


def validate_status_transition(current_status: str, new_status: str):
    """校验任务状态流转是否合法。

    Raises:
        HTTPException 400: 不允许的状态转换。
    """
    if current_status == new_status:
        return  # 相同状态不需要验证
    try:
        current_enum = TaskStatus(current_status)
        new_enum = TaskStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的状态值: {new_status}")

    allowed = VALID_STATUS_TRANSITIONS.get(current_enum, [])
    if new_enum not in allowed:
        allowed_labels = [s.value for s in allowed]
        raise HTTPException(
            status_code=400,
            detail=f"不允许从 '{current_status}' 转换为 '{new_status}'。允许的目标状态: {allowed_labels}"
        )


def build_task_tree(tasks: list[Task]) -> list[dict]:
    """构建任务树形结构 - 使用 HashMap 映射表优化（O(n) 复杂度）。

    返回完整的任务字段，以便前端的树形/看板/甘特图/列表等视图正常工作。
    """
    if not tasks:
        return []

    # 构建 parent_id -> children 映射
    children_map: dict[int | None, list[Task]] = {}
    for task in tasks:
        parent_id = task.parent_id if task.parent_id else None
        if parent_id not in children_map:
            children_map[parent_id] = []
        children_map[parent_id].append(task)

    def build_children(parent_id: int | None) -> list[dict]:
        result = []
        for task in sorted(children_map.get(parent_id, []), key=lambda t: t.sort_order):
            result.append({
                "id": task.id,
                "project_id": task.project_id,
                "parent_id": task.parent_id,
                "name": task.name,
                "description": task.description,
                "assignee_id": task.assignee_id,
                "status": task.status,
                "priority": task.priority,
                "progress": task.progress,
                "estimated_time": task.estimated_time,
                "actual_time": task.actual_time,
                "start_date": str(task.start_date) if task.start_date else None,
                "due_date": str(task.due_date) if task.due_date else None,
                "sort_order": task.sort_order,
                "children": build_children(task.id)
            })
        return result

    return build_children(None)


# ========== 任务CRUD ==========

@router.post("/projects/{project_id}/tasks", response_model=MessageResponse)
async def create_task(
    project_id: int,
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """在指定项目下创建一个新任务，可选指定父任务。"""
    # 验证项目权限
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查项目权限
    if project.owner_id != current_user.id:
        from app.models import ProjectMember
        result = await db.execute(
            select(ProjectMember).where(
                and_(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == current_user.id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="没有权限")

    # 验证父任务
    parent_task = None
    if task_data.parent_id:
        result = await db.execute(select(Task).where(Task.id == task_data.parent_id))
        parent_task = result.scalar_one_or_none()
        if not parent_task or parent_task.project_id != project_id:
            raise HTTPException(status_code=400, detail="父任务不存在")

    task = Task(
        project_id=project_id,
        parent_id=task_data.parent_id,
        name=task_data.name,
        description=task_data.description,
        assignee_id=task_data.assignee_id,
        priority=task_data.priority,
        start_date=task_data.start_date,
        due_date=task_data.due_date,
        estimated_time=task_data.estimated_time
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return MessageResponse(
        code=201,
        message="创建成功",
        data={
            "id": task.id,
            "project_id": task.project_id,
            "parent_id": task.parent_id,
            "name": task.name,
            "description": task.description,
            "assignee_id": task.assignee_id,
            "status": task.status,
            "priority": task.priority,
            "progress": task.progress
        }
    )


@router.get("/projects/{project_id}/tasks/tree", response_model=MessageResponse)
async def get_task_tree(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取项目下所有任务的树形结构（含完整字段）。"""
    # 查询所有任务
    result = await db.execute(
        select(Task).where(Task.project_id == project_id)
    )
    tasks = result.scalars().all()

    # 构建树形结构
    tree = build_task_tree(list(tasks))

    return MessageResponse(data=tree)


@router.get("/projects/{project_id}/tasks", response_model=MessageResponse)
async def list_tasks(
    project_id: int,
    parent_id: int = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Task).where(Task.project_id == project_id)

    if parent_id is not None:
        query = query.where(Task.parent_id == parent_id)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)

    # 统计
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.order_by(Task.sort_order).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    return MessageResponse(
        data={
            "items": [
                {
                    "id": t.id,
                    "project_id": t.project_id,
                    "parent_id": t.parent_id,
                    "name": t.name,
                    "description": t.description,
                    "assignee_id": t.assignee_id,
                    "status": t.status,
                    "priority": t.priority,
                    "progress": t.progress,
                    "sort_order": t.sort_order
                }
                for t in tasks
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/tasks/{task_id}", response_model=MessageResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_with_access(task_id, db, current_user)

    # 获取子任务
    result = await db.execute(
        select(Task).where(Task.parent_id == task_id)
    )
    children = result.scalars().all()

    # 获取标签
    result = await db.execute(
        select(TaskTag).join(TaskTagRelation).where(TaskTagRelation.task_id == task_id)
    )
    tags = result.scalars().all()

    # 获取依赖
    result = await db.execute(
        select(TaskDependency).where(
            (TaskDependency.task_id == task_id) | (TaskDependency.dependent_task_id == task_id)
        )
    )
    dependencies = result.scalars().all()

    return MessageResponse(
        data={
            "id": task.id,
            "project_id": task.project_id,
            "parent_id": task.parent_id,
            "name": task.name,
            "description": task.description,
            "assignee_id": task.assignee_id,
            "status": task.status,
            "priority": task.priority,
            "progress": task.progress,
            "estimated_time": task.estimated_time,
            "actual_time": task.actual_time,
            "start_date": str(task.start_date) if task.start_date else None,
            "due_date": str(task.due_date) if task.due_date else None,
            "sort_order": task.sort_order,
            "children": [
                {"id": c.id, "name": c.name, "status": c.status, "progress": c.progress}
                for c in children
            ],
            "tags": [
                {"id": t.id, "name": t.name, "color": t.color}
                for t in tags
            ],
            "dependencies": [
                {"id": d.id, "task_id": d.task_id, "dependent_task_id": d.dependent_task_id}
                for d in dependencies
            ]
        }
    )


@router.put("/tasks/{task_id}", response_model=MessageResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新任务属性，包含状态流转合法性校验和自动通知生成。"""
    task = await get_task_with_access(task_id, db, current_user)
    update_dict = task_data.model_dump(exclude_unset=True)

    # --- 状态流转校验 (CROSS-02 fix) ---
    new_status = update_dict.get("status")
    if new_status and new_status != task.status:
        validate_status_transition(task.status, new_status)

        # 任务状态变更时，向任务负责人发送通知 (CROSS-03 fix)
        if task.assignee_id and task.assignee_id != current_user.id:
            await create_notification(
                db,
                user_id=task.assignee_id,
                type="task_status",
                title=f"任务状态已更新",
                content=f'任务「{task.name}」状态已从 {task.status} 变更为 {new_status}',
                related_id=task.id,
                related_type="task",
            )

    # 更新字段
    for field, value in update_dict.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)

    return MessageResponse(message="更新成功", data={"id": task.id, "name": task.name})


@router.delete("/tasks/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: int,
    delete_children: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_with_access(task_id, db, current_user)

    if not delete_children:
        # 检查是否有子任务
        result = await db.execute(
            select(Task).where(Task.parent_id == task_id)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=400,
                detail="该任务有子任务，请先删除子任务或使用delete_children=true"
            )

    await db.delete(task)
    await db.commit()

    return MessageResponse(message="删除成功")


@router.put("/tasks/{task_id}/move", response_model=MessageResponse)
async def move_task(
    task_id: int,
    move_data: TaskMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """移动任务：改变父任务 和/或 排序位置，包含循环引用检测和同级任务 sort_order 重排。"""
    task = await get_task_with_access(task_id, db, current_user)

    new_parent_id = task.parent_id  # 默认保持不变

    if move_data.parent_id is not None:
        if move_data.parent_id == task_id:
            raise HTTPException(status_code=400, detail="不能将任务移动到自身")
        # 验证新的父任务存在且属于同一项目
        result = await db.execute(select(Task).where(Task.id == move_data.parent_id))
        parent = result.scalar_one_or_none()
        if not parent or parent.project_id != task.project_id:
            raise HTTPException(status_code=400, detail="父任务不存在")

        # 检查循环引用：沿父链向上遍历，确保不会形成环
        current_parent_id = move_data.parent_id
        while current_parent_id:
            if current_parent_id == task_id:
                raise HTTPException(status_code=400, detail="不能创建循环依赖")
            result = await db.execute(select(Task).where(Task.id == current_parent_id))
            p = result.scalar_one_or_none()
            current_parent_id = p.parent_id if p else None

        task.parent_id = move_data.parent_id
        new_parent_id = move_data.parent_id

    if move_data.sort_order is not None:
        target_order = move_data.sort_order
        # 重排同级任务的 sort_order，避免多次拖拽后序号冲突
        siblings = await db.execute(
            select(Task).where(
                and_(
                    Task.project_id == task.project_id,
                    Task.parent_id == new_parent_id if new_parent_id else Task.parent_id.is_(None),
                    Task.id != task_id
                )
            ).order_by(Task.sort_order)
        )
        sibling_list = list(siblings.scalars().all())
        # 将当前任务插入到目标位置，然后重新编号
        sibling_list.insert(min(target_order, len(sibling_list)), task)
        for idx, t in enumerate(sibling_list):
            t.sort_order = idx

    await db.commit()

    return MessageResponse(message="移动成功")


@router.post("/projects/{project_id}/tasks/batch", response_model=MessageResponse)
async def batch_create_tasks(
    project_id: int,
    batch_data: BatchTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 验证项目
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 创建任务
    tasks = []
    for task_data in batch_data.tasks:
        task = Task(
            project_id=project_id,
            name=task_data.name,
            description=task_data.description,
            priority=task_data.priority
        )
        tasks.append(task)

    db.add_all(tasks)
    await db.commit()

    return MessageResponse(
        code=201,
        message=f"成功创建{len(tasks)}个任务",
        data={"count": len(tasks)}
    )


# ========== 依赖关系 ==========

@router.post("/tasks/{task_id}/dependencies", response_model=MessageResponse)
async def create_dependency(
    task_id: int,
    dep_data: DependencyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_with_access(task_id, db, current_user)

    # 验证依赖任务
    result = await db.execute(select(Task).where(Task.id == dep_data.dependent_task_id))
    dep_task = result.scalar_one_or_none()

    if not dep_task or dep_task.project_id != task.project_id:
        raise HTTPException(status_code=400, detail="依赖任务不存在")

    # 检查是否已存在
    result = await db.execute(
        select(TaskDependency).where(
            and_(
                TaskDependency.task_id == task_id,
                TaskDependency.dependent_task_id == dep_data.dependent_task_id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="依赖关系已存在")

    dependency = TaskDependency(
        task_id=task_id,
        dependent_task_id=dep_data.dependent_task_id
    )
    db.add(dependency)
    await db.commit()

    return MessageResponse(code=201, message="创建依赖成功")


@router.delete("/tasks/{task_id}/dependencies/{dependent_task_id}", response_model=MessageResponse)
async def delete_dependency(
    task_id: int,
    dependent_task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_task_with_access(task_id, db, current_user)

    result = await db.execute(
        select(TaskDependency).where(
            and_(
                TaskDependency.task_id == task_id,
                TaskDependency.dependent_task_id == dependent_task_id
            )
        )
    )
    dependency = result.scalar_one_or_none()

    if not dependency:
        raise HTTPException(status_code=404, detail="依赖关系不存在")

    await db.delete(dependency)
    await db.commit()

    return MessageResponse(message="删除依赖成功")


@router.get("/tasks/{task_id}/dependencies/check", response_model=MessageResponse)
async def check_dependency(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_with_access(task_id, db, current_user)

    # 查找所有前置任务
    result = await db.execute(
        select(Task).join(
            TaskDependency,
            TaskDependency.task_id == Task.id
        ).where(TaskDependency.dependent_task_id == task_id)
    )
    blocking_tasks = result.scalars().all()

    can_start = all(t.status == "completed" for t in blocking_tasks)

    return MessageResponse(
        data={
            "can_start": can_start,
            "blocked_by": [
                {"task_id": t.id, "name": t.name, "status": t.status}
                for t in blocking_tasks if t.status != "completed"
            ]
        }
    )


# ========== 标签 ==========

@router.get("/projects/{project_id}/tags", response_model=MessageResponse)
async def list_tags(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskTag).where(TaskTag.project_id == project_id)
    )
    tags = result.scalars().all()

    return MessageResponse(
        data=[
            {"id": t.id, "name": t.name, "color": t.color}
            for t in tags
        ]
    )


@router.post("/projects/{project_id}/tags", response_model=MessageResponse)
async def create_tag(
    project_id: int,
    tag_data: TagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tag = TaskTag(
        project_id=project_id,
        name=tag_data.name,
        color=tag_data.color
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)

    return MessageResponse(code=201, message="创建成功", data={"id": tag.id, "name": tag.name})


@router.put("/tags/{tag_id}", response_model=MessageResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TaskTag).where(TaskTag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    if tag_data.name:
        tag.name = tag_data.name
    if tag_data.color:
        tag.color = tag_data.color

    await db.commit()

    return MessageResponse(message="更新成功")


@router.delete("/tags/{tag_id}", response_model=MessageResponse)
async def delete_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TaskTag).where(TaskTag.id == tag_id))
    tag = result.scalar_one_or_none()

    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    await db.delete(tag)
    await db.commit()

    return MessageResponse(message="删除成功")


@router.post("/tasks/{task_id}/tags", response_model=MessageResponse)
async def add_tags_to_task(
    task_id: int,
    tag_data: TaskTagsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await get_task_with_access(task_id, db, current_user)

    # 删除旧关联
    result = await db.execute(
        select(TaskTagRelation).where(TaskTagRelation.task_id == task_id)
    )
    old_relations = result.scalars().all()
    for relation in old_relations:
        await db.delete(relation)

    # 添加新关联
    for tag_id in tag_data.tag_ids:
        result = await db.execute(select(TaskTag).where(TaskTag.id == tag_id))
        tag = result.scalar_one_or_none()
        if tag and tag.project_id == task.project_id:
            relation = TaskTagRelation(task_id=task_id, tag_id=tag_id)
            db.add(relation)

    await db.commit()

    return MessageResponse(message="标签更新成功")


# ========== 评论 ==========

@router.get("/tasks/{task_id}/comments", response_model=MessageResponse)
async def list_comments(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_task_with_access(task_id, db, current_user)

    result = await db.execute(
        select(TaskComment)
        .options(selectinload(TaskComment.user))
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.desc())
    )
    comments = result.scalars().all()

    return MessageResponse(
        data=[
            {
                "id": c.id,
                "task_id": c.task_id,
                "user_id": c.user_id,
                "content": c.content,
                "created_at": c.created_at.isoformat(),
                "user": {
                    "id": c.user.id,
                    "email": c.user.email,
                    "nickname": c.user.nickname,
                    "avatar": c.user.avatar
                }
            }
            for c in comments
        ]
    )


@router.post("/tasks/{task_id}/comments", response_model=MessageResponse)
async def create_comment(
    task_id: int,
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建任务评论，并向任务负责人发送通知 (CROSS-03 fix)。"""
    task = await get_task_with_access(task_id, db, current_user)

    comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        content=comment_data.content
    )
    db.add(comment)

    # 向任务负责人发送评论通知（不给自己发）
    if task.assignee_id and task.assignee_id != current_user.id:
        await create_notification(
            db,
            user_id=task.assignee_id,
            type="comment",
            title="新评论",
            content=f'{current_user.nickname or current_user.email} 评论了任务「{task.name}」',
            related_id=task_id,
            related_type="task",
        )

    # 处理 @ 提及通知
    if comment_data.mentions:
        for mentioned_user_id in comment_data.mentions:
            if mentioned_user_id != current_user.id:
                await create_notification(
                    db,
                    user_id=mentioned_user_id,
                    type="mention",
                    title="有人提及了你",
                    content=f'{current_user.nickname or current_user.email} 在任务「{task.name}」中 @了你',
                    related_id=task_id,
                    related_type="task",
                )

    await db.commit()
    await db.refresh(comment)

    return MessageResponse(code=201, message="评论成功", data={"id": comment.id})


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id)
    )
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    if comment.user_id != current_user.id:
        # 检查是否是项目所有者或管理员
        result = await db.execute(
            select(Task).options(selectinload(Task.project)).where(Task.id == comment.task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            # 检查是否是项目所有者
            if task.project.owner_id == current_user.id:
                pass  # 所有者可以删除
            else:
                # 检查是否是管理员
                result = await db.execute(
                    select(ProjectMember).where(
                        and_(
                            ProjectMember.project_id == task.project_id,
                            ProjectMember.user_id == current_user.id
                        )
                    )
                )
                member = result.scalar_one_or_none()
                if not member or member.role not in ('owner', 'admin'):
                    raise HTTPException(status_code=403, detail="没有权限删除此评论")
        else:
            raise HTTPException(status_code=404, detail="评论关联的任务不存在")

    await db.delete(comment)
    await db.commit()

    return MessageResponse(message="删除成功")