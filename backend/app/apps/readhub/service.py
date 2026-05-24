"""
ReadHub — RSS 服务层
====================
封装订阅源管理和文章拉取逻辑，对接 WeweRSS 的 feed 地址。
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import feedparser
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rss import RssFeed, RssArticle, ReadHubSettings
from app.models import UserNotificationSettings

logger = logging.getLogger(__name__)


class RssService:
    """RSS 订阅与文章管理服务。"""

    # ────────────────── 订阅源 CRUD ──────────────────

    @staticmethod
    async def add_feed(db: AsyncSession, user_id: int, url: str, name: str) -> RssFeed:
        """添加一个新的订阅源。"""
        feed = RssFeed(user_id=user_id, url=url, name=name)
        db.add(feed)
        await db.commit()
        await db.refresh(feed)
        logger.info(f"[ReadHub] 用户 {user_id} 添加订阅源: {name} ({url})")
        return feed

    @staticmethod
    async def list_feeds(db: AsyncSession, user_id: int) -> list[RssFeed]:
        """获取用户的所有订阅源。"""
        result = await db.execute(
            select(RssFeed)
            .where(RssFeed.user_id == user_id)
            .order_by(RssFeed.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_feed(db: AsyncSession, feed_id: int, user_id: int) -> bool:
        """删除一个订阅源（级联删除其文章）。"""
        result = await db.execute(
            select(RssFeed).where(RssFeed.id == feed_id, RssFeed.user_id == user_id)
        )
        feed = result.scalar_one_or_none()
        if not feed:
            return False
        await db.delete(feed)
        await db.commit()
        logger.info(f"[ReadHub] 已删除订阅源 #{feed_id}: {feed.name}")
        return True

    # ────────────────── 文章拉取 ──────────────────

    @staticmethod
    async def fetch_feeds(db: AsyncSession, user_id: int) -> dict:
        """遍历用户的所有活跃订阅源，增量拉取新文章，并推送到钉钉。

        Returns:
            {"total_new": int, "feeds_updated": int, "errors": list[str]}
        """
        feeds = await RssService.list_feeds(db, user_id)
        active_feeds = [f for f in feeds if f.is_active]

        total_new_articles = []
        feeds_updated = 0
        errors: list[str] = []

        for feed in active_feeds:
            try:
                new_articles = await RssService._fetch_single_feed(db, feed)
                if new_articles:
                    total_new_articles.extend(new_articles)
                    feeds_updated += 1
            except Exception as e:
                error_msg = f"拉取 '{feed.name}' 失败: {e}"
                logger.warning(f"[ReadHub] {error_msg}")
                errors.append(error_msg)

        await db.commit()
        
        total_new = len(total_new_articles)
        
        # 获取用户的全局通知设置（为了拿 dingtalk_user_id）和 ReadHubSettings
        user_notif_result = await db.execute(
            select(UserNotificationSettings).where(UserNotificationSettings.user_id == user_id)
        )
        user_notif = user_notif_result.scalar_one_or_none()
        
        readhub_settings_result = await db.execute(
            select(ReadHubSettings).where(ReadHubSettings.user_id == user_id)
        )
        rh_settings = readhub_settings_result.scalar_one_or_none()
        
        interest_tags = []
        if rh_settings and rh_settings.interest_tags:
            import json
            try:
                interest_tags = json.loads(rh_settings.interest_tags)
            except:
                pass
        
        # (Removed) 批量生成摘要和分级，已改为按需计算 (On-Demand Compute)
        
        
        # 如果有新文章，尝试推送到钉钉
        if total_new > 0:
            try:
                from app.core.security import decrypt_token
                
                if user_notif and user_notif.dingtalk_user_id:
                    kwargs = {}
                    if rh_settings and rh_settings.dingtalk_stream_enabled and rh_settings.dingtalk_client_id:
                        kwargs["use_stream_mode"] = True
                        kwargs["client_id"] = rh_settings.dingtalk_client_id
                        if rh_settings.dingtalk_client_secret_encrypted:
                            kwargs["client_secret"] = decrypt_token(rh_settings.dingtalk_client_secret_encrypted)
                    elif rh_settings and rh_settings.dingtalk_webhook:
                        kwargs["webhook_url"] = rh_settings.dingtalk_webhook
                        kwargs["secret"] = rh_settings.dingtalk_secret
                        kwargs["use_stream_mode"] = False
                    
                    # 获取 feed 详情以便在推送中显示
                    for article in total_new_articles:
                        article.feed = next((f for f in active_feeds if f.id == article.feed_id), None)
                        
                    await dingtalk_service.send_rss_articles(
                        articles=total_new_articles,
                        dingtalk_user_id=user_notif.dingtalk_user_id,
                        **kwargs
                    )
            except Exception as e:
                logger.error(f"[ReadHub] 推送新文章到钉钉失败: {e}")

        return {"total_new": total_new, "feeds_updated": feeds_updated, "errors": errors}

    @staticmethod
    async def _fetch_single_feed(db: AsyncSession, feed: RssFeed) -> list[RssArticle]:
        """拉取单个 feed 的新文章，通过 source_url 去重。返回新增的文章列表。"""
        import httpx
        
        # 获取该 feed 已有的所有文章 URL（用于去重）
        existing_urls_result = await db.execute(
            select(RssArticle.source_url).where(RssArticle.feed_id == feed.id)
        )
        existing_urls = set(existing_urls_result.scalars().all())
        
        new_articles = []
        is_json_feed = ".json" in feed.url
        
        if is_json_feed:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(feed.url)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    if not items and isinstance(data, list):
                        items = data
                    
                    for item in items:
                        link = item.get("url", "") or item.get("id", "")
                        if not link or link in existing_urls:
                            continue
                        
                        published_at = None
                        date_str = item.get("date_published") or item.get("date_modified")
                        if date_str:
                            try:
                                published_at = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except Exception:
                                pass
                                
                        author_name = "未知作者"
                        if isinstance(item.get("author"), dict):
                            author_name = item["author"].get("name", author_name)
                        elif isinstance(item.get("author"), str):
                            author_name = item["author"]
                        
                        article = RssArticle(
                            feed_id=feed.id,
                            title=item.get("title", "无标题"),
                            content_html=item.get("content_html", "") or item.get("summary", ""),
                            summary=None,
                            source_url=link,
                            author=author_name,
                            published_at=published_at,
                        )
                        db.add(article)
                        new_articles.append(article)
                else:
                    raise ValueError(f"JSON Feed 返回状态码 {resp.status_code}")
        else:
            import asyncio
            import functools
            loop = asyncio.get_event_loop()
            # feedparser.parse is synchronous and performs network I/O, so run it in a thread pool
            parsed = await loop.run_in_executor(None, functools.partial(feedparser.parse, feed.url))

            if parsed.bozo and not parsed.entries:
                raise ValueError(f"Feed 解析错误: {parsed.bozo_exception}")

            for entry in parsed.entries:
                link = entry.get("link", "")
                if not link or link in existing_urls:
                    continue

                # 解析发布时间
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass

                article = RssArticle(
                    feed_id=feed.id,
                    title=entry.get("title", "无标题"),
                    content_html=entry.get("content", [{}])[0].get("value", "") if entry.get("content") else entry.get("summary", ""),
                    summary=entry.get("summary", "")[:500] if entry.get("summary") else None,
                    source_url=link,
                    author=entry.get("author", None),
                    published_at=published_at,
                )
                db.add(article)
                new_articles.append(article)

        # 更新 feed 的最后拉取时间
        feed.last_fetched_at = datetime.now(timezone.utc)
        logger.info(f"[ReadHub] '{feed.name}' 拉取到 {len(new_articles)} 篇新文章")
        return new_articles

    # ────────────────── 文章查询 ──────────────────

    @staticmethod
    async def get_articles(
        db: AsyncSession,
        user_id: int,
        feed_id: Optional[int] = None,
        unread_only: bool = False,
        author: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取文章列表（支持分页、按订阅源筛选、按作者筛选、仅未读）。"""
        # 基础查询：只返回当前用户订阅源下的文章
        query = (
            select(RssArticle)
            .join(RssFeed, RssArticle.feed_id == RssFeed.id)
            .where(RssFeed.user_id == user_id)
        )
        count_query = (
            select(func.count(RssArticle.id))
            .join(RssFeed, RssArticle.feed_id == RssFeed.id)
            .where(RssFeed.user_id == user_id)
        )

        if feed_id:
            query = query.where(RssArticle.feed_id == feed_id)
            count_query = count_query.where(RssArticle.feed_id == feed_id)

        if author:
            query = query.where(RssArticle.author == author)
            count_query = count_query.where(RssArticle.author == author)

        if unread_only:
            query = query.where(RssArticle.is_read == False)  # noqa: E712
            count_query = count_query.where(RssArticle.is_read == False)  # noqa: E712

        # 总数
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(RssArticle.published_at.desc().nullslast(), RssArticle.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        articles = list(result.scalars().all())

        return {
            "items": articles,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def get_feed_authors(db: AsyncSession, user_id: int, feed_id: int) -> list[str]:
        """获取指定订阅源下所有文章的去重作者列表。"""
        # 需要确保 feed 属于该用户
        result = await db.execute(
            select(RssFeed.id).where(RssFeed.id == feed_id, RssFeed.user_id == user_id)
        )
        if not result.scalar_one_or_none():
            return []

        # 查询去重的 author
        query = (
            select(RssArticle.author)
            .where(RssArticle.feed_id == feed_id)
            .where(RssArticle.author.isnot(None))
            .distinct()
        )
        authors_result = await db.execute(query)
        authors = [a for a in authors_result.scalars().all() if a]
        return sorted(authors)

    @staticmethod
    async def mark_read(db: AsyncSession, article_id: int, user_id: int) -> bool:
        """标记文章为已读。"""
        result = await db.execute(
            select(RssArticle)
            .join(RssFeed, RssArticle.feed_id == RssFeed.id)
            .where(RssArticle.id == article_id, RssFeed.user_id == user_id)
        )
        article = result.scalar_one_or_none()
        if not article:
            return False
        article.is_read = True
        await db.commit()
        return True

    @staticmethod
    async def get_article_detail(db: AsyncSession, article_id: int, user_id: int) -> Optional[RssArticle]:
        """获取单篇文章详情。"""
        result = await db.execute(
            select(RssArticle)
            .join(RssFeed, RssArticle.feed_id == RssFeed.id)
            .where(RssArticle.id == article_id, RssFeed.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def generate_ai_summary(db: AsyncSession, article_id: int, user_id: int) -> Optional[RssArticle]:
        """为单篇文章生成 AI 概览并保存"""
        import re
        from app.services.llm_service import LLMService
        from app.models.readhub import ReadHubSettings

        article = await RssService.get_article_detail(db, article_id, user_id)
        if not article:
            return None

        # 如果已经生成过，可以直接返回，但这里设计为允许重复生成覆盖
        raw = article.content_html or article.summary or ""
        clean = re.sub(r'<[^>]+>', '', raw).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if len(clean) > 1500:
            clean = clean[:1500]

        prompt = (
            f"请为以下文章生成一句话（30-60字）的中文摘要，概括其核心要点。\n"
            f"要求：有信息量，不要只重复标题，提炼关键信息。\n\n"
            f"标题：{article.title}\n"
            f"内容：{clean}"
        )

        try:
            # 读取用户的 LLM 配置，或者使用全局配置
            llm_service = LLMService() # Default global instance for now, if user settings exist, we can inject them later
            
            response = await llm_service.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的新闻编辑助手，擅长概括核心内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            summary = response.strip()
            # 移除可能的多余前缀
            summary = re.sub(r'^(摘要|概括|总结)[:：\s]*', '', summary)
            
            article.summary = f"[AI 概览] {summary}"
            await db.commit()
            return article
        except Exception as e:
            logger.error(f"[ReadHub] 生成 AI 摘要失败: {e}")
            raise ValueError(f"生成概览失败: {e}")
