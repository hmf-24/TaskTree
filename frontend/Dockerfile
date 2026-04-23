# 第一阶段：构建阶段
FROM node:18-alpine AS build-stage

WORKDIR /app

# 复制依赖定义
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码并构建
COPY . .
RUN npm run build

# 第二阶段：生产阶段
FROM nginx:alpine

# 从构建阶段复制构建产物
COPY --from=build-stage /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]