"""
TaskTree 应用配置
================
基于 pydantic-settings 的统一配置管理。
支持通过环境变量或 .env 文件覆盖默认值。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """应用全局配置，所有配置项均可通过同名环境变量覆盖。"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # ---- 应用配置 ----
    APP_NAME: str = "TaskTree"
    DEBUG: bool = True

    # ---- 数据库 ----
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tasktree.db"

    # ---- JWT 认证 ----
    SECRET_KEY: str = "your-secret-key-change-in-production"  # 生产环境务必通过环境变量覆盖
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 天 = 7 * 24 * 60

    # ---- CORS 跨域 ----
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ---- 文件上传 ----
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ---- 智能提醒 (Minimax) ----
    MINMAX_API_KEY: str = ""
    MINMAX_GROUP_ID: str = ""

    # ---- 智能提醒调度 ----
    REMINDER_INTERVAL_MINUTES: int = 30  # 定时检查间隔


settings = Settings()