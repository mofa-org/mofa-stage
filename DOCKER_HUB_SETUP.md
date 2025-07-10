# Docker Hub配置指南

## 快速开始

### 1. 注册账号
访问 https://hub.docker.com/ 注册账号

### 2. 本地登录
```bash
docker login
# 输入用户名和密码
```

### 3. 手动推送镜像
```bash
cd frontend
./docker-push.sh
```

## GitHub Actions自动推送配置

### 1. 创建Docker Hub Access Token
1. 登录Docker Hub
2. Account Settings → Security → New Access Token
3. 权限选择：Read, Write, Delete
4. 复制生成的token

### 2. 配置GitHub Secret
1. 访问仓库设置：Settings → Secrets → Actions
2. 添加新Secret：
   - Name: `DOCKER_PASSWORD`
   - Value: 你的Access Token

### 3. 修改docker-push.sh中的用户名
编辑 `frontend/docker-push.sh`，修改第13行：
```bash
DOCKER_USERNAME="你的用户名"  # 修改为你的Docker Hub用户名
```

### 4. 修改GitHub Actions中的用户名
编辑 `.github/workflows/docker-hub.yml`，修改第11行：
```yaml
DOCKER_USERNAME: 你的用户名
```

## 验证配置

推送代码后，检查：
1. GitHub Actions是否成功运行
2. Docker Hub是否有新镜像：https://hub.docker.com/r/你的用户名/mofa-stage-frontend

## 使用镜像

配置完成后，任何人都可以：
```bash
docker pull 你的用户名/mofa-stage-frontend:latest
docker run -d -p 3000:80 你的用户名/mofa-stage-frontend:latest
```