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

### 🐳 Docker 部署（推荐）

使用 Docker 可以避免所有环境问题，实现最快速的部署：

```bash
# 一行命令部署前端
docker run -d -p 3000:80 liyao1119/mofa-stage-frontend

# 启动后端
cd backend && python app.py
```

详细说明请查看 [Docker 快速部署指南](DOCKER_QUICKSTART.md)。

### 传统安装方式

#### 环境要求

**系统支持**
- Linux（支持 apt-get 和 yum 包管理系统）
- macOS
- Windows 暂不支持，推荐使用 WSL（Windows Subsystem for Linux）

**软件要求**
- Python 3.8 或更高
- Node.js 14 或更高
- 已安装 MoFA 框架

#### 安装和运行脚本

项目提供了两个脚本：

- **install**: 一键安装所有依赖
  ```bash
  chmod +x install
  ./install
  ```
  自动安装后端/前端依赖，支持选择 Docker 或传统安装方式。

- **run**: 一键启动服务
  ```bash
  chmod +x run
  ./run
  ```
  支持 Docker 和传统部署模式。


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

## 用户旅程图

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MOFA Stage 用户旅程图</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f5f7fa;
            padding: 20px 10px;
            line-height: 1.4;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            padding: 20px;
        }
        
        h1 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 25px;
            font-size: 1.8em;
            font-weight: 400;
        }
        
        .journey-flow {
            display: flex;
            flex-direction: column;
            gap: 3px;
            margin-bottom: 20px;
        }
        
        .flow-row {
            display: flex;
            /* justify-content: space-between; */
            align-items: stretch;
            gap: 20px;
            position: relative;
        }
        
        .phase {
            flex: 1;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 2px;
            position: relative;
            display: flex;
            flex-direction: column;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        
        .phase-header {
            background: #6ACED1;
            color: white;
            padding: 10px 12px;
            border-radius: 6px 6px 0 0;
            margin: 0;
            font-size: 0.95em;
            font-weight: 500;
            text-align: center;
        }
        
        .flow-row:not(:first-child) .phase-header {
            display: none;
        }
        
        .flow-row:not(:first-child) .phase {
            padding-top: 0;
        }
        
        .phase-content {
            display: flex;
            flex-direction: column;
            gap: 0;
            flex: 1;
            padding: 10px;
        }
        
        .item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid #6ACED1;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            min-height: 70px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin: 0;
        }
        
        
        .item strong {
            font-size: 0.85em;
        }
        
        .item br + text,
        .item br ~ text {
            font-size: 0.8em;
            color: #666;
        }
        
        .arrow-connector {
            width: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        
        .arrow-connector::after {
            content: '→';
            font-size: 24px;
            color: #6ACED1;
            font-weight: bold;
        }
        
        /* 特殊样式 */
        .user-needs .phase-header {
            background: #FF5039;
        }
        
        .user-needs .item {
            border-left-color: #FF5039;
        }
        
        .tech-impl .phase-header {
            background: #FF6857;
        }
        
        .tech-impl .item {
            border-left-color: #FF6857;
        }
        
        .goals .phase-header {
            background: #FFC837;
        }
        
        .goals .item {
            border-left-color: #FFC837;
        }
        
        /* Removed connecting line behind phases */
        
        /* 响应式设计 */
        /* First phase in rows with headers should include padding for content */
        .flow-row:first-child .phase .phase-content {
            padding: 15px;
        }
        
        /* Phases in rows without headers should have the content fill completely */
        .flow-row:not(:first-child) .phase .phase-content {
            padding: 0;
            height: 100%;
        }
        
        /* Items in rows without headers should fill the phase completely */
        .flow-row:not(:first-child) .phase .item {
            border-radius: 8px;
            height: 100%;
            margin: 0;
        }
        
        @media (max-width: 1024px) {
            .flow-row {
                flex-direction: column;
                gap: 10px;
            }
            
            .arrow-connector {
                display: none;
            }
            
            .phase {
                width: 100%;
            }
            
            .flow-row:not(:first-child) .phase-header {
                display: block;
            }
        }
        
        /* 标签样式 */
        .tag {
            display: inline-block;
            padding: 2px 6px;
            background: rgba(106, 172, 209, 0.1);
            color: #6ACED1;
            border: 1px solid rgba(106, 172, 209, 0.2);
            border-radius: 10px;
            font-size: 0.65em;
            margin-top: 4px;
            font-weight: 500;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        
        .highlight {
            background: linear-gradient(45deg, #ffe259 0%, #ffa751 100%);
            color: #333;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 500;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>MoFA Stage 用户旅程图</h1>
        
        <div class="journey-flow">
            <!-- 行1 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-header">用户需求</div>
                </div>
                <div class="phase tech-impl">
                    <div class="phase-header">技术实现</div>
                </div>
                <div class="phase goals">
                    <div class="phase-header">达成目标</div>
                </div>
            </div>
            
            <!-- 空白填充行 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>快速上手 AI Agent 开发</strong>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>一键安装/启动脚本</strong>
                            <br><span style="font-size: 0.8em; color: #666;">图形化展示流程</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>两分钟上手</strong>
                            <br><span style="font-size: 0.8em; color: #666;">零配置</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 行2 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>可视化设计数据流</strong>
                            <div class="tag">Mermaid Diagram</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Mermaid & Dataflow 可视化</strong>
                            <br><span style="font-size: 0.8em; color: #666;">图形化展示流程</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>流程可视化</strong>
                            <br><span style="font-size: 0.8em; color: #666;">根据yaml配置，自动生成互动可视化流程图，流程一目了然</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 行3 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>浏览器内代码编辑与调试</strong>
                            <div class="tag">Web IDE</div>
                            <div class="tag">DevOps Ready</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>网页内集成开发环境</strong>
                            <br><span style="font-size: 0.8em; color: #666;">嵌入代码编辑器/文件管理/可视化预览/一键运行测试</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>代码-调试闭环</strong>
                            <br><span style="font-size: 0.8em; color: #666;">开发效率提升</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 行4 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>实时终端与远程连接</strong>
                            <div class="tag">Terminal Support</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>多终端支持</strong>
                            <br><span style="font-size: 0.8em; color: #666;">用户PC本地终端/SSH远程服务器终端</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>一站式开发环境</strong>
                            <br><span style="font-size: 0.8em; color: #666;">无需切换窗口</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 行5 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>复用或生成 Nodes/Dataflows</strong>
                            <div class="tag">Quick Start</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>快速Node创建</strong>
                            <br><span style="font-size: 0.8em; color: #666;">复制已有Node/根据模板创建/从零开始</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>模板驱动开发</strong>
                            <br><span style="font-size: 0.8em; color: #666;">避免用户无从下手，提供模板让用户修改</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 行6 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>智能生成Dataflows</strong>
                            <div class="tag">LLM Powered</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>AI驱动的Dataflow生成</strong>
                            <br><span style="font-size: 0.8em; color: #666;">用户输入需求，大模型自动根据已有Nodes生成Dataflow</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>AI Native开发</strong>
                            <br><span style="font-size: 0.8em; color: #666;">动态完成用户需求</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html> 