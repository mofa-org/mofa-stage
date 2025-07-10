# MoFA Stage Docker 快速部署指南

## 🐳 为什么选择 Docker？

**Docker 完美解决环境问题：**
- ✅ 无需安装 Node.js、npm 等前端环境
- ✅ 避免版本冲突和依赖问题
- ✅ 一键启动，开箱即用
- ✅ 环境完全隔离，不影响本地系统

## 🚀 快速开始（30秒部署）

### 方法一：使用官方镜像（推荐）

```bash
# 1. 拉取并启动前端
docker run -d -p 3000:80 --name mofa-frontend \
  --add-host=host.docker.internal:host-gateway \
  liyao1119/mofa-stage-frontend:latest

# 2. 克隆仓库并启动后端
git clone https://github.com/mofa-org/mofa-stage.git
cd mofa-stage/backend
pip install -r requirements.txt
python app.py

# 3. 访问系统
# 打开浏览器：http://localhost:3000
```

### 方法二：本地构建

```bash
# 1. 克隆代码
git clone https://github.com/mofa-org/mofa-stage.git
cd mofa-stage

# 2. 使用安装脚本（支持选择Docker模式）
./install

# 3. 启动服务
./run
```

## 📋 系统要求

- Docker Desktop（[下载地址](https://www.docker.com/products/docker-desktop/)）
- Python 3.8+（仅后端需要）
- 4GB 可用内存

## 🔧 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Web界面 |
| 后端API | 5002 | Flask服务 |
| WebSSH | 5001 | SSH终端 |
| ttyd | 7681 | Web终端 |
| VS Code | 8080 | 代码编辑器 |

## 🛠️ 高级配置

### 自定义构建

```bash
cd frontend
# 修改配置后构建
docker build -t my-mofa-frontend .
docker run -d -p 3000:80 my-mofa-frontend
```

### 使用 Docker Compose（即将支持）

```bash
docker-compose up -d
```

## ❓ 常见问题

### Q: 提示端口被占用？
```bash
# 查看占用3000端口的进程
lsof -i :3000
# 或更改端口映射
docker run -d -p 8000:80 ...
```

### Q: 容器无法连接后端？
确保后端服务已启动：
```bash
cd backend && python app.py
```

### Q: 如何更新到最新版本？
```bash
docker pull liyao1119/mofa-stage-frontend:latest
docker stop mofa-frontend
docker rm mofa-frontend
# 重新运行docker run命令
```

### Q: 如何查看容器日志？
```bash
docker logs mofa-frontend
```

## 🔍 故障排查

1. **检查Docker是否正常运行**
   ```bash
   docker ps
   ```

2. **检查网络连接**
   ```bash
   curl http://localhost:3000
   curl http://localhost:5002/api/settings
   ```

3. **重启容器**
   ```bash
   docker restart mofa-frontend
   ```

## 📝 已知问题

- 多语言显示异常（显示key而非翻译文本）- 不影响功能使用
- Windows用户需要开启WSL2以获得最佳性能

## 🤝 贡献

欢迎提交Issue和PR！
- [报告问题](https://github.com/mofa-org/mofa-stage/issues)
- [查看源码](https://github.com/mofa-org/mofa-stage)

## 📄 许可证

本项目采用 Apache-2.0 许可证