"""
ReadHub — Obsidian 知识沉淀服务
================================
将 RSS 文章转换为 Markdown 并写入本地 Obsidian Vault。
"""
import os
import re
import logging
from pathlib import Path
from typing import Optional

from markdownify import markdownify as md
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rss import RssArticle, RssFeed, ReadHubSettings

logger = logging.getLogger(__name__)


class ObsidianService:
    """Obsidian Vault 文件写入服务。"""

    @staticmethod
    def _sanitize_filename(title: str) -> str:
        """将标题转化为安全的文件名。"""
        # 移除文件系统不允许的字符
        sanitized = re.sub(r'[\\/:*?"<>|]', '_', title)
        # 去除首尾空白和连续空格
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        # 限制长度
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized or "untitled"

    @staticmethod
    def _html_to_markdown(html: str) -> str:
        """将 HTML 正文转换为 Markdown。"""
        if not html:
            return ""
        try:
            return md(html, heading_style="ATX", strip=['script', 'style'])
        except Exception as e:
            logger.warning(f"[Obsidian] HTML→Markdown 转换失败: {e}")
            return html  # fallback：返回原始 HTML

    @staticmethod
    def _build_frontmatter(article: RssArticle) -> str:
        """拼接 YAML Frontmatter。"""
        lines = ["---"]
        lines.append(f'title: "{article.title}"')
        if article.source_url:
            lines.append(f"source: {article.source_url}")
        if article.author:
            lines.append(f"author: {article.author}")
        if article.published_at:
            lines.append(f"date: {article.published_at.strftime('%Y-%m-%d')}")
        lines.append("tags:")
        lines.append("  - ReadHub")
        lines.append(f"saved_at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("---")
        return "\n".join(lines)

    # ──────────── 核心方法 ────────────

    @staticmethod
    async def get_settings(db: AsyncSession, user_id: int) -> Optional[ReadHubSettings]:
        """获取用户的 ReadHub 设置。"""
        result = await db.execute(
            select(ReadHubSettings).where(ReadHubSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_settings(
        db: AsyncSession, user_id: int, **kwargs
    ) -> ReadHubSettings:
        """创建或更新用户的 ReadHub 设置。"""
        result = await db.execute(
            select(ReadHubSettings).where(ReadHubSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = ReadHubSettings(user_id=user_id)
            db.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        await db.commit()
        await db.refresh(settings)
        return settings

    @staticmethod
    def is_configured(settings: Optional[ReadHubSettings]) -> bool:
        """检查 Obsidian 集成是否已配置且路径有效。"""
        if not settings or not settings.obsidian_vault_path:
            return False
        return os.path.isdir(settings.obsidian_vault_path)

    @staticmethod
    async def save_article_to_vault(
        db: AsyncSession, article_id: int, user_id: int
    ) -> dict:
        """
        将文章保存为 Markdown 到 Obsidian Vault。

        Returns:
            {"success": True, "file_path": "相对路径"} 或抛出异常
        """
        # 1. 获取用户设置
        settings = await ObsidianService.get_settings(db, user_id)
        if not ObsidianService.is_configured(settings):
            raise ValueError("Obsidian Vault 路径未配置或目录不存在，请在 ReadHub 设置中配置。")

        # 2. 获取文章
        result = await db.execute(
            select(RssArticle)
            .join(RssFeed, RssArticle.feed_id == RssFeed.id)
            .where(RssArticle.id == article_id, RssFeed.user_id == user_id)
        )
        article = result.scalar_one_or_none()
        if not article:
            raise ValueError(f"文章 #{article_id} 不存在")

        # 3. 构建 Markdown 内容
        frontmatter = ObsidianService._build_frontmatter(article)
        body_md = ObsidianService._html_to_markdown(article.content_html or "")
        full_content = f"{frontmatter}\n\n{body_md}\n"

        # 4. 确保保存目录存在
        folder_name = settings.obsidian_folder or "ReadHub"
        save_dir = Path(settings.obsidian_vault_path) / folder_name
        save_dir.mkdir(parents=True, exist_ok=True)

        # 5. 写入文件
        safe_title = ObsidianService._sanitize_filename(article.title)
        file_path = save_dir / f"{safe_title}.md"

        # 如果文件已存在，追加序号
        if file_path.exists():
            counter = 1
            while file_path.exists():
                file_path = save_dir / f"{safe_title}_{counter}.md"
                counter += 1

        file_path.write_text(full_content, encoding="utf-8")

        # 6. 更新数据库
        article.is_saved_to_obsidian = True
        await db.commit()

        relative_path = f"{folder_name}/{file_path.name}"
        logger.info(f"[Obsidian] 文章 #{article_id} 已保存到: {relative_path}")
        return {"success": True, "file_path": relative_path}
