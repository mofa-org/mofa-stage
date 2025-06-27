/**
 * 简单的文件/目录浏览器工具
 */

/**
 * 选择目录 - 由于浏览器安全限制，直接跳转到路径输入
 * @returns {Promise<string|null>} 返回选择的目录路径，如果取消则返回null
 */
export async function selectDirectory() {
  // 由于浏览器安全限制，无法获取真实的文件系统路径
  // 直接提示用户手动输入路径
  return await promptForPath('', '请输入目录的完整路径\n（例如：/Users/username/Documents/project 或 C:\\Users\\username\\Documents\\project）')
}

/**
 * 选择文件
 * @param {string} accept - 接受的文件类型
 * @returns {Promise<string|null>} 返回选择的文件路径，如果取消则返回null
 */
export async function selectFile(accept = '*/*') {
  return new Promise((resolve) => {
    try {
      // 创建隐藏的input元素
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = accept
      input.style.display = 'none'
      
      // 处理选择结果
      input.addEventListener('change', (event) => {
        const files = event.target.files
        if (files && files.length > 0) {
          const file = files[0]
          // 注意：由于安全限制，我们无法获取真实的文件系统路径
          // 这里返回文件名，实际应用中可能需要其他处理方式
          resolve(file.name)
        } else {
          resolve(null)
        }
        
        // 清理DOM
        document.body.removeChild(input)
      })
      
      // 处理取消选择
      input.addEventListener('cancel', () => {
        resolve(null)
        document.body.removeChild(input)
      })
      
      // 添加到DOM并触发选择
      document.body.appendChild(input)
      input.click()
      
    } catch (error) {
      console.error('Error selecting file:', error)
      resolve(null)
    }
  })
}

/**
 * 显示路径输入对话框（备用方案）
 * @param {string} currentPath - 当前路径
 * @param {string} title - 对话框标题
 * @returns {Promise<string|null>} 返回输入的路径，如果取消则返回null
 */
export async function promptForPath(currentPath = '', title = '请输入路径') {
  return new Promise((resolve) => {
    try {
      const path = prompt(title, currentPath)
      resolve(path && path.trim() !== '' ? path.trim() : null)
    } catch (error) {
      console.error('Error prompting for path:', error)
      resolve(null)
    }
  })
}

/**
 * 智能路径选择（直接使用输入框，提供更好的用户体验）
 * @param {string} currentPath - 当前路径
 * @param {string} pathType - 路径类型（用于提示）
 * @returns {Promise<string|null>} 返回选择的路径
 */
export async function smartSelectPath(currentPath = '', pathType = 'directory') {
  const pathTypeNames = {
    mofa_dir: 'MoFA 根目录',
    mofa_env_path: 'MoFA 虚拟环境路径',
    custom_agent_hub_path: 'Agent Hub 目录',
    custom_examples_path: 'Examples 目录'
  }
  
  const pathTypeName = pathTypeNames[pathType] || '目录'
  const title = `请输入${pathTypeName}的完整路径\n\n示例格式：\n• Linux/Mac: /Users/username/path/to/directory\n• Windows: C:\\Users\\username\\path\\to\\directory\n\n当前路径: ${currentPath || '（未设置）'}`
  
  return await promptForPath(currentPath, title)
}

export default {
  selectDirectory,
  selectFile,
  promptForPath,
  smartSelectPath
} 