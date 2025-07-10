# MoFA_Stage

English | [中文](README_cn.md)

MoFA_Stage is a web-based development tool for managing and editing Agents and Dataflows in the MoFA framework.

## Features

- **Agent Management**
  - Browse Agent list
  - Create and copy Agents
  - Edit Agent files
  - Run and stop Agents
  - View execution logs

- **Terminal Access**
  - Web terminal
  - SSH connections
  - ttyd integration

- **Code Editing**
  - Text editor
  - File browser
  - VSCode Server integration (optional)

## Technology Stack

**Backend**
- Python + Flask
- WebSocket support
- SSH terminal integration
- RESTful API

**Frontend**
- Vue 3 + Element Plus
- Monaco editor

**Third-party Services**
- ttyd (recommanded)
- code-server (optional)

## Quick Start

### 🐳 Docker Deployment (Recommended)

For the fastest setup with no environment conflicts, use Docker:

```bash
# One-line deployment
docker run -d -p 3000:80 liyao1119/mofa-stage-frontend

# Then start backend
cd backend && python app.py
```

See [Docker Quick Start Guide](DOCKER_QUICKSTART.md) for detailed instructions.

### Traditional Installation

#### Environment Requirements

**System Support**
- Linux (supports apt-get and yum package managers)
- macOS
- Windows is not currently supported, WSL (Windows Subsystem for Linux) is recommended

**Software Requirements**
- Python 3.8 or higher
- Node.js 14 or higher
- MoFA framework installed

#### Installation and Run Scripts

The project provides two scripts:

- **install**: One-click installation of all dependencies
  ```bash
  chmod +x install
  ./install
  ```
  Automatically installs backend/frontend dependencies, with options for Docker or traditional installation.

- **run**: One-click service startup
  ```bash
  chmod +x run
  ./run
  ```
  Supports both Docker and traditional deployment modes.

### Development Mode

1. Start the backend
```bash
cd backend
python app.py
```

2. Start the frontend (development mode)
```bash
cd frontend
npm run dev
```

Access http://localhost:3000.

### Production Deployment

1. Build the frontend
```bash
cd frontend
npm run build  # Generates in the dist directory
```

2. Deployment methods (choose one)

**Using Nginx**

```nginx
server {
    listen 80;
    
    # Static files
    location / {
        root /path/to/mofa_stage/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API forwarding
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

**Simple Deployment**

Using Python's built-in HTTP server:
```bash
cd frontend/dist
python -m http.server 3000
```

Start the backend:
```bash
cd backend
python app.py
```

## Common Issues

### Port Occupation

If you encounter port occupation issues, you can use this command to release ports:

```bash
for port in 3000 5001 5002 7681; do
    pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        kill -9 $pid
        echo "Released port $port"
    fi
done
```

### Port Description

- 3000: Frontend service
- 5001: WebSSH service
- 5002: Main backend API
- 7681: ttyd terminal

### ttyd Installation Failure

If ttyd automatic installation fails, you can refer to the [ttyd GitHub page](https://github.com/tsl0922/ttyd) for manual installation.

## Directory Structure

```
mofa-stage/
├── backend/
│   ├── app.py              # Main application
│   ├── config.py           # Configuration
│   ├── routes/             # API routes
│   │   ├── agents.py       # Agent management
│   │   ├── terminal.py     # Terminal features
│   │   ├── webssh.py       # SSH connections
│   │   ├── vscode.py       # VSCode integration
│   │   ├── settings.py     # Settings management
│   │   ├── ttyd.py         # ttyd integration
│   │   └── mermaid.py      # Chart rendering
│   ├── utils/              # Utility modules
│   │   ├── mofa_cli.py     # MoFA command wrapper
│   │   ├── file_ops.py     # File operations
│   │   └── ttyd_manager.py # ttyd management
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── views/          # Page components
│   │   ├── components/     # UI components
│   │   ├── api/            # API calls
│   │   ├── store/          # State management
│   │   └── router/         # Routing
│   └── package.json        # Node.js dependencies
├── install.sh              # Installation script
└── run.sh                  # Startup script
```

## User Journey

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MOFA Stage User Journey</title>
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
        
        /* Special styles */
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
        
        /* Responsive design */
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
        
        /* Tag styles */
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
        <h1>MoFA Stage User Journey</h1>
        
        <div class="journey-flow">
            <!-- Row 1 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-header">User Needs</div>
                </div>
                <div class="phase tech-impl">
                    <div class="phase-header">Technical Implementation</div>
                </div>
                <div class="phase goals">
                    <div class="phase-header">Achieved Goals</div>
                </div>
            </div>
            
            <!-- Filling row -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Quickly Start AI Agent Development</strong>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>One-click installation/start scripts</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Graphically display process</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Get started in two minutes</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Zero configuration</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 2 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Visualize dataflow design</strong>
                            <div class="tag">Mermaid Diagram</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Mermaid & Dataflow visualization</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Graphically display process</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Process visualization</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Automatically generate interactive visual flowchart from yaml configuration, making the process clear at a glance</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 3 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Code editing and debugging within browser</strong>
                            <div class="tag">Web IDE</div>
                            <div class="tag">DevOps Ready</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Web-based integrated development environment</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Embedded code editor/file management/visual preview/one-click test run</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Code-debugging feedback loop</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Improved development efficiency</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 4 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Real-time terminal and remote connection</strong>
                            <div class="tag">Terminal Support</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Multi-terminal support</strong>
                            <br><span style="font-size: 0.8em; color: #666;">User PC local terminal / SSH remote server terminal</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>One-stop development environment</strong>
                            <br><span style="font-size: 0.8em; color: #666;">No need to switch windows</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 5 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Reuse or generate Nodes/Dataflows</strong>
                            <div class="tag">Quick Start</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Fast Node creation</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Copy existing Node / Create from template / Start from scratch</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Template-driven development</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Provide templates to avoid users having no starting point</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Row 6 -->
            <div class="flow-row">
                <div class="phase user-needs">
                    <div class="phase-content">
                        <div class="item">
                            <strong>Intelligent Generation of Dataflows</strong>
                            <div class="tag">LLM Powered</div>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase tech-impl">
                    <div class="phase-content">
                        <div class="item">
                            <strong>AI-driven Dataflow generation</strong>
                            <br><span style="font-size: 0.8em; color: #666;">User inputs requirements, large model automatically generates Dataflow based on existing Nodes</span>
                        </div>
                    </div>
                </div>
                <div class="arrow-connector"></div>
                <div class="phase goals">
                    <div class="phase-content">
                        <div class="item">
                            <strong>AI-native development</strong>
                            <br><span style="font-size: 0.8em; color: #666;">Dynamically fulfill user requirements</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>