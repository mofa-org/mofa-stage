const { contextBridge, ipcRenderer } = require('electron');

const terminalAPI = {
  isAvailable: async () => {
    try {
      return await ipcRenderer.invoke('terminal:available');
    } catch (error) {
      return false;
    }
  },
  getDefaultProfile: () => ipcRenderer.invoke('terminal:get-default-profile'),
  createSession: (options = {}) => ipcRenderer.invoke('terminal:create', options),
  write: (id, data) => {
    if (!id || typeof data !== 'string') {
      return;
    }
    ipcRenderer.send('terminal:write', { id, data });
  },
  resize: (id, cols, rows) => ipcRenderer.invoke('terminal:resize', { id, cols, rows }),
  close: (id) => ipcRenderer.invoke('terminal:close', { id }),
  listSessions: () => ipcRenderer.invoke('terminal:list-sessions'),
  onData: (callback) => {
    if (typeof callback !== 'function') {
      return () => {};
    }
    const channel = 'terminal:data';
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on(channel, listener);
    return () => ipcRenderer.removeListener(channel, listener);
  },
  onExit: (callback) => {
    if (typeof callback !== 'function') {
      return () => {};
    }
    const channel = 'terminal:exit';
    const listener = (_event, payload) => callback(payload);
    ipcRenderer.on(channel, listener);
    return () => ipcRenderer.removeListener(channel, listener);
  }
};

// 暴露受保护的方法给渲染器进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 获取平台信息
  platform: process.platform,
  
  // 版本信息
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron
  },
  
  // 是否为开发模式
  isDev: process.env.NODE_ENV === 'development',
  
  // 获取后端URL（将来可能需要动态获取）
  getBackendURL: () => {
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:5002' 
      : 'http://localhost:5002'; // 生产模式下也是本地端口
  },
  
  terminal: terminalAPI
});

// 在页面加载完成时通知主进程
window.addEventListener('DOMContentLoaded', () => {
  console.log('MoFA Stage Desktop loaded');
});
