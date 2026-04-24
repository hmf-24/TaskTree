# TaskTree Docker 部署指南

## 快速开始

### 1. 准备环境

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑 .env 文件，修改必要的配置
# 特别是 SECRET_KEY 和 LLM_API_KEY
nano .env
```

### 2. 启动应用

```bash
# 使用 Makefile (推荐)
make build
make up

# 或使用 docker-compose 命令
docker-compose build
docker-compose up -d
```

### 3. 验证部署

```bash
# 查看容器状态
make ps

# 查看日志
make logs

# 测试服务
make health
```

## 常用命令

### 使用 Makefile (推荐)

```bash
# 查看所有可用命令
make help

# 启动服务
make up

# 停止服务
make down

# 重启服务
make restart

# 查看日志
make logs
make logs-backend
make logs-frontend

# 进入容器
make shell-backend
make shell-frontend

# 运行测试
make test

# 备份数据
make backup

# 恢复数据
make restore

# 检查健康状态
make health

# 完全清理
make clean-all
```

### 使用 docker-compose 命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh

# 运行命令
docker-compose exec backend python -m pytest
```

## 部署配置

### 开发环境

```bash
# 使用默认的 docker-compose.yml
docker-compose up -d
```

### 生产环境

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d

# 或使用 Makefile
make -f Makefile.prod up
```

## 环境变量

### 必需配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `SECRET_KEY` | JWT 密钥 | `your-secret-key-here` |
| `LLM_API_KEY` | LLM API 密钥 | `sk-xxx` |

### 可选配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEBUG` | 调试模式 | false |
| `LOG_LEVEL` | 日志级别 | info |
| `DATABASE_URL` | 数据库连接 | sqlite+aiosqlite:////app/data/tasktree.db |
| `LLM_PROVIDER` | LLM 提供商 | minimax |
| `LLM_MODEL` | LLM 模型 | MiniMax-M2.7 |

## 数据管理

### 备份数据

```bash
# 使用 Makefile
make backup

# 或手动备份
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/tasktree-data-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

### 恢复数据

```bash
# 使用 Makefile
make restore

# 或手动恢复
docker run --rm -v tasktree_tasktree-data:/data -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/tasktree-data-YYYYMMDD-HHMMSS.tar.gz -C /data
```

## 故障排查

### 后端无法启动

```bash
# 查看错误日志
docker-compose logs backend

# 检查依赖
docker-compose exec backend pip list

# 检查数据库
docker-compose exec backend python -c "from app.core.database import engine; print(engine)"
```

### 前端无法访问

```bash
# 查看 Nginx 日志
docker-compose logs frontend

# 检查 Nginx 配置
docker-compose exec frontend nginx -t

# 检查端口占用
netstat -tlnp | grep 80
```

### 数据库错误

```bash
# 重新初始化
docker-compose down -v
docker-compose up -d
```

## 性能优化

### 后端优化

- 使用 Gunicorn + Uvicorn 提高性能
- 默认 4 个 worker 进程
- 可根据 CPU 核心数调整

### 前端优化

- 使用 Nginx 作为 Web 服务器
- 启用 Gzip 压缩
- 配置缓存策略

### 数据库优化

- 开发环境使用 SQLite
- 生产环境建议使用 PostgreSQL

## 监控和日志

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 查看特定服务
docker-compose logs -f backend

# 查看最后 100 行
docker-compose logs --tail=100
```

### 健康检查

```bash
# 查看健康状态
make health

# 或手动检查
curl http://localhost:8000/health
curl http://localhost/
```

### 资源监控

```bash
# 查看容器资源使用
docker stats

# 或使用 Makefile
make stats
```

## 更新和维护

### 更新应用

```bash
# 拉取最新代码
git pull origin main

# 重新构建
make build

# 重启服务
make restart
```

### 清理资源

```bash
# 删除未使用的镜像
docker image prune

# 删除未使用的卷
docker volume prune

# 完全清理
make clean-all
```

## 生产部署建议

1. **安全性**
   - 修改 SECRET_KEY
   - 使用强密码
   - 启用 HTTPS

2. **性能**
   - 使用 PostgreSQL
   - 配置负载均衡
   - 启用缓存

3. **监控**
   - 配置日志收集
   - 设置告警
   - 定期备份

4. **维护**
   - 定期更新依赖
   - 监控磁盘空间
   - 清理旧日志

## 相关文档

- [Docker 部署指南](docs/技术/Docker部署指南.md)
- [API 接口文档](docs/技术/API接口.md)
- [技术方案](docs/技术/技术方案.md)

## 获取帮助

如有问题，请查看：
- Docker 官方文档: https://docs.docker.com/
- Docker Compose 文档: https://docs.docker.com/compose/
- FastAPI 部署指南: https://fastapi.tiangolo.com/deployment/
