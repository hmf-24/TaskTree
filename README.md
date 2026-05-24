# Nexus 多模块智能生态系统

Nexus 是一个以大语言模型 (LLM) 为核心驱动引擎的集成化个人生态系统，目前主要涵盖两大核心智能体模块：
- **TaskTree (任务管理)**：直观高效的项目任务分解、进度管理与团队协作中枢。
- **ReadHub (知识聚合)**：智能 RSS/微信公众号订阅解析、AI 自动摘要与 FTS5 历史知识库全文检索。

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design 5 + Zustand
- **后端**: Python 3.11 + FastAPI + SQLAlchemy + SQLite (含 FTS5 插件)
- **AI 智能引擎**: 独立的 Agent Engine，支持 OpenAI / Claude / Kimi (Moonshot) 等提供商，实现钉钉流 (Stream) 的自然语言意图理解、工具调用 (Tool Use) 隔离。
- **部署**: Docker + Docker Compose

## 核心特性

### 🎯 TaskTree 任务助手
- 多层级任务树管理（无限嵌套）与依赖关系自动检查。
- 多种视图支持：树形、看板、甘特图、依赖流向图。
- AI 智能拆解：通过自然语言直接下发指令，AI 自动拆解项目并创建任务。

### 📡 ReadHub 订阅助手
- 基于 WeweRSS 的无缝微信公众号/RSS 挂载。
- 后台任务自动抓取、清洗正文并交由大模型生成核心摘要。
- 基于 FTS5 虚拟表的“记忆检索”，用自然语言即可快速翻找历史长文。

### 🤖 钉钉 Stream 端
- 纯本地环境免公网 IP 回调映射。
- 双机器人独立运行（`app_source` 物理隔离流量，互不干扰）。

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
# 克隆项目后，拷贝环境变量
cp .env.example .env

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

服务启动后访问：
- 前端应用：http://localhost
- 后端 API：http://localhost:8000
- 交互式接口文档：http://localhost:8000/docs

## 项目结构

```
Nexus/
├── docs/           # 项目与技术架构文档
├── frontend/       # 前端应用 (React + Vite)
├── backend/        # 后端 API 与 Agent Engine 服务 (FastAPI)
├── docker-compose.yml  # Docker 编排配置
└── .env.example    # 全局环境变量模板
```

## 开发文档
请查阅 [`docs/`](docs/) 目录获取更详细的需求架构设计、数据库定义与 API 说明。

## 许可证

MIT