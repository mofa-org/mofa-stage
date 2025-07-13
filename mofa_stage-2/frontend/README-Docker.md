# MoFA Stage Frontend Docker

## 快速使用（推荐）

### 从GitHub Container Registry拉取
```bash
# 拉取最新版本
docker pull ghcr.io/bh3gei/mofa-stage-frontend:latest

# 运行容器
docker run -d \
  --name mofa-frontend \
  -p 3000:80 \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/bh3gei/mofa-stage-frontend:latest
```

### 端口映射说明
前端容器会自动代理以下后端服务：
- API服务: 5002 -> /api
- WebSocket: 5002 -> /socket.io  
- WebSSH: 5001 -> /webssh
- ttyd终端: 7681 -> /ttyd
- VS Code: 8080 -> /vscode

## 本地构建
```bash
cd frontend
docker build -t mofa-stage-frontend .
```

## 运行容器

### 开发环境（连接本地后端）
```bash
docker run -d \
  --name mofa-frontend \
  -p 3000:80 \
  --add-host=host.docker.internal:host-gateway \
  mofa-stage-frontend
```

### 生产环境（连接远程后端）
```bash
docker run -d \
  --name mofa-frontend \
  -p 80:80 \
  -e BACKEND_URL=http://your-backend-server:5000 \
  mofa-stage-frontend
```

## Docker Compose方式
```yaml
version: '3'
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - BACKEND_URL=http://backend:5000
    depends_on:
      - backend
  
  backend:
    # 后端仍然在宿主机运行
    network_mode: host
```

## 优势
1. 解决Node.js版本依赖问题
2. 统一部署环境
3. 支持横向扩展
4. 内置nginx优化

## 注意事项
1. `host.docker.internal`在Linux需要`--add-host`参数
2. 生产环境记得修改后端API地址
3. 可以通过环境变量动态配置后端地址