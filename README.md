# TaskTree 任务树

直观高效的任务分解与项目管理工具

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design 5
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + SQLite
- **部署**: Docker + Docker Compose

## 功能特性

- 多层级任务树管理（无限嵌套）
- 多种视图：树形、看板、甘特图、依赖图
- 项目成员协作与权限管理
- 任务评论与标签系统
- 多格式导入导出（JSON、Markdown、Excel）
- 站内通知系统

## 快速开始

### 本地开发

#### 前端

```bash
cd frontend
npm install
npm run dev
```

#### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Docker 部署

```bash
# 克隆项目后
cp .env.example .env

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务启动后访问：
- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
TaskTree/
├── docs/           # 项目文档
├── frontend/       # 前端应用 (React + Vite)
├── backend/        # 后端服务 (FastAPI)
├── docker-compose.yml  # Docker 编排配置
└── .env.example    # 环境变量模板
```

## 开发命令

```bash
# 前端
npm run dev      # 开发服务器
npm run build    # 生产构建
npm run lint     # 代码检查
npm run format   # 代码格式化

# 后端
pytest           # 运行单元测试
```

## 许可证

MIT