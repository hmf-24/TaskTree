.PHONY: help build up down logs restart clean test lint format

# 默认目标
help:
	@echo "TaskTree Docker 命令"
	@echo ""
	@echo "构建和部署:"
	@echo "  make build          - 构建 Docker 镜像"
	@echo "  make up             - 启动所有服务"
	@echo "  make down           - 停止所有服务"
	@echo "  make restart        - 重启所有服务"
	@echo ""
	@echo "日志和调试:"
	@echo "  make logs           - 查看所有服务日志"
	@echo "  make logs-backend   - 查看后端日志"
	@echo "  make logs-frontend  - 查看前端日志"
	@echo "  make ps             - 查看容器状态"
	@echo ""
	@echo "开发:"
	@echo "  make test           - 运行后端测试"
	@echo "  make lint           - 运行代码检查"
	@echo "  make format         - 格式化代码"
	@echo ""
	@echo "清理:"
	@echo "  make clean          - 停止并删除所有容器"
	@echo "  make clean-volumes  - 删除所有数据卷"
	@echo "  make clean-all      - 完全清理（包括镜像）"

# 构建镜像
build:
	@echo "构建 Docker 镜像..."
	docker-compose build

# 启动服务
up:
	@echo "启动所有服务..."
	docker-compose up -d
	@echo "等待服务启动..."
	@sleep 3
	@docker-compose ps

# 停止服务
down:
	@echo "停止所有服务..."
	docker-compose down

# 重启服务
restart:
	@echo "重启所有服务..."
	docker-compose restart
	@docker-compose ps

# 查看日志
logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

# 查看容器状态
ps:
	docker-compose ps

# 运行测试
test:
	@echo "运行后端测试..."
	docker-compose exec backend python -m pytest -v

test-coverage:
	@echo "运行测试并生成覆盖率报告..."
	docker-compose exec backend python -m pytest --cov=app --cov-report=html

# 代码检查
lint:
	@echo "运行代码检查..."
	docker-compose exec backend python -m pylint app/

# 代码格式化
format:
	@echo "格式化代码..."
	docker-compose exec backend python -m black app/
	docker-compose exec backend python -m isort app/

# 进入容器
shell-backend:
	docker-compose exec backend bash

shell-frontend:
	docker-compose exec frontend sh

# 清理
clean:
	@echo "停止并删除所有容器..."
	docker-compose down

clean-volumes:
	@echo "删除所有数据卷..."
	docker-compose down -v

clean-all:
	@echo "完全清理..."
	docker-compose down -v
	docker rmi tasktree-backend:latest tasktree-frontend:latest

# 数据库操作
db-migrate:
	@echo "运行数据库迁移..."
	docker-compose exec backend alembic upgrade head

db-downgrade:
	@echo "回滚数据库..."
	docker-compose exec backend alembic downgrade -1

# 备份和恢复
backup:
	@echo "备份数据..."
	@mkdir -p backups
	docker run --rm -v tasktree_tasktree-data:/data -v $$(pwd)/backups:/backup \
		alpine tar czf /backup/tasktree-data-$$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

restore:
	@echo "恢复数据..."
	@read -p "输入备份文件名: " backup_file; \
	docker run --rm -v tasktree_tasktree-data:/data -v $$(pwd)/backups:/backup \
		alpine tar xzf /backup/$$backup_file -C /data

# 健康检查
health:
	@echo "检查服务健康状态..."
	@echo "后端: $$(curl -s http://localhost:8000/health || echo '❌ 不可用')"
	@echo "前端: $$(curl -s http://localhost/ > /dev/null && echo '✅ 正常' || echo '❌ 不可用')"

# 统计信息
stats:
	docker stats --no-stream

# 环境检查
check-env:
	@echo "检查环境..."
	@echo "Docker 版本: $$(docker --version)"
	@echo "Docker Compose 版本: $$(docker-compose --version)"
	@echo ".env 文件: $$(test -f .env && echo '✅ 存在' || echo '❌ 不存在')"
	@echo "后端 Dockerfile: $$(test -f backend/Dockerfile && echo '✅ 存在' || echo '❌ 不存在')"
	@echo "前端 Dockerfile: $$(test -f frontend/Dockerfile && echo '✅ 存在' || echo '❌ 不存在')"
