# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Nexus 是一个以大语言模型 (LLM) 为核心驱动引擎的集成化个人生态系统，涵盖两大核心模块：

- **TaskTree**：项目任务分解、进度管理、团队协作
- **ReadHub**：RSS/微信公众号订阅解析、AI 摘要、FTS5 全文检索知识库
- **钉钉 Stream**：双机器人独立运行的本地消息网关

## 技术栈

| 分层 | 技术 |
| :--- | :--- |
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 + Zustand |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + aiosqlite |
| AI Engine | Agent Engine (OpenAI/Claude/Kimi) |
| 部署 | Docker + Docker Compose |

## 常用命令

### 本地开发

```bash
# 前端
cd frontend && npm install
npm run dev      # 启动开发服务器
npm run build   # 生产构建
npm run lint    # 代码检查
npm run format # 代码格式化

# 后端
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload  # 启动后端服务
```

### Docker 部署

```bash
make build      # 构建镜像
make up        # 启动服务
make down      # 停止服务
make logs     # 查看日志
make health   # 健康检查
```

### 测试

```bash
make test           # 运行后端 pytest
make test-coverage # 生成覆盖率报告
```

## 架构设计

### 后端结构 (backend/app/)

- `api/v1/` — REST API 路由 (tasks, projects, users, auth, readhub, dingtalk...)
- `core/` — 核心基础设施 (config, database, security, agent engine)
- `models/` — SQLAlchemy ORM 模型
- `schemas/` — Pydantic 请求/响应模型
- `services/` — 业务逻辑服务
- `apps/` — 模块化应用 (tasktree/, readhub/)

**关键约定**：
- 全部使用 `AsyncSession`，通过 `Depends(get_db)` 注入
- 权限验证通过 `get_current_user` 和 `get_task_with_access()` 统一拦截
- Task 模型通过自引用 `parent_id` 实现无限层级树

### 前端结构 (frontend/src/)

- `api/` — Axios 封装与后端调用
- `components/` — 可复用 UI 组件
- `pages/` — 路由页面
- `stores/` — Zustand 状态管理
- `types/` — TypeScript 接口

**核心模式**：
- `ProjectDetail.tsx` 作为单一数据源
- 使用 `flattenAllTasks` / `collectDependencies` 进行形态转换
- 支持树形、看板、甘特图、依赖图四种视图

### AI Agent Engine

Agent Engine 位于 `backend/app/core/agent/engine.py`，负责意图理解和工具编排。

## 相关文档

详细架构设计见 `docs/` 目录。

## 环境变量

参考 `.env.example`。