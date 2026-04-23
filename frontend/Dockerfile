# 生产镜像：直接复制本地构建产物
FROM nginx:alpine

# 复制构建产物
COPY dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]