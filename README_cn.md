# MoFA_Stage

[English](README.md) | 中文

MoFA_Stage 是一个 Web 界面的开发工具，用于管理和编辑 MoFA 框架中的 Nodes 和 Dataflows。

## 功能

- **Agent 管理**
  - 浏览 Agent 列表
  - 创建和复制 Agent
  - 编辑 Agent 文件
  - 运行和停止 Agent
  - 查看运行日志

- **终端访问**
  - Web 终端
  - SSH 连接
  - ttyd 集成

- **代码编辑**
  - 文本编辑器
  - 文件浏览
  - VSCode Server 集成（可选）

## 技术栈

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

## 快速开始

### 环境要求

**系统支持**
- Linux（支持 apt-get 和 yum 包管理系统）
- macOS
- Windows 暂不支持，推荐使用 WSL（Windows Subsystem for Linux）

**软件要求**
- Python 3.8 或更高
- Node.js 14 或更高
- 已安装 MoFA 框架

### 安装和运行脚本

项目提供了两个脚本：

- **install.sh**: 一键安装所有依赖
  ```bash
  chmod +x install.sh
  ./install.sh
  ```
  自动安装后端/前端依赖，并根据需要安装 ttyd、构建前端。

- **run.sh**: 一键启动服务
  ```bash
  chmod +x run.sh
  ./run.sh
  ```


### 开发模式

1. 启动后端
```bash
cd backend
python app.py
```

2. 启动前端（开发模式）
```bash
cd frontend
npm run dev
```

访问 http://localhost:3000 。

### 生产部署


1. 构建前端
```bash
cd frontend
npm run build  # 生成在 dist 目录
```

2. 部署方式（二选一）

**使用 Nginx**

```nginx
server {
    listen 80;
    
    # 静态文件
    location / {
        root /path/to/mofa_stage/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API 转发
    location /api {
        proxy_pass http://localhost:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # WebSocket
    location /api/webssh {
        proxy_pass http://localhost:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**简易部署**

使用 Python 自带的 HTTP 服务器：
```bash
cd frontend/dist
python -m http.server 3000
```

启动后端：
```bash
cd backend
python app.py
```

## 常见问题

### 端口占用

如果遇到端口占用问题，可以用这条命令释放端口：

```bash
for port in 3000 5001 5002 7681; do
    pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        kill -9 $pid
        echo "释放了端口 $port"
    fi
done
```

### 端口说明

- 3000: 前端服务
- 5001: WebSSH 服务
- 5002: 主后端 API
- 7681: ttyd 终端

### ttyd 安装失败

如果 ttyd 自动安装失败，可以参考 [ttyd GitHub 页面](https://github.com/tsl0922/ttyd) 手动安装。

## 目录结构

```
mofa-stage/
├── backend/
│   ├── app.py              # 主应用
│   ├── config.py           # 配置文件
│   ├── routes/             # API 路由
│   │   ├── agents.py       # Agent 管理
│   │   ├── terminal.py     # 终端功能
│   │   ├── webssh.py       # SSH 连接
│   │   ├── vscode.py       # VSCode 集成
│   │   ├── settings.py     # 设置管理
│   │   ├── ttyd.py         # ttyd 集成
│   │   └── mermaid.py      # 图表渲染
│   ├── utils/              # 工具模块
│   │   ├── mofa_cli.py     # MoFA 命令封装
│   │   ├── file_ops.py     # 文件操作
│   │   └── ttyd_manager.py # ttyd 管理
│   └── requirements.txt    # Python 依赖
├── frontend/
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/     # UI 组件
│   │   ├── api/            # API 调用
│   │   ├── store/          # 状态管理
│   │   └── router/         # 路由配置
│   └── package.json        # Node.js 依赖
├── install.sh              # 安装脚本
└── run.sh                  # 启动脚本
``` 