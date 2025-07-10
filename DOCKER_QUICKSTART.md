# MoFA Stage Docker快速使用

## 同事使用方法（最简单）

### 1. 确保Docker已安装
```bash
docker --version
```

### 2. 启动MoFA Stage

#### 方法一：使用本地构建（推荐）
```bash
# 克隆代码
git clone https://github.com/BH3GEI/mofa-stage.git
cd mofa-stage

# 构建并启动前端
cd frontend
./docker-build.sh

# 启动后端（另一个终端）
cd ../backend
python app.py
```

#### 方法二：使用预构建镜像（待上传）
```bash
# 直接运行前端容器
docker run -d -p 3000:80 --name mofa-frontend \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/bh3gei/mofa-stage-frontend:latest

# 启动后端
cd backend
python app.py
```

### 3. 访问系统
打开浏览器访问：http://localhost:3000

## 注意事项
- 前端运行在Docker容器中（端口3000）
- 后端仍需在本地运行（端口5002）
- 确保后端正常启动后再访问前端

## 已知问题
- 多语言显示可能有问题（显示key而非翻译）
- 不影响功能使用