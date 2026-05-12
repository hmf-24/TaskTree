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

from app.models.rss import RssFeed, RssArticle

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
        """遍历用户的所有活跃订阅源，增量拉取新文章。

        Returns:
            {"total_new": int, "feeds_updated": int, "errors": list[str]}
        """
        feeds = await RssService.list_feeds(db, user_id)
        active_feeds = [f for f in feeds if f.is_active]

        total_new = 0
        feeds_updated = 0
        errors: list[str] = []

        for feed in active_feeds:
            try:
                new_count = await RssService._fetch_single_feed(db, feed)
                total_new += new_count
                if new_count > 0:
                    feeds_updated += 1
            except Exception as e:
                error_msg = f"拉取 '{feed.name}' 失败: {e}"
                logger.warning(f"[ReadHub] {error_msg}")
                errors.append(error_msg)

        await db.commit()
        return {"total_new": total_new, "feeds_updated": feeds_updated, "errors": errors}

    @staticmethod
    async def _fetch_single_feed(db: AsyncSession, feed: RssFeed) -> int:
        """拉取单个 feed 的新文章，通过 source_url 去重。"""
        parsed = feedparser.parse(feed.url)

        if parsed.bozo and not parsed.entries:
            raise ValueError(f"Feed 解析错误: {parsed.bozo_exception}")

        # 获取该 feed 已有的所有文章 URL（用于去重）
        existing_urls_result = await db.execute(
            select(RssArticle.source_url).where(RssArticle.feed_id == feed.id)
        )
        existing_urls = set(existing_urls_result.scalars().all())

        new_count = 0
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
            new_count += 1

        # 更新 feed 的最后拉取时间
        feed.last_fetched_at = datetime.now(timezone.utc)
        logger.info(f"[ReadHub] '{feed.name}' 拉取到 {new_count} 篇新文章")
        return new_count

    # ────────────────── 文章查询 ──────────────────

    @staticmethod
    async def get_articles(
        db: AsyncSession,
        user_id: int,
        feed_id: Optional[int] = None,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取文章列表（支持分页、按订阅源筛选、仅未读）。"""
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
