# MoFA Stage Docker快速使用



## 使用方法（最简单）

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
cd backend
python app.py
```

#### 方法二：使用预构建镜像（待上传，not working）
```bash
# 直接运行前端容器
cd mofa-stage/frontend

docker run -d -p 3000:80 --name mofa-frontend \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/bh3gei/mofa-stage-frontend:latest

# 启动后端
cd ../backend
python app.py
```

### 3. 访问系统
打开浏览器访问：http://localhost:3000

## 注意事项
- 前端运行在Docker容器中（端口3000）- 完全独立环境
- 后端仍需在本地运行- 需要Python环境
- 确保后端正常启动后再访问前端

## 环境问题FAQ
Q: 我本地Node版本太低/太高/有冲突怎么办？
A: Docker容器内有独立的Node环境，不依赖本地的Node。

Q: 本地npm install总是失败怎么办？
A: 用Docker就不需要本地npm install了，所有依赖都在容器内安装。

Q: 需要先卸载本地的Node吗？
A: 不需要. Docker和本地环境完全隔离。

## Docker解决环境问题

**即使本地Node.js版本有冲突、npm依赖有问题，Docker也能让前端正常运行。**
- ✅ 容器内自带Node.js LTS版本
- ✅ 所有前端依赖都在容器内解决
- ✅ 不会污染本地环境
- ✅ 不需要安装Node.js或npm

## 已知问题
- 多语言显示可能有问题（显示key而非翻译）不影响功能使用