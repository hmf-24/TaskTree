# 第一阶段：构建阶段
FROM node:18-alpine AS build-stage

WORKDIR /app

# 设置环境变量
ENV NODE_ENV=production

# 复制依赖定义
COPY package*.json ./

# 清除 npm 缓存并安装所有依赖（包括 devDependencies）
RUN npm cache clean --force && \
    npm install --legacy-peer-deps --include=dev

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 第二阶段：生产阶段
FROM nginx:alpine

# 设置环境变量
ENV TZ=Asia/Shanghai

# 从构建阶段复制构建产物
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建日志目录
RUN mkdir -p /var/log/nginx && \
    chmod -R 755 /var/log/nginx

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]