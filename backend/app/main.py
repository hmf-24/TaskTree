from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, projects, tasks, users


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

@app.get("/")
def root():
    return {"message": "TaskTree API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}