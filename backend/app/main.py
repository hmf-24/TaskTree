"""
TaskTree 后端应用入口
====================
基于 FastAPI 的 RESTful API 服务。
启动命令: uvicorn app.main:app --reload --port 8000
"""
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
from pathlib import Path
from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    file_system_exception_handler,
    generic_exception_handler
)
from app.api.v1 import auth, projects, tasks, users, export, notifications, notification_settings, llm_tasks, conversations, attachments, dingtalk
from app.apps.readhub.router import router as readhub_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await init_db()
    
    # 启动定时任务调度器
    from app.services.scheduler_service import SchedulerService
    SchedulerService.start()
    # 异步加载所有用户的后台拉取任务
    import asyncio
    asyncio.create_task(SchedulerService.reload_all_jobs())
    
    # 启动钉钉Stream客户端
    try:
        from app.services.dingtalk_stream_client import start_dingtalk_stream_mode
        await start_dingtalk_stream_mode(app)
    except Exception as e:
        try:
            print(f"[WARNING] 钉钉Stream客户端启动失败: {e}")
        except Exception:
            pass
    
    yield
    
    # 停止调度器
    SchedulerService.stop()
    
    # 关闭时停止所有Stream客户端
    if hasattr(app.state, 'dingtalk_stream_clients'):
        try:
            for user_id, clients in app.state.dingtalk_stream_clients.items():
                if isinstance(clients, dict):
                    for app_source, client in clients.items():
                        await client.stop()
                        try:
                            print(f"[SUCCESS] 用户 {user_id} 的 [{app_source}] Stream客户端已停止")
                        except Exception:
                            pass
                else:
                    await clients.stop()
                    try:
                        print(f"[SUCCESS] 用户 {user_id} 的Stream客户端已停止")
                    except Exception:
                        pass
        except Exception as e:
            try:
                print(f"[WARNING] 停止Stream客户端失败: {e}")
            except Exception:
                pass


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

# 注册异常处理器
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(OSError, file_system_exception_handler)
app.add_exception_handler(IOError, file_system_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

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
app.include_router(attachments.router, prefix="/api/v1/tasktree", tags=["附件"])
app.include_router(dingtalk.router, tags=["钉钉智能助手"])

# ---- ReadHub 应用路由 ----
app.include_router(readhub_router, prefix="/api/v1/readhub", tags=["ReadHub"])

# 挂载静态文件目录（用于访问上传的文件）
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "TaskTree API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}