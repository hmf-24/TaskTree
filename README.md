# TaskTree 任务树

直观高效的任务分解与项目管理工具

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Tauri 2.x + Ant Design 5
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + SQLite
- **部署**: Docker + Docker Compose

## 快速开始

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 后端（Docker）

```bash
cd backend
docker build -t tasktree-backend .
docker run -p 8000:8000 tasktree-backend
```

### 完整启动（Docker Compose）

```bash
docker-compose up -d
```

## 项目结构

```
TaskTree/
├── docs/           # 项目文档
├── frontend/        # 前端应用
├── backend/        # 后端服务
└── deploy/         # 部署配置
```

## 开发计划

详见 [docs/02-项目计划.md](./docs/02-项目计划.md)