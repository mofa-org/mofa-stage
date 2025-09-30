/**
 * API 配置
 */
export const API_BASE_URL = 'http://localhost:5002'

// 创建一个统一的fetch函数
export const apiFetch = (url, options = {}) => {
  const fullUrl = url.startsWith('/api') ? `${API_BASE_URL}${url}` : url
  return fetch(fullUrl, options)
}