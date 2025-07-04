/**
 * Agent 相关的 API 服务
 */
import axios from 'axios'

const API_URL = '/api'

export default {
  /**
   * 获取所有 agents 列表
   */
  getAllAgents() {
    return axios.get(`${API_URL}/agents/`)
  },

  /**
   * 获取指定 agent 的详细信息
   */
  getAgentDetails(agentName) {
    return axios.get(`${API_URL}/agents/${agentName}`)
  },

  /**
   * 创建新的 agent
   * @param {Object} agentData - Agent 数据
   * @param {string} agentData.name - Agent 名称
   * @param {string} [agentData.version='0.0.1'] - Agent 版本
   * @param {string} [agentData.authors='MoFA_Stage User'] - Agent 作者
   * @param {string} [agentData.agent_type='agent-hub'] - Agent 类型，'agent-hub' 或 'examples'
   */
  createAgent(agentData) {
    return axios.post(`${API_URL}/agents/`, agentData)
  },

  /**
   * 从已有 agent 复制创建新 agent
   * @param {string} sourceAgent - 源 Agent 名称
   * @param {string} targetAgent - 目标 Agent 名称
   * @param {string} [agentType=null] - Agent 类型，'agent-hub' 或 'examples'，如果为 null 则自动检测
   */
  copyAgent(sourceAgent, targetAgent, agentType = null) {
    return axios.post(`${API_URL}/agents/copy`, {
      source: sourceAgent,
      target: targetAgent,
      agent_type: agentType
    })
  },

  /**
   * 删除指定 agent
   */
  deleteAgent(agentName) {
    return axios.delete(`${API_URL}/agents/${agentName}`)
  },

  /**
   * 运行指定 agent
   */
  runAgent(agentName, timeout = 5) {
    return axios.post(`${API_URL}/agents/${agentName}/run`, { timeout })
  },

  /**
   * 停止正在运行的 agent
   */
  stopAgent(processId) {
    return axios.post(`${API_URL}/agents/stop/${processId}`)
  },

  /**
   * 获取 agent 运行日志
   */
  fetchAgentLogs(agentName) {
    return axios.get(`${API_URL}/agents/${agentName}/logs`)
  },
  
  /**
   * 获取正在运行的进程的输出
   */
  fetchProcessOutput(agentName) {
    return axios.get(`${API_URL}/agents/${agentName}/process-output`)
  },

  /**
   * 获取 agent 的所有文件
   */
  getAgentFiles(agentName, agentType = null) {
    const params = agentType ? { agent_type: agentType } : {}
    return axios.get(`${API_URL}/agents/${agentName}/files`, { params })
  },

  /**
   * 获取文件内容
   */
  getFileContent(agentName, filePath, agentType = null) {
    const params = agentType ? { agent_type: agentType } : {}
    return axios.get(`${API_URL}/agents/${agentName}/files/${filePath}`, { params })
  },

  /**
   * 更新文件内容
   */
  updateFileContent(agentName, filePath, content) {
    return axios.put(`${API_URL}/agents/${agentName}/files/${filePath}`, { content })
  },

  /**
   * 删除文件或文件夹
   */
  deleteFileOrFolder(agentName, filePath) {
    return axios.delete(`${API_URL}/agents/${agentName}/files/${filePath}`)
  },

  /**
   * 重命名文件或文件夹
   */
  renameFileOrFolder(agentName, filePath, newName) {
    return axios.post(`${API_URL}/agents/${agentName}/files/${filePath}/rename`, { 
      new_name: newName 
    })
  },

  /**
   * 获取所有可用的nodes列表
   */
  getAvailableNodes() {
    return axios.get(`${API_URL}/agents/available-nodes`)
  },

  /**
   * 基于选择的nodes和描述生成dataflow
   * @param {Array} selectedNodes - 选择的node名称列表
   * @param {string} flowDescription - flow的功能描述
   * @param {string} flowName - flow的名称
   */
  generateDataflow(selectedNodes, flowDescription, flowName) {
    return axios.post(`${API_URL}/agents/generate-dataflow`, {
      selected_nodes: selectedNodes,
      flow_description: flowDescription,
      flow_name: flowName
    })
  }
}
