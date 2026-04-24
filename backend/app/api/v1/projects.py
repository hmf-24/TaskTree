"""
TaskTree 项目管理路由
====================
提供项目 CRUD、归档、成员管理等端点。
所有操作都通过 get_project_with_access() 进行权限校验。
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import User, Project, ProjectMember, Task
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDetailResponse,
    ProjectArchiveRequest, MemberCreate, MemberUpdate, MemberResponse,
    MessageResponse, PaginatedResponse
)
from app.api.v1.auth import get_current_user

router = APIRouter()


async def get_project_with_access(
    project_id: int,
    db: AsyncSession,
    current_user: User,
    require_owner: bool = False
) -> Project:
    """获取项目并验证权限"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 检查权限：所有者或成员
    if project.owner_id == current_user.id:
        return project

    result = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=403, detail="没有权限访问此项目")

    if require_owner and member.role != "owner":
        raise HTTPException(status_code=403, detail="需要项目所有者权限")

    return project


@router.post("", response_model=MessageResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 将字符串日期转换为 date 对象
    start_date = None
    end_date = None
    if project_data.start_date:
        start_date = date.fromisoformat(project_data.start_date)
    if project_data.end_date:
        end_date = date.fromisoformat(project_data.end_date)

    project = Project(
        name=project_data.name,
        description=project_data.description,
        start_date=start_date,
        end_date=end_date,
        owner_id=current_user.id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return MessageResponse(
        code=201,
        message="创建成功",
        data={
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
            "start_date": str(project.start_date) if project.start_date else None,
            "end_date": str(project.end_date) if project.end_date else None,
            "status": project.status,
            "is_archived": project.is_archived
        }
    )


@router.get("", response_model=MessageResponse)
async def list_projects(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 构建查询：用户拥有的项目 + 用户是成员的项目
    owned_subquery = select(Project.id).where(Project.owner_id == current_user.id)
    member_subquery = select(ProjectMember.project_id).where(
        ProjectMember.user_id == current_user.id
    )

    project_ids_query = owned_subquery.union(member_subquery)

    # 查询项目
    query = select(Project).where(Project.id.in_(project_ids_query))

    if status:
        query = query.where(Project.status == status)

    # 统计总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return MessageResponse(
        data={
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "owner_id": p.owner_id,
                    "status": p.status,
                    "is_archived": p.is_archived,
                    "created_at": p.created_at.isoformat()
                }
                for p in projects
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/{project_id}", response_model=MessageResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_with_access(project_id, db, current_user)

    # 统计任务数和已完成数 - 使用单个查询
    result = await db.execute(
        select(
            func.count(Task.id).label('total'),
            func.sum(case((Task.status == "completed", 1), else_=0)).label('completed')
        ).where(Task.project_id == project_id)
    )
    stats = result.one()
    task_count = stats.total or 0
    completed_count = stats.completed or 0

    return MessageResponse(
        data={
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "owner_id": project.owner_id,
            "start_date": str(project.start_date) if project.start_date else None,
            "end_date": str(project.end_date) if project.end_date else None,
            "status": project.status,
            "is_archived": project.is_archived,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "task_count": task_count,
            "completed_count": completed_count
        }
    )


@router.put("/{project_id}", response_model=MessageResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_with_access(project_id, db, current_user, require_owner=True)

    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.start_date is not None:
        project.start_date = project_data.start_date
    if project_data.end_date is not None:
        project.end_date = project_data.end_date

    await db.commit()
    await db.refresh(project)

    return MessageResponse(message="更新成功", data={"id": project.id, "name": project.name})


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除项目及其所有关联数据（任务、成员、标签等）"""
    project = await get_project_with_access(project_id, db, current_user, require_owner=True)
    
    try:
        # 级联删除会自动处理所有关联数据
        await db.delete(project)
        await db.commit()
        return MessageResponse(message="删除成功")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


@router.post("/{project_id}/archive", response_model=MessageResponse)
async def archive_project(
    project_id: int,
    archive_data: ProjectArchiveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_with_access(project_id, db, current_user, require_owner=True)
    project.is_archived = archive_data.archived
    project.status = "archived" if archive_data.archived else "active"
    await db.commit()

    return MessageResponse(message="归档成功" if archive_data.archived else "取消归档成功")


# ========== 项目成员管理 ==========

@router.get("/{project_id}/members", response_model=MessageResponse)
async def get_members(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_with_access(project_id, db, current_user)

    result = await db.execute(
        select(ProjectMember)
        .options(selectinload(ProjectMember.user))
        .where(ProjectMember.project_id == project_id)
    )
    members = result.scalars().all()

    return MessageResponse(
        data=[
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role,
                "created_at": m.created_at.isoformat(),
                "user": {
                    "id": m.user.id,
                    "email": m.user.email,
                    "nickname": m.user.nickname,
                    "avatar": m.user.avatar
                }
            }
            for m in members
        ]
    )


@router.post("/{project_id}/members", response_model=MessageResponse)
async def add_member(
    project_id: int,
    member_data: MemberCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_with_access(project_id, db, current_user, require_owner=True)

    # 查找用户
    result = await db.execute(select(User).where(User.email == member_data.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已是成员
    result = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user.id
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户已是项目成员")

    # 添加成员
    member = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=member_data.role
    )
    db.add(member)
    await db.commit()

    return MessageResponse(code=201, message="添加成员成功")


@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    project = await get_project_with_access(project_id, db, current_user, require_owner=True)

    result = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    await db.delete(member)
    await db.commit()

    return MessageResponse(message="移除成员成功")


@router.put("/{project_id}/members/{user_id}", response_model=MessageResponse)
async def update_member(
    project_id: int,
    user_id: int,
    member_data: MemberUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await get_project_with_access(project_id, db, current_user, require_owner=True)

    result = await db.execute(
        select(ProjectMember).where(
            and_(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id
            )
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")

    member.role = member_data.role
    await db.commit()

    return MessageResponse(message="更新成员角色成功")