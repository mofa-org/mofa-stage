<template>
  <div 
    class="variable-monitor-window" 
    :style="windowStyle"
    v-show="visible"
  >
    <!-- 窗口头部 - 可拖拽区域 -->
    <div class="monitor-header" @mousedown="startDrag">
      <div class="header-left">
        <el-icon class="window-icon"><View /></el-icon>
        <span class="window-title">Variable Monitor</span>
      </div>
      <div class="header-controls">
        <el-button size="small" text @click="refreshVariables" :loading="isRefreshing" title="Refresh">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button size="small" text @click="clearWatch" title="Clear">
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button size="small" text @click="toggleMinimize" title="Minimize">
          <el-icon><Minus /></el-icon>
        </el-button>
        <el-button size="small" text @click="closeWindow" title="Close">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 窗口内容区域 -->
    <div class="monitor-content" v-show="!minimized">
      <!-- 添加监控表达式 -->
      <div class="add-watch-section">
        <el-input
          v-model="newWatchExpression"
          placeholder="Add watch expression (e.g., hello-world.query)..."
          size="small"
          @keyup.enter="addWatch"
        >
          <template #append>
            <el-button @click="addWatch" :disabled="!newWatchExpression.trim()">
              <el-icon><Plus /></el-icon>
            </el-button>
          </template>
        </el-input>
        <div class="quick-actions" style="margin-top: 8px;">
          <el-button size="small" @click="autoDiscoverVariables" :loading="isDiscovering">
            <el-icon><Search /></el-icon>
            Auto discover variables
          </el-button>
        </div>
      </div>

      <!-- 监控变量列表 -->
      <div class="watch-list">
        <div v-if="watchList.length === 0" class="empty-state">
          <el-empty description="No monitored variables yet" :image-size="50">
            <el-button type="primary" size="small" @click="addSampleWatch">
              Add sample monitors
            </el-button>
          </el-empty>
        </div>
        <div v-else class="watch-items">
          <div 
            v-for="(watch, index) in watchList" 
            :key="index"
            class="watch-item"
            :class="{ 'error': watch.error, 'changed': watch.changed }"
          >
            <div class="watch-expression">
              <el-icon class="watch-icon">
                <View v-if="!watch.error" />
                <Warning v-else />
              </el-icon>
              <span class="expression-text">{{ watch.expression }}</span>
              <el-button 
                size="small" 
                text 
                @click="removeWatch(index)"
                class="remove-btn"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
            <div class="watch-value">
              <span v-if="watch.error" class="error-value">{{ watch.error }}</span>
              <span v-else class="value-text" :title="watch.value">{{ formatValue(watch.value) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 监控窗口底部 -->
    <div class="monitor-footer" v-show="!minimized">
      <el-text size="small" type="info">
        Monitoring {{ watchList.length }} expressions
      </el-text>
    </div>

    <!-- 调整大小手柄 -->
    <div class="resize-handle" @mousedown="startResize" v-show="!minimized"></div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { Refresh, Delete, Plus, View, Warning, Close, Minus, Search } from '@element-plus/icons-vue'

export default {
  name: 'VariableMonitor',
  components: {
    Refresh,
    Delete,
    Plus,
    View,
    Warning,
    Close,
    Minus,
    Search
  },
  props: {
    // 窗口默认宽度和高度
    defaultWidth: {
      type: Number,
      default: 320
    },
    defaultHeight: {
      type: Number,
      default: 400
    },
    // 窗口默认位置
    defaultX: {
      type: Number,
      default: 100
    },
    defaultY: {
      type: Number,
      default: 100
    },
    // 是否显示窗口
    visible: {
      type: Boolean,
      default: true
    },
    // Agent信息
    agentName: {
      type: String,
      default: ''
    },
    agentType: {
      type: String,
      default: ''
    }
  },
  emits: ['close', 'minimize', 'position-change', 'size-change'],
  setup(props, { emit }) {
    // 窗口状态
    const x = ref(props.defaultX)
    const y = ref(props.defaultY)
    const width = ref(props.defaultWidth)
    const height = ref(props.defaultHeight)
    const minimized = ref(false)
    
    // 拖拽状态
    const isDragging = ref(false)
    const dragStartX = ref(0)
    const dragStartY = ref(0)
    const windowStartX = ref(0)
    const windowStartY = ref(0)
    
    // 调整大小状态
    const isResizing = ref(false)
    const resizeStartX = ref(0)
    const resizeStartY = ref(0)
    const resizeStartWidth = ref(0)
    const resizeStartHeight = ref(0)
    
    // 监控相关状态
    const newWatchExpression = ref('')
    const isRefreshing = ref(false)
    const isDiscovering = ref(false)
    const watchList = reactive([])

    // 计算窗口样式
    const windowStyle = computed(() => ({
      position: 'fixed',
      left: x.value + 'px',
      top: y.value + 'px',
      width: width.value + 'px',
      height: minimized.value ? 'auto' : height.value + 'px',
      zIndex: 1000
    }))

    // 开始拖拽窗口
    const startDrag = (event) => {
      // 防止在按钮上开始拖拽
      if (event.target.closest('.el-button') || event.target.closest('.header-controls')) {
        return
      }
      
      isDragging.value = true
      dragStartX.value = event.clientX
      dragStartY.value = event.clientY
      windowStartX.value = x.value
      windowStartY.value = y.value
      
      document.addEventListener('mousemove', handleDrag)
      document.addEventListener('mouseup', stopDrag)
      event.preventDefault()
    }

    // 处理拖拽
    const handleDrag = (event) => {
      if (!isDragging.value) return
      
      const deltaX = event.clientX - dragStartX.value
      const deltaY = event.clientY - dragStartY.value
      
      x.value = Math.max(0, Math.min(window.innerWidth - width.value, windowStartX.value + deltaX))
      y.value = Math.max(0, Math.min(window.innerHeight - 40, windowStartY.value + deltaY))
      
      emit('position-change', { x: x.value, y: y.value })
    }

    // 停止拖拽
    const stopDrag = () => {
      isDragging.value = false
      document.removeEventListener('mousemove', handleDrag)
      document.removeEventListener('mouseup', stopDrag)
    }

    // 开始调整大小
    const startResize = (event) => {
      isResizing.value = true
      resizeStartX.value = event.clientX
      resizeStartY.value = event.clientY
      resizeStartWidth.value = width.value
      resizeStartHeight.value = height.value
      
      document.addEventListener('mousemove', handleResize)
      document.addEventListener('mouseup', stopResize)
      event.preventDefault()
      event.stopPropagation()
    }

    // 处理调整大小
    const handleResize = (event) => {
      if (!isResizing.value) return
      
      const deltaX = event.clientX - resizeStartX.value
      const deltaY = event.clientY - resizeStartY.value
      
      width.value = Math.max(280, Math.min(800, resizeStartWidth.value + deltaX))
      height.value = Math.max(200, Math.min(600, resizeStartHeight.value + deltaY))
      
      emit('size-change', { width: width.value, height: height.value })
    }

    // 停止调整大小
    const stopResize = () => {
      isResizing.value = false
      document.removeEventListener('mousemove', handleResize)
      document.removeEventListener('mouseup', stopResize)
    }

    // 切换最小化状态
    const toggleMinimize = () => {
      minimized.value = !minimized.value
      emit('minimize', minimized.value)
    }

    // 关闭窗口
    const closeWindow = () => {
      emit('close')
    }

    // 添加监控表达式
    const addWatch = () => {
      const expression = newWatchExpression.value.trim()
      if (!expression) return
      
      const watch = {
        expression,
        value: null,
        error: null,
        changed: false
      }
      
      // TODO: 实际的变量求值逻辑
      evaluateWatch(watch)
      watchList.push(watch)
      newWatchExpression.value = ''
    }

    // 移除监控表达式
    const removeWatch = (index) => {
      watchList.splice(index, 1)
    }

    // 清空所有监控
    const clearWatch = () => {
      watchList.splice(0)
    }

    // 刷新所有变量
    const refreshVariables = async () => {
      isRefreshing.value = true
      try {
        for (const watch of watchList) {
          await evaluateWatch(watch)
        }
      } finally {
        isRefreshing.value = false
      }
    }

    // 添加示例监控
    const addSampleWatch = async () => {
      // 先尝试获取实际的节点信息
      const allVariables = await queryAllDuckDBVariables()
      const nodes = Object.keys(allVariables)
        .filter(key => key.includes('.'))
        .map(key => key.split('.')[0])
        .filter((node, index, arr) => arr.indexOf(node) === index)
      
      const sampleWatches = []
      
      if (nodes.length > 0) {
        // 如果有实际节点，使用实际的节点名
        const firstNode = nodes[0]
        sampleWatches.push(
          { expression: `${firstNode}.query`, value: null },
          { expression: `${firstNode}.output`, value: null },
          { expression: 'query', value: null },
          { expression: 'output', value: null }
        )
      } else {
        // 回退到通用示例
        sampleWatches.push(
          { expression: 'query', value: null },
          { expression: 'output', value: null },
          { expression: 'result', value: null }
        )
      }
      
      // 添加基础变量
      sampleWatches.push({ expression: 'window.location.href', value: window.location.href })
      
      // 添加示例监控项
      sampleWatches.forEach(sample => {
        watchList.push({
          ...sample,
          error: null,
          changed: false
        })
      })
      
      // 立即求值这些示例
      await refreshVariables()
    }

    // 求值监控表达式 - 集成DuckDB查询
    const evaluateWatch = async (watch) => {
      try {
        // 先处理一些基本的全局变量
        const basicValues = {
          'window.location.href': window.location.href,
          'document.title': document.title,
          'Date.now()': Date.now(),
          'Math.random()': Math.random()
        }
        
        if (basicValues.hasOwnProperty(watch.expression)) {
          const newValue = basicValues[watch.expression]
          watch.changed = watch.value !== null && watch.value !== newValue
          watch.value = newValue
          watch.error = null
          return
        }
        
        // 解析DuckDB查询表达式，格式: node_id.variable_name
        const duckdbMatch = watch.expression.match(/^([^.]+)\.(.+)$/)
        if (duckdbMatch) {
          const [, nodeId, variableName] = duckdbMatch
          const value = await queryDuckDBVariable(nodeId, variableName)
          
          if (value !== null) {
            watch.changed = watch.value !== null && JSON.stringify(watch.value) !== JSON.stringify(value)
            watch.value = value
            watch.error = null
          } else {
            watch.error = `Variable ${variableName} was not found in node ${nodeId}`
            watch.value = null
            watch.changed = false
          }
        } else {
          // 对于其他表达式，尝试从当前页面环境查询所有DuckDB变量
          const allVariables = await queryAllDuckDBVariables()
          if (allVariables[watch.expression]) {
            const newValue = allVariables[watch.expression]
            watch.changed = watch.value !== null && JSON.stringify(watch.value) !== JSON.stringify(newValue.value)
            watch.value = newValue.value
            watch.error = null
          } else {
            watch.value = 'Variable not found'
            watch.error = null
            watch.changed = false
          }
        }
      } catch (error) {
        watch.error = error.message
        watch.value = null
        watch.changed = false
      }
    }

    // 查询DuckDB中的特定变量
    const queryDuckDBVariable = async (nodeId, variableName) => {
      try {
        // 构建数据库文件路径（需要从当前环境获取）
        const currentPath = getCurrentDuckDBPath()
        if (!currentPath) return null
        
        const queryParam = encodeURIComponent(currentPath)
        const response = await fetch(`/api/agents/duckdb/file/node/${nodeId}/variables?path=${queryParam}`)
        const data = await response.json()
        
        if (data.success && data.variables[variableName]) {
          return data.variables[variableName].value
        }
        return null
      } catch (error) {
        console.error('Failed to query DuckDB variable:', error)
        return null
      }
    }

    // 查询所有DuckDB变量
    const queryAllDuckDBVariables = async () => {
      try {
        const currentPath = getCurrentDuckDBPath()
        if (!currentPath) return {}
        
        const queryParam = encodeURIComponent(currentPath)
        
        // 获取所有节点
        const nodesResponse = await fetch(`/api/agents/duckdb/file/nodes?path=${queryParam}`)
        const nodesData = await nodesResponse.json()
        
        const allVariables = {}
        
        if (nodesData.success) {
          // 为每个节点获取变量
          for (const node of nodesData.nodes) {
            const variablesResponse = await fetch(`/api/agents/duckdb/file/node/${node.node_name}/variables?path=${queryParam}`)
            const variablesData = await variablesResponse.json()
            
            if (variablesData.success) {
              // 添加节点前缀的变量名
              Object.keys(variablesData.variables).forEach(varName => {
                const key = `${node.node_name}.${varName}`
                allVariables[key] = variablesData.variables[varName]
                // 也添加不带节点前缀的版本（如果没有冲突）
                if (!allVariables[varName]) {
                  allVariables[varName] = variablesData.variables[varName]
                }
              })
            }
          }
        }
        
        return allVariables
      } catch (error) {
        console.error('Failed to query all DuckDB variables:', error)
        return {}
      }
    }

    // 获取当前DuckDB文件路径
    const getCurrentDuckDBPath = () => {
      // 使用传入的agent信息构建路径
      const agentName = props.agentName || window.location.pathname.split('/').pop() || 'hello_world'
      const agentType = props.agentType
      
      // 根据agent类型构建不同的路径
      if (agentType === 'examples') {
        return `/Users/liyao/Code/mofa/mofa_old/mofa/python/examples/${agentName}/logs.duckdb`
      } else if (agentType === 'custom') {
        // 自定义agent的路径逻辑
        return `/path/to/custom/agents/${agentName}/logs.duckdb`
      } else {
        // 默认路径构建逻辑
        return `/Users/liyao/Code/mofa/mofa_old/mofa/python/examples/${agentName}/logs.duckdb`
      }
    }

    // 自动发现变量
    const autoDiscoverVariables = async () => {
      isDiscovering.value = true
      try {
        // 清空现有监控
        watchList.splice(0)
        
        const allVariables = await queryAllDuckDBVariables()
        
        // 添加发现的变量到监控列表
        const addedVariables = new Set()
        Object.keys(allVariables).forEach(varName => {
          // 跳过重复的变量名（优先使用带节点前缀的）
          const simpleName = varName.split('.').pop()
          if (!varName.includes('.') && addedVariables.has(simpleName)) {
            return // 跳过不带前缀的版本
          }
          
          watchList.push({
            expression: varName,
            value: allVariables[varName].value,
            error: null,
            changed: false
          })
          
          addedVariables.add(simpleName)
        })
        
        // 如果没有找到变量，添加一些基本示例
        if (watchList.length === 0) {
          await addSampleWatch()
        }
        
      } catch (error) {
        console.error('Failed to auto-discover variables:', error)
      } finally {
        isDiscovering.value = false
      }
    }

    // 格式化显示值
    const formatValue = (value) => {
      if (value === null) return 'null'
      if (value === undefined) return 'undefined'
      if (typeof value === 'string') return `"${value}"`
      if (typeof value === 'object') return JSON.stringify(value, null, 2)
      return String(value)
    }

    // 组件挂载时的处理
    onMounted(() => {
      // 可以在这里初始化一些默认的监控表达式或连接调试器
    })

    // 组件卸载前清理
    onBeforeUnmount(() => {
      if (isResizing.value) {
        stopResize()
      }
      if (isDragging.value) {
        stopDrag()
      }
    })

    // 暴露方法给父组件
    const exposedMethods = {
      autoDiscoverVariables,
      refreshVariables,
      addWatch,
      clearWatch
    }

    return {
      windowStyle,
      minimized,
      newWatchExpression,
      isRefreshing,
      isDiscovering,
      watchList,
      startDrag,
      startResize,
      toggleMinimize,
      closeWindow,
      addWatch,
      removeWatch,
      clearWatch,
      refreshVariables,
      addSampleWatch,
      autoDiscoverVariables,
      formatValue,
      ...exposedMethods
    }
  }
}
</script>

<style scoped>
.variable-monitor-window {
  background-color: #fff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: none;
  transition: all 0.2s ease;
}

.variable-monitor-window:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.monitor-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  user-select: none;
}

.monitor-header:hover {
  background: linear-gradient(135deg, #f1f3f4 0%, #e2e5e8 100%);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.window-icon {
  color: var(--el-color-primary);
  font-size: 16px;
}

.window-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-controls {
  display: flex;
  gap: 2px;
}

.header-controls .el-button {
  padding: 4px;
  min-height: 24px;
  border: none;
}

.monitor-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.add-watch-section {
  padding: 8px;
  border-bottom: 1px solid var(--border-color);
}

.watch-list {
  flex: 1;
  overflow-y: auto;
}

.empty-state {
  padding: 20px 8px;
  text-align: center;
}

.watch-items {
  padding: 4px 0;
}

.watch-item {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  transition: background-color 0.2s ease;
}

.watch-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}

.watch-item.changed {
  background-color: rgba(255, 193, 7, 0.1);
  border-left: 3px solid #ffc107;
}

.watch-item.error {
  background-color: rgba(245, 108, 108, 0.1);
  border-left: 3px solid #f56c6c;
}

.watch-expression {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.watch-icon {
  font-size: 12px;
  color: var(--el-color-primary);
}

.expression-text {
  flex: 1;
  font-size: 12px;
  font-family: monospace;
  color: var(--el-color-info);
}

.remove-btn {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.watch-item:hover .remove-btn {
  opacity: 1;
}

.watch-value {
  padding-left: 18px;
  font-size: 12px;
  font-family: monospace;
}

.value-text {
  color: var(--el-text-color-primary);
  word-break: break-all;
}

.error-value {
  color: var(--el-color-danger);
  font-style: italic;
}

.monitor-footer {
  padding: 6px 12px;
  border-top: 1px solid var(--border-color);
  text-align: center;
  background-color: #fafafa;
}

.resize-handle {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  cursor: nw-resize;
  background: linear-gradient(-45deg, transparent 40%, #ccc 40%, #ccc 50%, transparent 50%);
  background-size: 3px 3px;
}

.resize-handle:hover {
  background: linear-gradient(-45deg, transparent 40%, #999 40%, #999 50%, transparent 50%);
  background-size: 3px 3px;
}

/* 自定义滚动条样式 */
.watch-list::-webkit-scrollbar {
  width: 6px;
}

.watch-list::-webkit-scrollbar-track {
  background: transparent;
}

.watch-list::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.watch-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}
</style>
