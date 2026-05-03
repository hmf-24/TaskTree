---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree 本地测试与生产环境部署指南，推荐Docker Compose部署"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
---

# TaskTree 部署指南

> [!tip] 推荐方案
> 对于测试与生产环境，**强烈推荐使用 Docker Compose** 进行一键化容器编排部署。

---

## ⚡ 快速测试部署 (Docker 推荐)

如果你刚刚完成了代码拉取，准备在本地机器或测试服务器上运行整个系统，请按照以下 3 步执行：

### 1. 环境准备

> [!info] 环境要求
> - **Docker** (20.10+): 容器引擎
> - **Docker Compose** (2.0+): 容器编排工具

### 2. 配置文件
进入项目根目录，复制环境变量模板：
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```
*(在本地测试阶段，你可以直接使用 `.env` 中的默认值，无需修改即可跑通全流程)*

### 3. 一键启动
在项目根目录（包含 `docker-compose.yml` 的目录）执行：
```bash
docker-compose up -d --build
```
> [!note]
> 此命令将自动构建前端 (Vite/Nginx) 和后端 (FastAPI) 的镜像并启动。首次构建由于需要安装 npm 依赖和 python 依赖，可能需要几分钟时间。

### 4. 访问系统
当容器启动完毕后，在浏览器中访问：
- **💻 前端界面**: [http://localhost](http://localhost) (由 Nginx 映射到 80 端口)
- **🔌 后端 API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **🩺 后端健康检查**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🛠️ Docker 运维常用命令

> [!tip] 常用命令
> 在测试或运行期间，你可能会用到以下命令：

```bash
# 查看所有服务的运行状态与健康检查(Healthcheck)情况
docker-compose ps

# 实时查看前后端的运行日志（Ctrl+C 退出）
docker-compose logs -f

# 仅查看后端报错日志
docker-compose logs -f backend

# 停止服务（不删除数据）
docker-compose down

# 彻底清理：停止服务，并删除 SQLite 数据库数据卷（⚠️警告：数据将清空！）
docker-compose down -v
```

---

## ⚙️ 环境变量说明

如果要在生产环境中正式部署，请务必修改 `.env` 文件中的配置：

| 变量名 | 说明 | 默认值 | 生产环境要求 |
|--------|------|--------|------|
| `SECRET_KEY` | JWT 用户登录 Token 的签名密钥 | `your-secret-key...` | **必填**。请使用强随机字符串（如 `openssl rand -hex 32`） |
| `ENCRYPTION_KEY` | 智能提醒大模型 API Key 的底层加密盐值 | `tasktree-default...` | **选填**。修改后系统会更安全，但会导致旧的 API Key 无法解密 |
| `DEBUG` | FastAPI 调试模式 | `false` | 保持 `false` |
| `DATABASE_URL` | SQLite 数据库挂载路径 | `sqlite+aiosqlite:///app/data/tasktree.db` | 无需修改，由 Volume 管理 |

---

## 🗄️ 数据持久化与备份

TaskTree 使用 SQLite 作为底层数据库。在 Docker 架构下，数据库文件存储在虚拟数据卷 `tasktree_backend-data` 中。

**数据库实际路径**: `backend/data/tasktree.db`

### 如何备份数据？
你可以在容器运行期间，直接将数据库文件拷贝到宿主机：
```bash
docker cp tasktree-backend:/app/data/tasktree.db ./tasktree_backup.db
```

### 如何恢复数据？
1. 停止当前服务：`docker-compose down`
2. 将备份文件覆盖进去：`docker cp ./tasktree_backup.db tasktree-backend:/app/data/tasktree.db`
3. 重启服务：`docker-compose up -d`

---

## 🚑 常见问题排查 (FAQ)

> [!warning] Q1: backend 容器处于 `unhealthy` 状态或无限重启？
> - **排查**: 请执行 `docker-compose logs backend` 检查日志。常见原因是依赖安装失败、端口冲突，或旧版本代码健康检查路由未更新。TaskTree 的标准健康检查路由为无需认证的 `/health`。

> [!warning] Q2: 前端页面一直显示 Loading 或无法请求到数据？
> - **排查**: 打开浏览器的开发者工具 (F12) 检查 Console 与 Network 面板。Nginx 默认会将以 `/api` 开头的请求反向代理到后端容器（`backend:8000`）。请确保 backend 容器已成功启动。

> [!warning] Q3: 端口 80 或 8000 被占用怎么办？
> - **解决**: 修改 `docker-compose.yml` 中的 `ports` 映射。例如将前端端口改为 `8080`：
  ```yaml
  ports:
    - "8080:80"
  ```
  修改后重新执行 `docker-compose up -d` 即可。

---

## 👩‍💻 本地开发模式 (供二次开发参考)

如果你不使用 Docker，希望在本地机器直接裸机运行代码：

### 后端 (Terminal 1)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python -c "from app.core.database import init_db; init_db()"
uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

### 前端 (Terminal 2)
```bash
cd frontend
npm install
npm run dev
# 将会在 http://localhost:5173 启动热更新服务
```