# MoFA Stage Desktop

English | [中文](README_cn.md)

MoFA Stage Desktop is an Electron-based desktop application for managing and editing Nodes and Dataflows in the MoFA framework, providing a unified development platform with embedded services.

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

- **Desktop Integration**
  - Cross-platform support (Windows, macOS, Linux)
  - Single installation package
  - Embedded Python backend
  - No environment configuration required

## Technology Stack

**Desktop Framework**
- Electron for cross-platform desktop application

**Backend**
- Python + Flask
- WebSocket support
- SSH terminal integration
- RESTful API

**Frontend**
- Vue 3 + Element Plus
- Monaco editor

**Third-party Services**
- ttyd (recommended)
- code-server (optional)

## Project Structure

```
mofa-stage-desktop/
├── electron/           # Electron main process code
│   ├── main.js        # Main process entry
│   └── preload.js     # Preload script
├── frontend/          # Vue.js frontend code
├── backend/           # Flask backend code
├── scripts/           # Build scripts
├── assets/            # Application icons and resources
└── dist/              # Build output directory
```

## Quick Start

### For End Users

**Method 1: Download Release Package (Recommended)**

1. Download the appropriate installer from the releases page
   - Windows: `.exe` installer
   - macOS: `.dmg` package
   - Linux: `AppImage` file

2. Install and run the application
   - No additional setup required
   - Python environment is embedded

**Method 2: Build from Source**

```bash
# Clone the repository
git clone https://github.com/mofa-org/mofa-stage-desktop.git
cd mofa-stage-desktop

# Install dependencies
npm install
cd frontend && npm install
cd ../backend && pip install -r requirements.txt

# Build and package
npm run build
npm run dist
```

### For Developers

#### Environment Requirements

**System Support**
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 18.04+ or equivalent)

**Software Requirements**
- Node.js 18 or higher
- Python 3.8 or higher
- npm or yarn

#### Development Setup

1. **Clone and install dependencies**
   ```bash
   git clone https://github.com/mofa-org/mofa-stage-desktop.git
   cd mofa-stage-desktop
   
   # Install root dependencies
   npm install
   
   # Install frontend dependencies
   cd frontend
   npm install
   
   # Install backend dependencies
   cd ../backend
   pip install -r requirements.txt
   cd ..
   ```

2. **Development mode**
   ```bash
   npm run dev
   ```
   This command will:
   - Start the backend Flask server
   - Start the frontend development server
   - Launch Electron in development mode

3. **Individual services**
   ```bash
   # Start only backend
   npm run backend:dev
   
   # Start only frontend
   npm run frontend:dev
   ```

#### Build and Package

1. **Build for production**
   ```bash
   npm run build
   ```
   This will:
   - Build the frontend application
   - Package the Python backend using PyInstaller

2. **Create distributable packages**
   ```bash
   npm run dist
   ```
   Generates platform-specific installers in the `dist/` directory

## System Requirements

### For End Users
- Memory: Minimum 4GB, recommended 8GB+
- Storage: Minimum 500MB available space
- Operating System:
  - Windows 10/11
  - macOS 10.15+
  - Ubuntu 18.04+ or equivalent Linux distribution

### For Developers
- Node.js 18 or higher
- Python 3.8 or higher
- npm or yarn
- Git (for version control)

## Development Guide

### Available Scripts

- `npm run dev` - Start development server (frontend + backend + Electron)
- `npm run frontend:dev` - Start only frontend development server
- `npm run backend:dev` - Start only backend server
- `npm run frontend:build` - Build frontend for production
- `npm run backend:build` - Package backend using PyInstaller
- `npm run build` - Build both frontend and backend
- `npm run dist` - Create distributable desktop packages

### Debugging

1. **Enable Developer Tools**
   - Press `F12` or select "Toggle DevTools" from menu

2. **View Backend Logs**
   - Backend logs are displayed in Electron main process console

3. **Reload Application**
   - Press `Ctrl+R` (Windows/Linux) or `Cmd+R` (macOS)

### Backend Packaging

The backend is packaged using PyInstaller to create a standalone executable:

```bash
python scripts/build_backend.py
```

This script will:
- Use PyInstaller to bundle the Flask application
- Include all necessary dependencies
- Create a single executable file
- Handle platform-specific requirements

### Desktop Application Packaging

Use electron-builder to create platform-specific packages:

```bash
npm run electron:pack  # Create package without installer
npm run dist          # Create installer/distributable
```

#### Package Output

After running `npm run dist`, you'll find platform-specific packages in the `dist/` directory:

- **Windows**: `.exe` installer and unpacked application
- **macOS**: `.dmg` disk image and `.app` bundle
- **Linux**: `AppImage` portable application

## Common Issues

### Port Conflicts

The application automatically finds available ports starting from the default values:

| Service | Default Port | Description |
|---------|--------------|-------------|
| Backend API | 5002 | Flask main service |
| WebSSH | 5001 | SSH terminal service |
| Frontend (dev) | 3000 | Development server |
| ttyd | 7681 | Web terminal |

If you encounter port conflicts, the application will automatically search for available ports.

### Python Dependencies

Ensure all dependencies from `requirements.txt` are installed:

```bash
cd backend
pip install -r requirements.txt
```

### Frontend Build Issues

If frontend build fails:

```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### Application Startup

First startup may take longer as the backend initializes. The application will:
1. Start the Python backend service
2. Initialize the frontend
3. Launch the Electron window

### Platform-Specific Issues

**Windows**
- Ensure Python is in PATH
- Some antivirus software may flag the packaged executable

**macOS**
- You may need to allow the application in Security & Privacy settings
- Gatekeeper may require manual approval for first launch

**Linux**
- Ensure necessary libraries are installed
- AppImage may require executable permissions: `chmod +x MoFA-Stage-Desktop.AppImage`

## Port Description

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Web interface (development) |
| Backend API | 5002 | Flask service |
| WebSSH | 5001 | SSH terminal |
| ttyd | 7681 | Web terminal |
| VS Code | 8080 | Code editor (if enabled) |

## Troubleshooting

### Release Port Conflicts

If you encounter port occupation issues, use this command to release ports:

```bash
for port in 3000 5001 5002 7681; do
    pid=$(lsof -t -i:$port)
    if [ -n "$pid" ]; then
        kill -9 $pid
        echo "Released port $port"
    fi
done
```

### Check Service Status

1. **Check if backend is running**
   ```bash
   curl http://localhost:5002/api/system/info
   ```

2. **Check frontend connection**
   ```bash
   curl http://localhost:3000
   ```

3. **View application logs**
   - Open Developer Tools in the application
   - Check Console tab for frontend logs
   - Backend logs appear in the terminal running the application

## Release Process

### Automated Release with GitHub Actions

The project uses GitHub Actions for automated building and releasing of desktop applications.

#### Publishing a New Version

**Step 1: Prepare and push changes**
```bash
# Add and commit your changes
git add .
git commit -m "your commit message"
git push
```

**Step 2: Create a release version**
```bash
# For patch version (e.g., 0.6.0 -> 0.6.1)
npm run version:patch

# For minor version (e.g., 0.6.0 -> 0.7.0)  
npm run version:minor

# For major version (e.g., 0.6.0 -> 1.0.0)
npm run version:major
```

**Step 3: Monitor the build**
- GitHub Actions will automatically trigger when a new tag is pushed
- Check the "Actions" tab in your GitHub repository
- The workflow will build for both macOS (.dmg) and Windows (.exe)
- Upon successful completion, releases will be published to GitHub Releases

#### Manual Release (Alternative)

If you prefer manual control:

```bash
# 1. Update version in package.json manually
# 2. Commit changes
git add .
git commit -m "release: bump version to vX.X.X"
git push

# 3. Create and push tag
git tag vX.X.X
git push --tags
```

#### Build Outputs

The automated build process creates:
- **macOS**: `.dmg` installer package
- **Windows**: `.exe` installer package  
- **Artifacts**: Available for download from GitHub Actions

#### Release Notes

After the automated build completes:
1. Go to the GitHub Releases page
2. Edit the auto-generated release
3. Add release notes and descriptions
4. Mark as pre-release if needed

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Electron](https://electronjs.org/) - Cross-platform desktop application framework
- [Vue.js](https://vuejs.org/) - Progressive JavaScript framework
- [Flask](https://flask.palletsprojects.com/) - Python micro-framework
- [MoFA](https://github.com/mofa-org/mofa) - AI Agent framework