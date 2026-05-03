---
source: 工作文档
author: HMF
created: 2026-04-10
description: "TaskTree Docker和Docker Compose部署指南"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/Python
  - Tech/Docker
---

# Docker 部署指南

> [!info] 概述
> 本指南介绍如何使用 Docker 和 Docker Compose 部署 TaskTree 应用。

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB 可用内存
- 至少 1GB 可用磁盘空间

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd tasktree
```

### 2. 配置环境变量

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，修改必要的配置
# 特别是 SECRET_KEY 和 LLM_API_KEY
nano .env
```

### 3. 启动容器

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务的日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 4. 验证部署

```bash
# 检查容器状态
docker-compose ps

# 测试后端 API
curl http://localhost:8000/health

# 访问前端
# 打开浏览器访问 http://localhost
```

## 常用命令

### 启动和停止

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时查看日志
docker-compose logs -f

# 查看最后 100 行日志
docker-compose logs --tail=100

# 查看特定时间范围的日志
docker-compose logs --since 2024-01-01 --until 2024-01-02
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 在容器中执行命令
docker-compose exec backend python -m pytest
```

### 数据管理

```bash
# 查看数据卷
docker volume ls

# 检查数据卷内容
docker volume inspect tasktree_tasktree-data

# 备份数据
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/tasktree-data-backup.tar.gz -C /data .

# 恢复数据
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/tasktree-data-backup.tar.gz -C /data
```

## 环境变量配置

### 后端配置

| 变量 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `SECRET_KEY` | JWT 密钥 | - | ✅ |
| `DEBUG` | 调试模式 | false | ❌ |
| `LOG_LEVEL` | 日志级别 | info | ❌ |
| `DATABASE_URL` | 数据库连接字符串 | sqlite+aiosqlite:////app/data/tasktree.db | ❌ |
| `LLM_PROVIDER` | LLM 提供商 | minimax | ❌ |
| `LLM_API_KEY` | LLM API 密钥 | - | ✅ (如使用 AI 功能) |
| `LLM_MODEL` | LLM 模型名称 | MiniMax-M2.7 | ❌ |

### Docker Compose 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `FRONTEND_PORT` | 前端端口 | 80 |
| `BACKEND_PORT` | 后端端口 | 8000 |
| `TZ` | 时区 | Asia/Shanghai |

## 性能优化

> [!tip] 后端优化
> 后端使用 Gunicorn + Uvicorn 配置，默认 4 个 worker 进程。根据 CPU 核心数调整：

```bash
# 在 backend/Dockerfile 中修改 workers 数量
# 推荐: workers = CPU 核心数 + 1
```

### 前端优化

前端使用 Nginx 作为 Web 服务器，已配置：
- Gzip 压缩
- 缓存策略
- 代理超时设置

### 数据库优化

对于生产环境，建议使用 PostgreSQL 而不是 SQLite：

```bash
# 修改 .env 文件
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/tasktree
```

## 监控和日志

### 健康检查

两个服务都配置了健康检查：

```bash
# 查看健康检查状态
docker-compose ps

# 查看健康检查日志
docker inspect tasktree-backend | grep -A 10 "Health"
```

### 日志管理

日志配置为 JSON 格式，最大 10MB，保留 3 个文件：

```bash
# 查看日志驱动配置
docker inspect tasktree-backend | grep -A 5 "LogConfig"

# 清理旧日志
docker system prune --volumes
```

## 故障排查

> [!warning] 后端无法启动
```bash
# 查看错误日志
docker-compose logs backend

# 检查数据库连接
docker-compose exec backend python -c "from app.core.database import engine; print(engine)"

# 检查依赖
docker-compose exec backend pip list
```

> [!warning] 前端无法访问
```bash
# 查看 Nginx 错误日志
docker-compose logs frontend

# 检查 Nginx 配置
docker-compose exec frontend nginx -t

# 检查端口占用
netstat -tlnp | grep 80
```

> [!warning] 数据库错误
```bash
# 检查数据卷
docker volume ls
docker volume inspect tasktree_tasktree-data

# 重新初始化数据库
docker-compose down -v
docker-compose up -d
```

> [!warning] 内存不足

```bash
# 查看容器资源使用
docker stats

# 限制容器内存 (在 docker-compose.yml 中添加)
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

## 生产部署

### 安全建议

1. **修改 SECRET_KEY**
   ```bash
   # 生成强密钥
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **使用 HTTPS**
   - 配置 SSL 证书
   - 在 Nginx 中启用 HTTPS

3. **环境变量管理**
   - 不要在代码中硬编码敏感信息
   - 使用 Docker secrets 或环境变量文件

4. **数据库备份**
   - 定期备份数据库
   - 测试恢复流程

### 扩展部署

对于高可用部署，考虑：

1. **负载均衡**
   - 使用 Nginx 或 HAProxy 进行负载均衡
   - 运行多个后端实例

2. **数据库集群**
   - 使用 PostgreSQL 集群
   - 配置主从复制

3. **容器编排**
   - 使用 Kubernetes 进行容器编排
   - 自动扩展和故障转移

## 更新和维护

### 更新应用

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

### 清理资源

```bash
# 删除未使用的镜像
docker image prune

# 删除未使用的卷
docker volume prune

# 删除所有未使用的资源
docker system prune -a
```

## 常见问题

### Q: 如何修改端口？

A: 在 `.env` 文件中修改 `FRONTEND_PORT` 和 `BACKEND_PORT`，或在 `docker-compose.yml` 中修改 `ports` 配置。

### Q: 如何使用自定义数据库？

A: 修改 `.env` 文件中的 `DATABASE_URL`，确保数据库服务可访问。

### Q: 如何备份数据？

A: 使用 `docker volume` 命令备份数据卷，或定期导出数据库。

### Q: 如何监控容器性能？

A: 使用 `docker stats` 命令实时监控，或使用 Prometheus + Grafana 进行详细监控。

## 相关资源

- [[../tech/API|API 接口文档]]
- [[../tech/DATABASE|数据库设计]]
- [[DEPLOYMENT_LOG|部署记录]]
- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 官方文档](https://docs.docker.com/compose/)
- [FastAPI 部署指南](https://fastapi.tiangolo.com/deployment/)
- [Nginx 官方文档](https://nginx.org/en/docs/)
