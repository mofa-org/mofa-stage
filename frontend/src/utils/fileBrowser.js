/**
 * 简单的文件/目录浏览器工具
 */
import { ElMessageBox, ElMessage } from 'element-plus'

/**
 * 选择目录
 * @param {Object} options
 * @param {string} [options.defaultPath]
 * @param {string} [options.title]
 * @param {boolean} [options.allowMultiple=false]
 * @param {string} [options.fallbackTitle]
 * @returns {Promise<string|string[]|null>}
 */
export async function selectDirectory({
  defaultPath = '',
  title = 'Select Directory',
  allowMultiple = false,
  fallbackTitle
} = {}) {
  if (window?.electronAPI?.dialog?.selectDirectory) {
    try {
      const result = await window.electronAPI.dialog.selectDirectory({
        defaultPath: defaultPath || undefined,
        title,
        allowMultiple
      })

      if (result) {
        return allowMultiple ? result : result
      }

      return allowMultiple ? [] : null
    } catch (error) {
      console.error('Native directory selection failed:', error)
    }
  }

  const promptTitle = fallbackTitle || 'Enter the full directory path\n(e.g., /Users/username/Documents/project or C:\\Users\\username\\Documents\\project)'
  const promptResult = await promptForPath(defaultPath, {
    title: 'Select Directory',
    message: promptTitle,
    placeholder: defaultPath || '/Users/username/path/to/directory'
  })
  return allowMultiple ? (promptResult ? [promptResult] : []) : promptResult
}

/**
 * 选择文件
 * @param {string} accept - 接受的文件类型
 * @returns {Promise<string|null>} 返回选择的文件路径，如果取消则返回null
 */
export async function selectFile({
  accept = '*/*',
  title = 'Select File',
  allowMultiple = false
} = {}) {
  if (window?.electronAPI?.dialog?.selectFile) {
    try {
      const filters = []
      if (accept && accept !== '*/*') {
        const extensions = accept
          .split(',')
          .map((item) => item.trim())
          .map((token) => (token.startsWith('.') ? token.slice(1) : token))
          .filter((token) => token && !token.includes('/'))
        if (extensions.length > 0) {
          filters.push({ name: 'Custom Files', extensions })
        }
      }

      const result = await window.electronAPI.dialog.selectFile({
        filters,
        title,
        allowMultiple
      })
      if (result) {
        return allowMultiple ? result : result
      }
      return allowMultiple ? [] : null
    } catch (error) {
      console.error('Native file selection failed:', error)
    }
  }

  return await new Promise((resolve) => {
    try {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = accept
      input.style.display = 'none'

      input.addEventListener('change', (event) => {
        const files = event.target.files
        if (!files || files.length === 0) {
          resolve(allowMultiple ? [] : null)
        } else if (allowMultiple) {
          resolve(Array.from(files).map((file) => file.name))
        } else {
          resolve(files[0].name)
        }
        document.body.removeChild(input)
      })

      input.addEventListener('cancel', () => {
        resolve(allowMultiple ? [] : null)
        document.body.removeChild(input)
      })

      document.body.appendChild(input)
      input.click()
    } catch (error) {
      console.error('Error selecting file:', error)
      resolve(allowMultiple ? [] : null)
    }
  })
}

/**
 * 显示路径输入对话框（备用方案）
 * @param {string} currentPath - 当前路径
 * @param {string} title - 对话框标题
 * @returns {Promise<string|null>} 返回输入的路径，如果取消则返回null
 */
export async function promptForPath(currentPath = '', options = {}) {
  const {
    title = 'Enter a path',
    message = 'Enter the full path',
    placeholder = '/path/to/target',
    confirmButtonText = 'Confirm',
    cancelButtonText = 'Cancel'
  } = typeof options === 'string' ? { message: options } : options

  try {
    const { value } = await ElMessageBox.prompt(message, title, {
      confirmButtonText,
      cancelButtonText,
      inputValue: currentPath,
      inputPlaceholder: placeholder,
      closeOnClickModal: false,
      showClose: true,
      customClass: 'mofa-dialog',
      confirmButtonClass: 'mofa-dialog__confirm',
      cancelButtonClass: 'mofa-dialog__cancel'
    })

    const trimmed = value?.trim()
    return trimmed ? trimmed : null
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return null
    }
    console.error('Error prompting for path:', error)
    ElMessage.error('Path selection failed. Please try again.')
    return null
  }
}

/**
 * 智能路径选择（直接使用输入框，提供更好的用户体验）
 * @param {string} currentPath - 当前路径
 * @param {string} pathType - 路径类型（用于提示）
 * @returns {Promise<string|null>} 返回选择的路径
 */
export async function smartSelectPath(currentPath = '', pathType = 'directory') {
  const pathTypeNames = {
    mofa_dir: 'MoFA root directory',
    mofa_env_path: 'MoFA virtual environment path',
    custom_agent_hub_path: 'Agent Hub directory',
    custom_examples_path: 'Examples directory'
  }
  
  const pathTypeName = pathTypeNames[pathType] || 'directory'
  
  if (window?.electronAPI?.dialog?.selectDirectory) {
    try {
      const selected = await window.electronAPI.dialog.selectDirectory({
        defaultPath: currentPath || undefined,
        title: `Select ${pathTypeName}`
      })

      if (Array.isArray(selected)) {
        return selected[0] || null
      }

      if (selected) {
        return selected
      }
    } catch (error) {
      console.error('Native smartSelectPath failed:', error)
    }
  }

  const title = `Enter the full path for ${pathTypeName}\n\nExamples:\n• Linux/Mac: /Users/username/path/to/directory\n• Windows: C:\\Users\\username\\path\\to\\directory\n\nCurrent path: ${currentPath || '(not set)'}`
  return await promptForPath(currentPath, {
    title: 'Manual Path Entry',
    message: title,
    placeholder: currentPath || '/Users/username/path/to/directory'
  })
}

export default {
  selectDirectory,
  selectFile,
  promptForPath,
  smartSelectPath
} 
