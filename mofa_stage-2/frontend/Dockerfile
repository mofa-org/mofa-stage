# 构建阶段
FROM node:lts-alpine AS builder

# 安装中文字符集和locale支持
RUN apk add --no-cache tzdata \
    && apk add --no-cache gcompat \
    && apk add --no-cache musl-locales musl-locales-lang

# 设置环境变量
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码 - 确保国际化文件被正确复制
COPY . .

# 验证国际化文件存在
RUN ls -la src/locales/ && cat src/locales/index.js | head -20

# 构建生产版本
RUN npm run build

# 验证构建产物中的国际化文件
RUN ls -la dist/assets/ | grep -E "\.(js|css)$" | head -5

# 运行阶段
FROM nginx:alpine

# 安装中文字符集和locale支持
RUN apk add --no-cache tzdata \
    && apk add --no-cache gcompat \
    && apk add --no-cache musl-locales musl-locales-lang

# 设置环境变量
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN.UTF-8 \
    LC_ALL=zh_CN.UTF-8

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost || exit 1