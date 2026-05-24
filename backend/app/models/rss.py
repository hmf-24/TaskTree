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
    
    # ---- 智能分级与标签 ----
    importance = Column(String(50), default="medium", comment="重要度 (high/medium/low/unrelated)")
    tags = Column(Text, nullable=True, comment="文章命中的关注标签 (JSON数组)")
    
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
    
    # ---- 独立钉钉机器人配置 (ReadHub 专属) ----
    dingtalk_webhook = Column(String(500), nullable=True)  # 钉钉 Webhook 地址 (可选)
    dingtalk_secret = Column(String(100), nullable=True)   # 钉钉 Webhook 加签密钥 (可选)
    dingtalk_client_id = Column(String(100), nullable=True) # 钉钉 AppKey (Stream模式)
    dingtalk_client_secret_encrypted = Column(Text, nullable=True) # 钉钉 AppSecret (加密)
    dingtalk_stream_enabled = Column(Boolean, default=False) # 是否启用 Stream 模式

    # ---- WeWe-RSS 配置 ----
    wewe_server_url = Column(String(500), nullable=True, comment="WeWe-RSS 服务地址")
    wewe_auth_code = Column(String(100), nullable=True, comment="WeWe-RSS 授权码")
    
    # ---- 智能分级过滤配置 ----
    interest_tags = Column(Text, nullable=True, default='["AI", "前沿技术", "数据中心", "算力", "GPU"]', comment="用户关注的领域标签 (JSON数组)")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关联关系
    user = relationship('User')
