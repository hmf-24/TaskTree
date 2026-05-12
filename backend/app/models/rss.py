"""
ReadHub 数据库模型
=================
RSS 订阅源和文章的数据模型，与 TaskTree 的表完全隔离。
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models import Base


class RssFeed(Base):
    """RSS 订阅源 — 记录用户订阅的 WeweRSS feed 地址。"""
    __tablename__ = 'rss_feeds'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True, comment="所属用户 ID")
    url = Column(Text, nullable=False, comment="Feed 地址 (WeweRSS 生成的 Atom/RSS URL)")
    name = Column(String(255), nullable=False, comment="订阅源显示名称")
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_fetched_at = Column(DateTime, comment="最近一次拉取时间")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    user = relationship('User')
    articles = relationship('RssArticle', back_populates='feed', cascade='all, delete-orphan')


class RssArticle(Base):
    """RSS 文章 — 存储从 feed 拉取到的每一篇文章。"""
    __tablename__ = 'rss_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    feed_id = Column(Integer, ForeignKey('rss_feeds.id', ondelete='CASCADE'), nullable=False, index=True, comment="所属订阅源 ID")
    title = Column(String(500), nullable=False, comment="文章标题")
    content_html = Column(Text, comment="文章原始 HTML 正文")
    summary = Column(Text, comment="文章摘要 (feed 自带或 AI 生成)")
    source_url = Column(Text, nullable=False, comment="文章原文链接 (用于去重)")
    author = Column(String(255), comment="作者")
    published_at = Column(DateTime, comment="发布时间")
    is_read = Column(Boolean, default=False, index=True, comment="是否已读")
    is_saved_to_obsidian = Column(Boolean, default=False, comment="是否已保存到 Obsidian")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # 关联关系
    feed = relationship('RssFeed', back_populates='articles')


class ReadHubSettings(Base):
    """ReadHub 用户设置 — 存储 Obsidian Vault 路径等 ReadHub 专属配置。"""
    __tablename__ = 'readhub_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True, comment="所属用户 ID")
    obsidian_vault_path = Column(Text, default="", comment="Obsidian Vault 本地绝对路径")
    obsidian_folder = Column(String(255), default="ReadHub", comment="Vault 内保存子目录名")
    auto_fetch_enabled = Column(Boolean, default=False, comment="是否启用自动定时拉取")
    auto_fetch_interval = Column(Integer, default=60, comment="自动拉取间隔（分钟）")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    user = relationship('User')
