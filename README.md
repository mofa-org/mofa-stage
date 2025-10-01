# MoFA Stage Desktop

English | [中文](README_cn.md)

MoFA Stage Desktop is an Electron-based desktop application for AI agent development and management.

## Features

- **Agent Management** - Browse, create, edit, run and monitor agents
- **Terminal Access** - Desktop terminal (Electron), web terminal, SSH connections, ttyd integration  
- **Code Editing** - Text editor, file browser, optional VSCode Server
- **Cross-platform** - Windows, macOS, Linux with embedded Python backend

## Quick Start

### Download & Install
Download from [Releases](https://github.com/mofa-org/mofa-stage/releases):
- Windows: `.exe` installer
- macOS: `.dmg` package  
- Linux: `AppImage` file

### Development

```bash
# Clone and setup
git clone https://github.com/mofa-org/mofa-stage.git
cd mofa-stage
npm install

# Start development
npm run dev
```

**Requirements:** Node.js 18+, Python 3.8+

## Build & Release

```bash
# Build for production
npm run build

# Create installers
npm run dist

# Release new version
npm run version:patch  # or minor/major
```

## Release Process

### Publishing a New Version

1. **Prepare changes**
   ```bash
   git add .
   git commit -m "your changes"
   git push
   ```

2. **Create release**
   ```bash
   npm run version:patch  # 0.6.0 -> 0.6.1
   npm run version:minor  # 0.6.0 -> 0.7.0  
   npm run version:major  # 0.6.0 -> 1.0.0
   ```

3. **Monitor build** - Check GitHub Actions for automated macOS/Windows builds

## Tech Stack

- **Desktop:** Electron
- **Backend:** Python + Flask + WebSocket
- **Frontend:** Vue 3 + Element Plus + Monaco Editor

## Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Development server |
| Backend | 5002 | API service |
| WebSSH | 5001 | SSH terminal |
| ttyd | 7681 | Web terminal |

## Troubleshooting

**Port conflicts:**
```bash
npm run kill-ports  # Automatically kills conflicting ports
```

**Electron native module mismatch (e.g. `node-pty` ABI errors):**
```bash
npm run rebuild:native  # Rebuild native Node modules against the bundled Electron version
```

**Reset dependencies:**
```bash
rm -rf node_modules frontend/node_modules
npm run install-all
```

## License

Apache License 2.0 - see [LICENSE](LICENSE) file.
