const { app, ipcMain, webContents, dialog } = require('electron');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const sessions = new Map();
let handlersRegistered = false;
let ptyModule = null;
let ptyLoadError = null;
let loadWarningShown = false;

function loadPty() {
  if (ptyModule || ptyLoadError) {
    return ptyModule;
  }

  try {
    ptyModule = require('node-pty');
    return ptyModule;
  } catch (error) {
    ptyLoadError = error;
    console.error('Failed to load node-pty:', error);
    return null;
  }
}

function showPtyFailureDialog() {
  if (loadWarningShown || !ptyLoadError) {
    return;
  }
  loadWarningShown = true;

  const detail = [
    'Local terminal features require the native module "node-pty".',
    'Run "npm run rebuild:native" inside the project root to rebuild native dependencies.',
    '',
    `Original error: ${ptyLoadError.message}`
  ].join('\n');

  app
    .whenReady()
    .then(() => dialog.showMessageBox({
      type: 'error',
      title: 'Local Terminal Unavailable',
      message: 'node-pty failed to load. Local terminal features are disabled.',
      detail,
      buttons: ['OK']
    }))
    .catch(() => {});
}

function getDefaultShell(command) {
  if (command && typeof command === 'string') {
    return command;
  }

  if (process.platform === 'win32') {
    return process.env.COMSPEC || 'powershell.exe';
  }

  return process.env.SHELL || '/bin/bash';
}

function getDefaultCwd(requestedCwd) {
  if (requestedCwd && typeof requestedCwd === 'string' && requestedCwd.trim()) {
    return requestedCwd;
  }

  if (process.platform === 'win32') {
    return process.env.USERPROFILE || os.homedir();
  }

  return process.env.HOME || os.homedir();
}


function expandHomeDirectory(targetPath) {
  if (!targetPath || typeof targetPath !== 'string') {
    return targetPath;
  }

  if (targetPath === '~') {
    return os.homedir();
  }

  if (targetPath.startsWith('~/') || targetPath.startsWith('~\\')) {
    return path.join(os.homedir(), targetPath.slice(2));
  }

  return targetPath;
}

function normalizeCwd(cwd) {
  const expanded = expandHomeDirectory(cwd);
  if (!expanded) {
    return expanded;
  }

  try {
    return path.resolve(expanded);
  } catch (error) {
    return expanded;
  }
}



function sanitizeDimensions(value, fallback) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return fallback;
  }
  return Math.floor(numeric);
}

function sendToRenderer(sessionId, channel, payload) {
  const session = sessions.get(sessionId);
  if (!session) {
    return;
  }

  const target = webContents.fromId(session.webContentsId);
  if (target && !target.isDestroyed()) {
    target.send(channel, payload);
  }
}

function disposeSession(sessionId, reason = null) {
  const session = sessions.get(sessionId);
  if (!session) {
    return;
  }

  try {
    session.pty?.kill();
  } catch (error) {
    console.warn('Failed to terminate pty process:', error.message);
  }

  sessions.delete(sessionId);

  if (reason) {
    sendToRenderer(sessionId, 'terminal:exit', { id: sessionId, ...reason });
  }
}

function registerTerminalHandlers() {
  if (handlersRegistered) {
    return;
  }
  handlersRegistered = true;

  const pty = loadPty();

  if (!pty) {
    showPtyFailureDialog();

    ipcMain.handle('terminal:available', () => false);
    ipcMain.handle('terminal:get-default-profile', () => ({
      shell: getDefaultShell(),
      cwd: getDefaultCwd(),
      platform: process.platform,
      disabled: true
    }));

    ipcMain.handle('terminal:create', () => {
      throw new Error('Local terminal is unavailable. Please reinstall dependencies with "npm run rebuild:native".');
    });

    ipcMain.on('terminal:write', () => {});
    ipcMain.handle('terminal:resize', () => false);

    return;
  }

  ipcMain.handle('terminal:available', () => true);

  ipcMain.handle('terminal:get-default-profile', () => ({
    shell: getDefaultShell(),
    cwd: getDefaultCwd(),
    platform: process.platform
  }));

  ipcMain.handle('terminal:create', (event, options = {}) => {
    const shell = getDefaultShell(options.shellCommand);
    const cwd = normalizeCwd(getDefaultCwd(options.cwd));
    const cols = sanitizeDimensions(options.cols, 80);
    const rows = sanitizeDimensions(options.rows, 24);
    const env = Object.assign({}, process.env, options.env || {});
    const shellArgs = Array.isArray(options.shellArgs) ? options.shellArgs : [];

    const sessionId = crypto.randomUUID();

    try {
      const ptyProcess = pty.spawn(shell, shellArgs, {
        name: 'xterm-color',
        cols,
        rows,
        cwd,
        env
      });

      sessions.set(sessionId, {
        id: sessionId,
        pty: ptyProcess,
        shell,
        cwd,
        cols,
        rows,
        createdAt: Date.now(),
        webContentsId: event.sender.id
      });

      ptyProcess.onData((data) => {
        sendToRenderer(sessionId, 'terminal:data', { id: sessionId, data });
      });

      ptyProcess.onExit(({ exitCode, signal }) => {
        sendToRenderer(sessionId, 'terminal:exit', {
          id: sessionId,
          exitCode,
          signal
        });
        sessions.delete(sessionId);
      });

      return {
        id: sessionId,
        shell,
        cwd,
        cols,
        rows
      };
    } catch (error) {
      console.error('Failed to create terminal session:', error);
      throw new Error(error?.message || 'Unable to start local terminal');
    }
  });

  ipcMain.on('terminal:write', (_event, payload) => {
    const { id, data } = payload || {};
    if (!id || typeof data !== 'string') {
      return;
    }
    const session = sessions.get(id);
    if (!session) {
      return;
    }
    session.pty.write(data);
  });

  ipcMain.handle('terminal:resize', (_event, payload = {}) => {
    const { id, cols, rows } = payload;
    const session = sessions.get(id);
    if (!session) {
      return false;
    }
    try {
      session.pty.resize(Math.max(2, Math.floor(cols || 80)), Math.max(1, Math.floor(rows || 24)));
      return true;
    } catch (error) {
      console.warn('Failed to resize terminal session:', error.message);
      return false;
    }
  });

  ipcMain.handle('terminal:close', (_event, payload = {}) => {
    const { id } = payload;
    if (!id) {
      return false;
    }
    disposeSession(id);
    return true;
  });

  ipcMain.handle('terminal:list-sessions', () => {
    return Array.from(sessions.values()).map((session) => ({
      id: session.id,
      shell: session.shell,
      cwd: session.cwd,
      cols: session.cols,
      rows: session.rows,
      createdAt: session.createdAt
    }));
  });

  app.on('browser-window-created', (_event, window) => {
    const contentsId = window.webContents.id;
    window.on('closed', () => {
      for (const [id, session] of sessions.entries()) {
        if (session.webContentsId === contentsId) {
          disposeSession(id);
        }
      }
    });
  });
}

module.exports = {
  registerTerminalHandlers
};
