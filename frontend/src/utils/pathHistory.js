/**
 * 路径历史记录管理工具
 */

const MAX_HISTORY_COUNT = 5

export class PathHistory {
  /**
   * 获取指定类型的路径历史记录
   * @param {string} pathType - 路径类型 (mofa_dir, agent_hub_path, examples_path, etc.)
   * @returns {Array} 路径历史记录数组
   */
  static getHistory(pathType) {
    try {
      const key = `path_history_${pathType}`
      const history = localStorage.getItem(key)
      return history ? JSON.parse(history) : []
    } catch (error) {
      console.error('Error reading path history:', error)
      return []
    }
  }

  /**
   * 添加新路径到历史记录
   * @param {string} pathType - 路径类型
   * @param {string} newPath - 新路径
   */
  static addToHistory(pathType, newPath) {
    if (!newPath || newPath.trim() === '') {
      return
    }

    try {
      const key = `path_history_${pathType}`
      let history = this.getHistory(pathType)
      
      // 移除已存在的相同路径
      history = history.filter(path => path !== newPath)
      
      // 将新路径添加到开头
      history.unshift(newPath)
      
      // 限制历史记录数量
      if (history.length > MAX_HISTORY_COUNT) {
        history = history.slice(0, MAX_HISTORY_COUNT)
      }
      
      localStorage.setItem(key, JSON.stringify(history))
    } catch (error) {
      console.error('Error saving path history:', error)
    }
  }

  /**
   * 清除指定类型的路径历史记录
   * @param {string} pathType - 路径类型
   */
  static clearHistory(pathType) {
    try {
      const key = `path_history_${pathType}`
      localStorage.removeItem(key)
    } catch (error) {
      console.error('Error clearing path history:', error)
    }
  }

  /**
   * 获取所有支持的路径类型
   */
  static getSupportedPathTypes() {
    return [
      'mofa_dir',
      'mofa_env_path', 
      'agent_hub_path',
      'examples_path',
      'custom_agent_hub_path',
      'custom_examples_path'
    ]
  }

  /**
   * 清除所有路径历史记录
   */
  static clearAllHistory() {
    this.getSupportedPathTypes().forEach(pathType => {
      this.clearHistory(pathType)
    })
  }

  /**
   * 获取路径建议（历史记录 + 智能推荐）
   * @param {string} pathType - 路径类型
   * @param {string} currentInput - 当前输入值
   * @param {Object} context - 上下文信息（如mofa_dir）
   * @returns {Array} 建议路径数组
   */
  static getPathSuggestions(pathType, currentInput = '', context = {}) {
    const history = this.getHistory(pathType)
    let suggestions = [...history]

    // 根据路径类型添加智能建议
    if (context.mofa_dir && pathType === 'custom_agent_hub_path') {
      const agentHubSuggestion = context.mofa_dir + '/python/agent-hub'
      if (!suggestions.includes(agentHubSuggestion)) {
        suggestions.push(agentHubSuggestion)
      }
    }

    if (context.mofa_dir && pathType === 'custom_examples_path') {
      const examplesSuggestion = context.mofa_dir + '/python/examples'
      if (!suggestions.includes(examplesSuggestion)) {
        suggestions.push(examplesSuggestion)
      }
    }

    // 如果有输入值，进行模糊匹配过滤
    if (currentInput && currentInput.trim() !== '') {
      const input = currentInput.toLowerCase()
      suggestions = suggestions.filter(path => 
        path.toLowerCase().includes(input)
      )
    }

    return suggestions.slice(0, MAX_HISTORY_COUNT)
  }
}

export default PathHistory 