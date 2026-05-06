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
