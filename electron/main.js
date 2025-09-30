const { app, BrowserWindow, Menu, shell, dialog, session } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const net = require('net');

// 保持对窗口对象的全局引用
let mainWindow;
let splashWindow;
let backendProcess = null;
let backendPort = 5002;

const isDev = process.env.NODE_ENV === 'development';

// Relax Chromium's strict CORS checks so packaged builds can talk to local services
app.commandLine.appendSwitch('disable-features', 'OutOfBlinkCors');

// Cache flag to avoid registering duplicate webRequest listeners
let corsInterceptorRegistered = false;

function createSplashWindow() {
  if (splashWindow || isDev) {
    return;
  }

  splashWindow = new BrowserWindow({
    width: 300,
    height: 260,
    frame: false,
    resizable: false,
    show: false,
    transparent: false,
    alwaysOnTop: true,
    fullscreenable: false,
    skipTaskbar: true,
    backgroundColor: '#ffffff',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  const logoPath = path.join(__dirname, '..', 'assets', 'mofa-logo.png');
  const logoData = fs.existsSync(logoPath) ? fs.readFileSync(logoPath).toString('base64') : '';
  const logoSrc = logoData ? `data:image/png;base64,${logoData}` : '';

  const splashHtml = encodeURIComponent(`
    <style>
      body { margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #ffffff; color:#131a2c; display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; }
      img { width: 96px; height: 96px; margin-bottom: 18px; }
      .subtitle { font-size: 14px; letter-spacing: 0.4px; }
    </style>
    <body>
      ${logoSrc ? `<img src="${logoSrc}" alt="MoFA Stage" />` : '<div style="font-size:22px;font-weight:600;margin-bottom:18px;">MoFA Stage</div>'}
      <div class="subtitle">Loading…</div>
    </body>`);

  splashWindow.loadURL(`data:text/html;charset=UTF-8,${splashHtml}`);
  splashWindow.once('ready-to-show', () => splashWindow?.show());
}

function destroySplashWindow() {
  if (splashWindow) {
    splashWindow.close();
    splashWindow = null;
  }
}

function getConfiguredTtydPort() {
  try {
    const settingsPath = path.join(__dirname, '..', 'backend', 'settings.json');
    if (fs.existsSync(settingsPath)) {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
      if (settings && typeof settings.ttyd_port === 'number') {
        return settings.ttyd_port;
      }
    }
  } catch (error) {
    console.warn('Failed to read ttyd_port from settings.json:', error.message);
  }
  return 7681;
}

function registerTtydCorsInterceptor() {
  if (corsInterceptorRegistered || !session?.defaultSession) {
    return;
  }

  const ttydPort = getConfiguredTtydPort();
  const allowedPrefixes = [
    `http://localhost:${ttydPort}`,
    `http://127.0.0.1:${ttydPort}`
  ];

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const shouldPatch = allowedPrefixes.some((prefix) => details.url.startsWith(prefix));

    if (shouldPatch) {
      const responseHeaders = { ...details.responseHeaders };
      responseHeaders['Access-Control-Allow-Origin'] = ['*'];
      responseHeaders['Access-Control-Allow-Headers'] = ['*'];
      responseHeaders['Access-Control-Allow-Methods'] = ['GET, POST, PUT, DELETE, OPTIONS'];

      callback({ cancel: false, responseHeaders });
      return;
    }

    callback({ cancel: false, responseHeaders: details.responseHeaders });
  });

  corsInterceptorRegistered = true;
}

// 暴力杀掉指定端口的进程
function killPortsForce(ports = [3000, 5000, 5001, 5002]) {
  return new Promise((resolve) => {
    const portList = ports.join(',');
    
    // 根据平台选择命令
    let killCommand;
    if (process.platform === 'win32') {
      // Windows: 使用netstat和taskkill
      killCommand = `for /f "tokens=5" %a in ('netstat -aon ^| findstr ":${ports.join(' :')}"') do taskkill /f /pid %a 2>nul`;
    } else {
      // Unix/Linux/macOS: 使用lsof和kill
      killCommand = `lsof -ti:${portList} | xargs -r kill -9 2>/dev/null || true`;
    }
    
    console.log(`Force killing processes on ports: ${portList}`);
    exec(killCommand, (error, stdout, stderr) => {
      if (error) {
        console.log(`Port kill command completed with some errors (this is normal): ${error.message}`);
      }
      console.log(`Ports ${portList} have been cleared`);
      resolve();
    });
  });
}

// 检查端口是否可用
function checkPort(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(port, () => {
      server.once('close', () => resolve(true));
      server.close();
    });
    server.on('error', () => resolve(false));
  });
}

// 找到可用端口
async function findAvailablePort(startPort = 5002) {
  let port = startPort;
  while (!(await checkPort(port)) && port < startPort + 100) {
    port++;
  }
  return port;
}

// 启动Python后端
async function startBackend() {
  try {
    // 查找可用端口
    backendPort = await findAvailablePort();
    console.log(`Starting backend on port ${backendPort}`);

    let backendPath;
    if (isDev) {
      // 开发模式：直接运行Python脚本
      backendPath = path.join(__dirname, '..', 'backend', 'app.py');
      
      // 尝试不同的Python命令
      const pythonCommands = [
        '/opt/homebrew/opt/python@3.11/bin/python3.11',
        '/opt/homebrew/bin/python3',
        'python3',
        'python'
      ];
      
      let pythonCmd = 'python3'; // 默认值
      for (const cmd of pythonCommands) {
        try {
          require('child_process').execSync(`${cmd} --version`, { stdio: 'ignore' });
          pythonCmd = cmd;
          break;
        } catch (e) {
          continue;
        }
      }
      
      console.log(`Using Python: ${pythonCmd}`);
      backendProcess = spawn(pythonCmd, [backendPath, '--port', backendPort], {
        cwd: path.join(__dirname, '..', 'backend'),
        stdio: ['pipe', 'pipe', 'pipe']
      });
    } else {
      // 生产模式：运行打包的可执行文件
      const resourcesPath = process.resourcesPath || path.join(__dirname, '..');
      backendPath = path.join(resourcesPath, 'backend', 'app');
      
      // Windows下添加.exe扩展名
      if (process.platform === 'win32') {
        backendPath += '.exe';
      }
      
      if (!fs.existsSync(backendPath)) {
        throw new Error(`Backend executable not found: ${backendPath}`);
      }
      
      backendProcess = spawn(backendPath, ['--port', backendPort], {
        stdio: ['pipe', 'pipe', 'pipe']
      });
    }

    // 处理后端输出
    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend stdout: ${data}`);
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend stderr: ${data}`);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
      if (code !== 0 && mainWindow) {
        dialog.showErrorBox('Backend Error', 'Backend process crashed. Please restart the application.');
      }
    });

    // 不等待后端启动完成，让应用先显示界面
    console.log('Backend process started, continuing with app initialization...');
    
  } catch (error) {
    console.error('Failed to start backend:', error);
    dialog.showErrorBox('Startup Error', `Failed to start backend: ${error.message}`);
  }
}

// 等待后端服务可用
function waitForBackend(maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    
    const checkBackend = () => {
      attempts++;
      console.log(`Checking backend availability, attempt ${attempts}/${maxAttempts}`);
      
      // 使用HTTP请求检查而不是TCP连接
      const http = require('http');
      const req = http.get(`http://localhost:${backendPort}/`, (res) => {
        console.log('Backend is responding with status:', res.statusCode);
        resolve();
      });
      
      req.on('error', (error) => {
        console.log(`Backend check failed (${attempts}/${maxAttempts}):`, error.message);
        if (attempts >= maxAttempts) {
          reject(new Error('Backend failed to start within timeout'));
        } else {
          setTimeout(checkBackend, 1000);
        }
      });
      
      req.setTimeout(2000, () => {
        req.destroy();
        if (attempts >= maxAttempts) {
          reject(new Error('Backend failed to start within timeout'));
        } else {
          setTimeout(checkBackend, 1000);
        }
      });
    };
    
    checkBackend();
  });
}

// 停止后端进程
function stopBackend() {
  if (backendProcess) {
    console.log('Stopping backend process...');
    backendProcess.kill();
    backendProcess = null;
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    icon: path.join(__dirname, '..', 'assets', process.platform === 'darwin' ? 'icon.icns' : 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: false, // 允许跨域请求后端API
      preload: path.join(__dirname, 'preload.js')
    },
    show: false, // 先不显示，等加载完成后再显示
    titleBarStyle: 'default', // 使用默认标题栏，确保可以拖动窗口
    frame: true, // 强制显示窗口边框和标题栏
    titleBarOverlay: false, // 禁用标题栏覆盖
    backgroundColor: '#ffffff', // 设置窗口背景色为白色
    ...(process.platform === 'darwin' && {
      vibrancy: 'under-window', // macOS 毛玻璃效果
      visualEffectState: 'active'
    })
  });

  // 加载应用
  if (isDev) {
    // 开发模式：加载开发服务器
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式：加载打包的静态文件
    const indexPath = path.join(__dirname, '..', 'frontend', 'dist', 'index.html');
    console.log('Loading production file:', indexPath);
    
    // 检查文件是否存在
    if (fs.existsSync(indexPath)) {
      mainWindow.loadFile(indexPath);
    } else {
      console.error('Frontend index.html not found at:', indexPath);
      // 显示错误页面
      mainWindow.loadURL('data:text/html,<h1>Frontend files not found</h1><p>Path: ' + indexPath + '</p>');
    }
  }

  // 窗口准备好后显示
  mainWindow.once('ready-to-show', () => {
    destroySplashWindow();
    mainWindow.show();
    
    // 聚焦到窗口
    if (isDev) {
      mainWindow.focus();
    }
  });

  // 当窗口关闭时发出事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 处理外部链接
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });
}

// 创建应用菜单
function createMenu() {
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => {
            if (mainWindow) {
              mainWindow.reload();
            }
          }
        },
        {
          label: 'Toggle DevTools',
          accelerator: 'F12',
          click: () => {
            if (mainWindow) {
              mainWindow.webContents.toggleDevTools();
            }
          }
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'close' }
      ]
    }
  ];

  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    });
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// 应用事件处理
app.whenReady().then(async () => {
  console.log('Electron app is ready');

  registerTtydCorsInterceptor();
  
  // 暴力杀掉可能冲突的端口（生产模式下）
  if (!isDev) {
    console.log('Killing conflicting ports before startup...');
    createSplashWindow();
    try {
      await killPortsForce([3000, 5000, 5001, 5002]);
      await startBackend();

      try {
        console.log('Waiting for backend service to become available...');
        await waitForBackend(15);
        console.log('Backend is ready.');
      } catch (error) {
        console.error('Backend failed to respond in time:', error);
      }
    } finally {
      destroySplashWindow();
    }
  }
  
  // 创建窗口和菜单
  createWindow();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopBackend();
});

// 处理未捕获的异常
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  dialog.showErrorBox('Uncaught Exception', error.message);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
