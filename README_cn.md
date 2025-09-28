# MoFA Stage Desktop

[English](README.md) | 中文

MoFA Stage Desktop 是基于 Electron 的桌面应用程序，用于管理和编辑 MoFA 框架中的 Nodes 和 Dataflows，提供集成服务的统一开发平台。

## 功能

- **Agent 管理**
  - 浏览 Agent 列表
  - 创建和复制 Agent
  - 编辑 Agent 文件
  - 运行和停止 Agent
  - 查看执行日志

- **终端访问**
  - Web 终端
  - SSH 连接
  - ttyd 集成

- **代码编辑**
  - 文本编辑器
  - 文件浏览
  - VSCode Server 集成（可选）

- **桌面集成**
  - 跨平台支持（Windows、macOS、Linux）
  - 单一安装包
  - 内嵌 Python 后端
  - 无需环境配置

## 技术栈

**桌面框架**
- Electron 跨平台桌面应用

**后端**
- Python + Flask
- WebSocket 支持
- SSH 终端集成
- RESTful API

**前端**
- Vue 3 + Element Plus
- Monaco 编辑器

**第三方服务**
- ttyd（推荐）
- code-server（可选）

## 项目结构

```
mofa-stage-desktop/
├── electron/           # Electron 主进程代码
│   ├── main.js        # 主进程入口
│   └── preload.js     # 预加载脚本
├── frontend/          # Vue.js 前端代码
├── backend/           # Flask 后端代码
├── scripts/           # 构建脚本
├── assets/            # 应用图标和资源
└── dist/              # 构建输出目录
```

## 快速开始

### 用户部署

**方法一：下载发布包（推荐）**

1. 从发布页面下载相应的安装程序
   - Windows：`.exe` 安装程序
   - macOS：`.dmg` 安装包
   - Linux：`AppImage` 文件

2. 安装并运行应用程序
   - 无需额外设置
   - Python 环境已内嵌

**方法二：从源码构建**

```bash
# 克隆仓库
git clone https://github.com/mofa-org/mofa-stage-desktop.git
cd mofa-stage-desktop

# 安装依赖
npm install
cd frontend && npm install
cd ../backend && pip install -r requirements.txt

# 构建和打包
npm run build
npm run dist
```

### 开发部署

#### 环境要求

**系统支持**
- Windows 10/11
- macOS 10.15+
- Linux（Ubuntu 18.04+ 或同等版本）

**软件要求**
- Node.js 18 或更高版本
- Python 3.8 或更高版本
- npm 或 yarn

#### 开发环境搭建

1. **克隆并安装依赖**
   ```bash
   git clone https://github.com/mofa-org/mofa-stage-desktop.git
   cd mofa-stage-desktop
   
   # 安装根目录依赖
   npm install
   
   # 安装前端依赖
   cd frontend
   npm install
   
   # 安装后端依赖
   cd ../backend
   pip install -r requirements.txt
   cd ..
   ```

2. **开发模式**
   ```bash
   npm run dev
   ```
   此命令将：
   - 启动后端 Flask 服务器
   - 启动前端开发服务器
   - 在开发模式下启动 Electron

3. **单独服务**
   ```bash
   # 仅启动后端
   npm run backend:dev
   
   # 仅启动前端
   npm run frontend:dev
   ```

#### 构建和打包

1. **生产构建**
   ```bash
   npm run build
   ```
   这将：
   - 构建前端应用程序
   - 使用 PyInstaller 打包 Python 后端

2. **创建可分发包**
   ```bash
   npm run dist
   ```
   在 `dist/` 目录中生成特定平台的安装程序

## 系统要求

### 用户端
- 内存：最少 4GB，推荐 8GB+
- 存储：最少 500MB 可用空间
- 操作系统：
  - Windows 10/11
  - macOS 10.15+
  - Ubuntu 18.04+ 或同等 Linux 发行版

### 开发端
- Node.js 18 或更高版本
- Python 3.8 或更高版本
- npm 或 yarn
- Git（用于版本控制）

## 开发指南

### 可用脚本

- `npm run dev` - 启动开发服务器（前端 + 后端 + Electron）
- `npm run frontend:dev` - 仅启动前端开发服务器
- `npm run backend:dev` - 仅启动后端服务器
- `npm run frontend:build` - 构建生产前端
- `npm run backend:build` - 使用 PyInstaller 打包后端
- `npm run build` - 构建前端和后端
- `npm run dist` - 创建可分发的桌面包

### 调试

1. **启用开发者工具**
   - 按 `F12` 或从菜单选择 "Toggle DevTools"

2. **查看后端日志**
   - 后端日志显示在 Electron 主进程控制台中

3. **重新加载应用程序**
   - 按 `Ctrl+R`（Windows/Linux）或 `Cmd+R`（macOS）

### 后端打包

后端使用 PyInstaller 打包为独立可执行文件：

```bash
python scripts/build_backend.py
```

此脚本将：
- 使用 PyInstaller 打包 Flask 应用程序
- 包含所有必要的依赖项
- 创建单个可执行文件
- 处理特定平台的要求

### 桌面应用程序打包

使用 electron-builder 创建特定平台的包：

```bash
npm run electron:pack  # 创建无安装程序的包
npm run dist          # 创建安装程序/可分发文件
```

#### 包输出

运行 `npm run dist` 后，您将在 `dist/` 目录中找到特定平台的包：

- **Windows**：`.exe` 安装程序和解压应用程序
- **macOS**：`.dmg` 磁盘映像和 `.app` 包
- **Linux**：`AppImage` 便携应用程序

## 常见问题

### 端口冲突

应用程序从默认值开始自动查找可用端口：

| 服务 | 默认端口 | 说明 |
|------|----------|------|
| 后端 API | 5002 | Flask 主服务 |
| WebSSH | 5001 | SSH 终端服务 |
| 前端（开发） | 3000 | 开发服务器 |
| ttyd | 7681 | Web 终端 |

如果遇到端口冲突，应用程序将自动搜索可用端口。

### Python 依赖

确保已安装 `requirements.txt` 中的所有依赖项：

```bash
cd backend
pip install -r requirements.txt
```

### 前端构建问题

如果前端构建失败：

```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### 应用程序启动

首次启动可能需要更长时间，因为后端需要初始化。应用程序将：
1. 启动 Python 后端服务
2. 初始化前端
3. 启动 Electron 窗口

### 平台特定问题

**Windows**
- 确保 Python 在 PATH 中
- 某些杀毒软件可能会标记打包的可执行文件

**macOS**
- 您可能需要在安全性与隐私设置中允许应用程序
- Gatekeeper 可能需要手动批准首次启动

**Linux**
- 确保安装了必要的库
- AppImage 可能需要可执行权限：`chmod +x MoFA-Stage-Desktop.AppImage`

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | Web 界面（开发） |
| 后端 API | 5002 | Flask 服务 |
| WebSSH | 5001 | SSH 终端 |
| ttyd | 7681 | Web 终端 |
| VS Code | 8080 | 代码编辑器（如果启用） |

## 故障排查

### 释放端口冲突

如果遇到端口占用问题，使用此命令释放端口：

```bash
for port in 3000 5001 5002 7681; do
    pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        kill -9 $pid
        echo "释放了端口 $port"
    fi
done
```

### 检查服务状态

1. **检查后端是否运行**
   ```bash
   curl http://localhost:5002/api/system/info
   ```

2. **检查前端连接**
   ```bash
   curl http://localhost:3000
   ```

3. **查看应用程序日志**
   - 在应用程序中打开开发者工具
   - 检查控制台选项卡以查看前端日志
   - 后端日志出现在运行应用程序的终端中

## 贡献指南

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/AmazingFeature`）
3. 提交您的更改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 致谢

- [Electron](https://electronjs.org/) - 跨平台桌面应用程序框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Flask](https://flask.palletsprojects.com/) - Python 微框架
- [MoFA](https://github.com/mofa-org/mofa) - AI Agent 框架