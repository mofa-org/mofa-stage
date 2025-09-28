const { contextBridge, ipcRenderer } = require('electron');

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
  }
});

// 在页面加载完成时通知主进程
window.addEventListener('DOMContentLoaded', () => {
  console.log('MoFA Stage Desktop loaded');
});