# MoFA Stage Desktop

[English](README.md) | 中文

MoFA Stage Desktop 是基于 Electron 的桌面应用程序，用于 AI 智能体开发和管理。

## 功能特性

- **智能体管理** - 浏览、创建、编辑、运行和监控智能体
- **终端访问** - Web 终端、SSH 连接、ttyd 集成
- **代码编辑** - 文本编辑器、文件浏览器、可选 VSCode Server
- **跨平台** - Windows、macOS、Linux，内嵌 Python 后端

## 快速开始

### 下载安装
从 [Releases](https://github.com/mofa-org/mofa-stage/releases) 下载：
- Windows: `.exe` 安装包
- macOS: `.dmg` 安装包
- Linux: `AppImage` 文件

### 开发环境

```bash
# 克隆和设置
git clone https://github.com/mofa-org/mofa-stage.git
cd mofa-stage
npm install

# 启动开发
npm run dev
```

**环境要求：** Node.js 18+，Python 3.8+

## 构建发布

```bash
# 生产构建
npm run build

# 创建安装包
npm run dist

# 发布新版本
npm run version:patch  # 或 minor/major
```

## 发布流程

### 发布新版本

1. **准备代码**
   ```bash
   git add .
   git commit -m "你的修改"
   git push
   ```

2. **创建发布**
   ```bash
   npm run version:patch  # 0.6.0 -> 0.6.1
   npm run version:minor  # 0.6.0 -> 0.7.0  
   npm run version:major  # 0.6.0 -> 1.0.0
   ```

3. **监控构建** - 检查 GitHub Actions 自动构建 macOS/Windows 版本

## 技术栈

- **桌面端：** Electron
- **后端：** Python + Flask + WebSocket
- **前端：** Vue 3 + Element Plus + Monaco Editor

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 3000 | 开发服务器 |
| 后端 | 5002 | API 服务 |
| WebSSH | 5001 | SSH 终端 |
| ttyd | 7681 | Web 终端 |

## 故障排除

**端口冲突：**
```bash
npm run kill-ports  # 自动清理冲突端口
```

**重置依赖：**
```bash
rm -rf node_modules frontend/node_modules
npm run install-all
```

## 许可证

Apache License 2.0 - 查看 [LICENSE](LICENSE) 文件。