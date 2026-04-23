"""
TaskTree 后端应用入口
====================
基于 FastAPI 的 RESTful API 服务。
启动命令: uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, projects, tasks, users, export, notifications, notification_settings, llm_tasks, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    yield


app = FastAPI(
    title="TaskTree API",
    description="TaskTree 任务树后端API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/tasktree/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/tasktree/users", tags=["用户"])
app.include_router(projects.router, prefix="/api/v1/tasktree/projects", tags=["项目"])
app.include_router(tasks.router, prefix="/api/v1/tasktree", tags=["任务"])
app.include_router(export.router, prefix="/api/v1/tasktree/projects", tags=["导入导出"])
app.include_router(notifications.router, prefix="/api/v1/tasktree/notifications", tags=["通知"])
app.include_router(notification_settings.router, prefix="/api/v1/tasktree", tags=["智能提醒"])
app.include_router(llm_tasks.router, prefix="/api/v1/tasktree", tags=["AI智能任务"])
app.include_router(conversations.router, prefix="/api/v1/tasktree", tags=["AI对话"])

@app.get("/")
def root():
    return {"message": "TaskTree API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}