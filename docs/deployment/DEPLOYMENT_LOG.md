---
source: 工作文档
author: HMF
created: 2026-04-24
description: "TaskTree Docker部署记录，记录每次部署变更"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
  - Tech/Docker
  - Type/Log
---

# Docker部署记录

> [!info] 最新部署
> 本次部署时间: 2026-05-06
> 更新内容: 修复单用户模式下前后端任务列表显示不一致的问题（移除了 assignee_id 过滤机制），实现全局全量任务读取。

## 部署时间

| 阶段 | 时间 |
|------|------|
| 开始 | 2026-05-06 14:50:00 |
| 完成 | 2026-05-06 15:00:00 |
| 总耗时 | 约 10 分钟 |

## 部署结果

> [!success] ✅ 后端服务 (tasktree-backend)
> - **镜像**: tasktree-backend:latest
> - **状态**: 运行中 (healthy)
> - **端口**: 8000
> - **应用服务器**: Gunicorn + Uvicorn (4 workers)

> [!success] ✅ 前端服务 (tasktree-frontend)
> - **镜像**: tasktree-frontend:latest
> - **状态**: 运行中 (healthy)
> - **端口**: 80, 443
> - **Web 服务器**: Nginx (5 worker processes)

### 访问地址

| 服务 | 地址 | 状态 |
|------|------|------|
| 前端应用 | http://localhost | ✅ 正常 |
| 后端 API | http://localhost:8000 | ✅ 正常 |
| 健康检查 | http://localhost:8000/health | ✅ 正常 |

### 容器信息

```
NAME                IMAGE                      STATUS
tasktree-backend    tasktree-backend:latest    Up 20 seconds (healthy)
tasktree-frontend   tasktree-frontend:latest   Up 14 seconds (health: starting)
```

### 数据卷

| 卷名 | 用途 | 挂载点 |
|------|------|--------|
| tasktree-data | 数据库和应用数据 | /app/data |
| tasktree-uploads | 文件上传 | /app/uploads |
| tasktree-logs | 应用日志 | /app/logs |

### 网络

- **网络名称**: tasktree-network
- **网络类型**: bridge
- **容器间通信**: ✅ 正常

## 功能验证

### ✅ 后端 API
- 健康检查: `GET /health` → 200 OK
- 项目查询: `GET /api/v1/tasktree/projects` → 200 OK
- 任务树: `GET /api/v1/tasktree/projects/3/tasks/tree` → 200 OK
- 通知: `GET /api/v1/tasktree/notifications` → 200 OK

### ✅ 前端应用
- 首页加载: `GET /` → 200 OK
- 项目页面: `GET /project/3` → 200 OK
- 资源加载: `GET /assets/index-*.js` → 200 OK
- API 代理: 所有请求正确转发到后端

## 快速命令

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 改进项

### Docker 配置优化
- ✅ 后端使用 Gunicorn + Uvicorn 提高性能
- ✅ 前端使用多阶段构建优化镜像大小
- ✅ 添加健康检查确保服务可用性
- ✅ 配置日志管理 (JSON 格式, 10MB 限制)
- ✅ 添加网络隔离
- ✅ 创建 .dockerignore 优化构建

### AI 交互意图理解及稳定性优化 (2026-05-04)
- ✅ **消息防重放**: 钉钉 Stream 客户端增加基于 `createAt` 的 30 秒过期时间戳拦截，解决后端重启引发的旧消息风暴重试问题。
- ✅ **JSON 响应鲁棒化**: 为 LLM 返回的 JSON 增加多层级容错解析（去除 markdown 包裹、容忍并移除破坏语法的 `reasoning` 长文本字段、修复 trailing comma）。
- ✅ **Prompt 系统指引优化**: 全面精简提示词中的 JSON 结构要求，剔除容易引发格式问题的 `reasoning`，修正示例策略以引导大模型对追问类意图优先选择 `general_chat` 模式作自然语言应答。
- ✅ **缓存数据竞争修复**: 提前 `process_dingtalk_message` 中的对话历史写入节点，保证当前输入可以即时被 LLM 的 ContextBuilder 感知以完成无缝追问消解。
- ✅ **规则引擎退让机制**: 降低 "进度如何/状态怎样" 等正则拦截器的置信度至 0.70-0.75，避免其截胡应该被 LLM 接管的深层 Q&A 上下文。

### 新增文件
- ✅ `backend/.dockerignore` - 后端构建忽略文件
- ✅ `frontend/.dockerignore` - 前端构建忽略文件
- ✅ `docker-compose.prod.yml` - 生产环境配置
- ✅ `Makefile` - 快捷命令集
- ✅ `DOCKER_README.md` - Docker 使用指南
- ✅ `docs/技术/Docker部署指南.md` - 详细部署文档
- ✅ `backend/requirements.txt` - 添加 gunicorn 依赖

## 下一步

### 立即可做
1. 访问 http://localhost 使用应用
2. 查看日志: `docker-compose logs -f`
3. 测试 API: `curl http://localhost:8000/health`

### 生产部署
1. 使用 `docker-compose.prod.yml` 配置
2. 配置 SSL/TLS 证书
3. 设置环境变量 (SECRET_KEY, LLM_API_KEY 等)
4. 配置数据库备份策略
5. 设置监控和告警

### 性能优化
1. 根据 CPU 核心数调整 Gunicorn workers
2. 配置 Redis 缓存
3. 使用 PostgreSQL 替代 SQLite
4. 配置 CDN 加速前端资源

## 故障排查

> [!warning] 如果容器无法启动
```bash
# 查看详细错误
docker-compose logs backend
docker-compose logs frontend

# 重新构建
docker-compose build --no-cache
```

> [!warning] 如果无法访问服务
```bash
# 检查端口占用
netstat -tlnp | grep 80
netstat -tlnp | grep 8000

# 检查容器网络
docker network inspect tasktree-network
```

> [!warning] 如果数据丢失
```bash
# 备份数据
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/backup-$(date +%Y%m%d).tar.gz -C /data .

# 恢复数据
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/backup-YYYYMMDD.tar.gz -C /data
```

## 相关文档

- [[DOCKER|Docker 部署指南]]
- [[../00-开发记录|开发记录]]
- [Docker 使用指南](../../DOCKER_README.md)
- [开发记录](../00-开发记录.md)
- [API 接口文档](API接口.md)


## 2026-05-07 项目删除功能修复

### 问题描述
项目删除功能失败，错误信息：`NOT NULL constraint failed: ai_conversations.project_id`

### 根本原因
1. `ai_conversations`表的`project_id`字段设置为NOT NULL
2. SQLAlchemy在请求结束时尝试将关联的AI对话记录的`project_id`设置为NULL（因为project被删除）
3. 由于NOT NULL约束导致失败

### 解决方案
1. **修改数据库模型** (`backend/app/models/__init__.py`)
   - 将`AIConversation.project_id`改为可空字段
   - 修改外键约束为`ON DELETE SET NULL`
   - 移除可能导致问题的backref关联

2. **优化删除逻辑** (`backend/app/api/v1/projects.py`)
   - 使用独立的数据库连接，避免ORM session干扰
   - 在删除前启用外键约束（`PRAGMA foreign_keys = ON`）
   - 简化删除逻辑，依赖数据库的级联删除

3. **添加外键启用配置** (`backend/app/core/database.py`)
   - 在数据库连接时自动启用SQLite的外键约束

4. **创建数据库迁移脚本**
   - `backend/migrations/allow_ai_conversations_null_project.py` - 修改表结构
   - `backend/migrations/fix_ai_conversations_cascade.py` - 修复外键配置

5. **重新创建Docker volume**
   - 删除旧的`tasktree_tasktree-data` volume
   - 重新启动服务，应用新的表结构

### 验证结果
✅ 项目删除功能已完全修复
✅ 可以成功删除项目及其所有关联数据
✅ 外键级联删除正常工作

### 相关提交
- commit: 4bf55f6 - "fix: 修复项目删除功能 - 允许ai_conversations.project_id为NULL并优化删除逻辑"

## 2026-05-12 ReadHub 自动化闭环与知识沉淀 (阶段三)

### 新增功能
1. **ReadHub 专属设置系统**
   - 数据库新增 `readhub_settings` 表用于存储每个用户的独立配置（Obsidian Vault 路径、自动拉取间隔等）。
   - 前端新增 ReadHub 设置页面（`/app/readhub/settings`），允许用户直接在 UI 配置 Obsidian 知识库集成。
2. **Obsidian 知识沉淀服务**
   - 实现 `obsidian_service.py`：支持将 RSS 订阅文章（HTML）自动转化为 Markdown 格式。
   - 自动在 Markdown 头部生成 YAML Frontmatter（包含 title, source, author, date, tags 等元数据）。
   - 一键将文章安全写入本地 Obsidian Vault 指定目录中。
3. **文章转任务链路打通**
   - ReadHub 前端文章详情页新增**"转为任务"**按钮，支持选择目标项目。
   - 后端新增 `POST /articles/{id}/convert-to-task` 接口，自动带上文章来源链接与摘要并存入 TaskTree。
4. **钉钉 AI 机器人扩展 (ReadHub 专属命令)**
   - `/read` (或 `/阅读`、`/订阅`): 在钉钉中获取今日未读文章摘要及链接。
   - `/save <ID>` (或 `/保存`): 在钉钉中通过命令直接将指定文章推送到本地 Obsidian。
   - `/convert <ID> [项目名]` (或 `/转任务`): 在钉钉中通过命令直接将文章转化为工作任务。
   - 更新系统 `/help` 菜单，按 TaskTree 与 ReadHub 分组展示可用指令。

### 验证状态
✅ 后端服务启动正常，`readhub_settings` 表已自动创建。
✅ 前端路由与侧边栏成功挂载设置面板，文章操作按钮交互正常。
✅ 钉钉斜杠命令扩展及动作执行器联调通过。
