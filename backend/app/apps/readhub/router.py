"""
ReadHub — API 路由
==================
所有接口统一挂载在 /api/v1/readhub 下，与 TaskTree 的 /api/v1/tasktree 物理隔离。
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import User
from app.apps.readhub.service import RssService
from app.apps.readhub.obsidian_service import ObsidianService

router = APIRouter()


# ──────────── Schemas ────────────

class FeedCreate(BaseModel):
    url: str
    name: str

class FeedOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    last_fetched_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

class ArticleOut(BaseModel):
    id: int
    feed_id: int
    title: str
    summary: Optional[str] = None
    source_url: str
    author: Optional[str] = None
    published_at: Optional[str] = None
    is_read: bool
    is_saved_to_obsidian: bool
    created_at: str

    class Config:
        from_attributes = True

class ArticleDetailOut(ArticleOut):
    content_html: Optional[str] = None


# ──────────── 订阅源管理 ────────────

@router.post("/feeds", summary="添加订阅源")
async def add_feed(
    body: FeedCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    feed = await RssService.add_feed(db, user.id, body.url, body.name)
    return {
        "code": 200,
        "message": "订阅源添加成功",
        "data": _feed_to_dict(feed),
    }


@router.get("/feeds", summary="获取订阅源列表")
async def list_feeds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    feeds = await RssService.list_feeds(db, user.id)
    return {
        "code": 200,
        "data": [_feed_to_dict(f) for f in feeds],
    }


@router.delete("/feeds/{feed_id}", summary="删除订阅源")
async def delete_feed(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ok = await RssService.delete_feed(db, feed_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="订阅源不存在或无权删除")
    return {"code": 200, "message": "删除成功"}


@router.post("/feeds/fetch", summary="手动触发拉取所有订阅源")
async def fetch_feeds(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await RssService.fetch_feeds(db, user.id)
    return {"code": 200, "data": result}


@router.get("/feeds/{feed_id}/authors", summary="获取订阅源下的所有作者/公众号")
async def get_feed_authors(
    feed_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    authors = await RssService.get_feed_authors(db, user.id, feed_id)
    return {"code": 200, "data": authors}


# ──────────── 文章管理 ────────────

@router.get("/articles", summary="获取文章列表")
async def list_articles(
    feed_id: Optional[int] = None,
    unread_only: bool = False,
    author: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await RssService.get_articles(db, user.id, feed_id, unread_only, author, page, page_size)
    return {
        "code": 200,
        "data": {
            "items": [_article_to_dict(a) for a in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "page_size": result["page_size"],
        },
    }


@router.get("/articles/{article_id}", summary="获取文章详情")
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    article = await RssService.get_article_detail(db, article_id, user.id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    # 自动标记已读
    if not article.is_read:
        await RssService.mark_read(db, article_id, user.id)
        article.is_read = True
    return {"code": 200, "data": _article_detail_to_dict(article)}

@router.post("/articles/{article_id}/ai-summary", summary="生成AI概览")
async def generate_ai_summary(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        article = await RssService.generate_ai_summary(db, article_id, user.id)
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")
        return {"code": 200, "data": {"summary": article.summary}}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/articles/{article_id}/read", summary="标记文章已读")
async def mark_article_read(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ok = await RssService.mark_read(db, article_id, user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {"code": 200, "message": "已标记为已读"}


# ──────────── Serializers ────────────

def _feed_to_dict(feed) -> dict:
    return {
        "id": feed.id,
        "url": feed.url,
        "name": feed.name,
        "is_active": feed.is_active,
        "last_fetched_at": feed.last_fetched_at.isoformat() if feed.last_fetched_at else None,
        "created_at": feed.created_at.isoformat() if feed.created_at else "",
    }


def _article_to_dict(article) -> dict:
    return {
        "id": article.id,
        "feed_id": article.feed_id,
        "title": article.title,
        "summary": article.summary,
        "source_url": article.source_url,
        "author": article.author,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "is_read": article.is_read,
        "is_saved_to_obsidian": article.is_saved_to_obsidian,
        "created_at": article.created_at.isoformat() if article.created_at else "",
    }


def _article_detail_to_dict(article) -> dict:
    d = _article_to_dict(article)
    d["content_html"] = article.content_html
    return d


# ──────────── ReadHub 设置 ────────────

class ReadHubSettingsUpdate(BaseModel):
    obsidian_vault_path: Optional[str] = None
    obsidian_folder: Optional[str] = None
    auto_fetch_enabled: Optional[bool] = None
    auto_fetch_interval: Optional[int] = None
    dingtalk_webhook: Optional[str] = None
    dingtalk_secret: Optional[str] = None
    dingtalk_client_id: Optional[str] = None
    dingtalk_client_secret: Optional[str] = None # 注意：接收明文，保存时加密
    dingtalk_stream_enabled: Optional[bool] = None
    wewe_server_url: Optional[str] = None
    wewe_auth_code: Optional[str] = None
    interest_tags: Optional[str] = None


@router.get("/settings", summary="获取 ReadHub 设置")
async def get_readhub_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = await ObsidianService.get_settings(db, user.id)
    if not settings:
        return {
            "code": 200,
            "data": {
                "obsidian_vault_path": "",
                "obsidian_folder": "ReadHub",
                "obsidian_configured": False,
                "auto_fetch_enabled": False,
                "auto_fetch_interval": 60,
                "dingtalk_webhook": "",
                "dingtalk_secret": "",
                "dingtalk_client_id": "",
                "dingtalk_stream_enabled": False,
                "wewe_server_url": "",
                "wewe_auth_code": "",
            },
        }
    client_secret = ""
    if settings.dingtalk_client_secret_encrypted:
        from app.core.crypto import decrypt_api_key
        try:
            client_secret = decrypt_api_key(settings.dingtalk_client_secret_encrypted) or ""
        except Exception:
            pass

    return {
        "code": 200,
        "data": {
            "obsidian_vault_path": settings.obsidian_vault_path or "",
            "obsidian_folder": settings.obsidian_folder or "ReadHub",
            "obsidian_configured": ObsidianService.is_configured(settings),
            "auto_fetch_enabled": settings.auto_fetch_enabled,
            "auto_fetch_interval": settings.auto_fetch_interval,
            "dingtalk_webhook": settings.dingtalk_webhook or "",
            "dingtalk_secret": settings.dingtalk_secret or "",
            "dingtalk_client_id": settings.dingtalk_client_id or "",
            "dingtalk_client_secret": client_secret,
            "dingtalk_stream_enabled": settings.dingtalk_stream_enabled,
            "wewe_server_url": settings.wewe_server_url or "",
            "wewe_auth_code": settings.wewe_auth_code or "",
            "interest_tags": settings.interest_tags or '["AI", "前沿技术", "数据中心", "算力", "GPU"]',
        },
    }


@router.put("/settings", summary="更新 ReadHub 设置")
async def update_readhub_settings(
    request: Request,
    body: ReadHubSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 构建要更新的字段字典
    update_data = body.model_dump(exclude_unset=True)
    
    settings = await ObsidianService.update_settings(
        db, user.id,
        **update_data
    )
    
    # (由于现在使用 AgentRoutine 统一接管自动拉取，此处不再独立注册定时任务)
    # 异步触发调度器重载 (如果之后需要单独拉起特定例程可以恢复)
    # from app.services.scheduler_service import SchedulerService
    # import asyncio
    # asyncio.create_task(SchedulerService.reload_user_rss_job(user.id))
    
    # 触发钉钉 Stream Client 局部重启
    from app.services.dingtalk_stream_client import restart_user_stream_client
    # 传入 settings 参数
    asyncio.create_task(restart_user_stream_client(request.app, user.id, settings, app_source="readhub"))
    
    return {
        "code": 200,
        "message": "设置已保存",
        "data": {
            "obsidian_vault_path": settings.obsidian_vault_path or "",
            "obsidian_folder": settings.obsidian_folder or "ReadHub",
            "obsidian_configured": ObsidianService.is_configured(settings),
            "auto_fetch_enabled": settings.auto_fetch_enabled,
            "auto_fetch_interval": settings.auto_fetch_interval,
            "dingtalk_webhook": settings.dingtalk_webhook or "",
            "dingtalk_secret": settings.dingtalk_secret or "",
            "dingtalk_client_id": settings.dingtalk_client_id or "",
            "dingtalk_stream_enabled": settings.dingtalk_stream_enabled,
            "wewe_server_url": settings.wewe_server_url or "",
            "wewe_auth_code": settings.wewe_auth_code or "",
        },
    }


# ──────────── Obsidian 保存 ────────────

@router.post("/articles/{article_id}/save-to-obsidian", summary="保存文章到 Obsidian")
async def save_to_obsidian(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await ObsidianService.save_article_to_vault(db, article_id, user.id)
        return {"code": 200, "message": "已保存到 Obsidian", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/obsidian/status", summary="检查 Obsidian 集成状态")
async def obsidian_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = await ObsidianService.get_settings(db, user.id)
    configured = ObsidianService.is_configured(settings)
    return {
        "code": 200,
        "data": {
            "configured": configured,
            "vault_path": settings.obsidian_vault_path if settings else "",
            "folder": settings.obsidian_folder if settings else "ReadHub",
        },
    }


# ──────────── 文章转任务 ────────────

class ConvertToTaskRequest(BaseModel):
    project_id: int
    title: Optional[str] = None  # 可选覆盖标题


@router.post("/articles/{article_id}/convert-to-task", summary="将文章转化为 TaskTree 任务")
async def convert_to_task(
    article_id: int,
    body: ConvertToTaskRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """将文章的标题和链接作为一个任务创建到指定项目中。"""
    from app.models import Task, Project
    from sqlalchemy import select

    # 验证文章存在
    article = await RssService.get_article_detail(db, article_id, user.id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 验证项目存在且用户有权限
    proj_result = await db.execute(select(Project).where(Project.id == body.project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 构建任务
    task_title = body.title or f"[阅读] {article.title}"
    task_desc = f"来源：{article.source_url}\n\n"
    if article.summary:
        task_desc += f"{article.summary[:500]}\n"

    from datetime import datetime, timezone
    task = Task(
        project_id=body.project_id,
        title=task_title,
        description=task_desc,
        status="todo",
        priority="medium",
        created_by=user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "code": 200,
        "message": f"已创建任务：{task_title}",
        "data": {"task_id": task.id, "title": task.title, "project_id": body.project_id},
    }


# ──────────── WeWe-RSS 集成 ────────────

class WeweRssSyncRequest(BaseModel):
    """wewe-rss 同步请求"""
    server_url: str  # wewe-rss 服务地址，如 http://localhost:4000
    auth_code: Optional[str] = None  # wewe-rss 授权码（如设置了 AUTH_CODE）


@router.post("/wewerss/sync", summary="从 wewe-rss 实例同步公众号订阅源")
async def sync_wewerss(
    body: WeweRssSyncRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    连接到用户部署的 wewe-rss 实例，获取所有已订阅的公众号 feed，
    自动注册为本地 RSS 订阅源。
    """
    import httpx
    from app.models.rss import RssFeed
    from sqlalchemy import select

    base_url = body.server_url.rstrip('/')

    # 通过 wewe-rss 的 /feeds/all.json 获取所有公众号源
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"{base_url}/feeds/all.json"
            params = {}
            if body.auth_code:
                params["auth_code"] = body.auth_code
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail=f"无法连接到 wewe-rss 服务: {base_url}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"wewe-rss 返回错误: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"请求 wewe-rss 失败: {str(e)}")

    feed_url = f"{base_url}/feeds/all.json"
    if body.auth_code:
        feed_url += f"?auth_code={body.auth_code}"

    # 检查是否已经存在
    existing = await db.execute(
        select(RssFeed).where(RssFeed.user_id == user.id, RssFeed.url == feed_url)
    )
    existing_feed = existing.scalar_one_or_none()

    added = []
    skipped = []

    if existing_feed:
        skipped.append("WeWe-RSS 聚合订阅")
    else:
        new_feed = RssFeed(
            user_id=user.id,
            url=feed_url,
            name="WeWe-RSS 聚合订阅",
            is_active=True,
        )
        db.add(new_feed)
        added.append("WeWe-RSS 聚合订阅")
        await db.commit()

    return {
        "code": 200,
        "message": f"同步完成：已将 WeWe-RSS 添加为聚合订阅源",
        "data": {
            "added": added,
            "skipped": skipped,
            "total_added": len(added),
            "total_skipped": len(skipped),
        },
    }


@router.get("/wewerss/status", summary="检查 wewe-rss 连接状态")
async def check_wewerss_status(
    server_url: str,
    auth_code: Optional[str] = None,
):
    """检测指定 wewe-rss 实例是否可达。"""
    import httpx

    base_url = server_url.rstrip('/')
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            url = f"{base_url}/feeds/all.json"
            params = {}
            if auth_code:
                params["auth_code"] = auth_code
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return {
                "code": 200,
                "data": {
                    "connected": True,
                    "feed_count": 1,
                    "server_url": base_url,
                },
            }
    except Exception as e:
        return {
            "code": 200,
            "data": {
                "connected": False,
                "error": str(e),
                "server_url": base_url,
            },
        }

