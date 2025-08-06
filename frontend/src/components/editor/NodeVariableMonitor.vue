<template>
  <div 
    class="node-variable-monitor-window" 
    :style="windowStyle"
    v-show="visible"
  >
    <!-- 窗口头部 - 可拖拽区域 -->
    <div class="monitor-header" @mousedown="startDrag">
      <div class="header-left">
        <el-icon class="window-icon"><Box /></el-icon>
        <span class="window-title">{{ nodeInfo.id || 'Node Monitor' }}</span>
        <el-tag size="small" type="info" v-if="nodeInfo.type">{{ nodeInfo.type }}</el-tag>
      </div>
      <div class="header-controls">
        <el-button size="small" text @click="refreshVariables" :loading="isRefreshing" title="刷新">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button size="small" text @click="clearWatch" title="清空">
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button size="small" text @click="showNodeStats" title="节点统计">
          <el-icon><DataAnalysis /></el-icon>
        </el-button>
        <el-button size="small" text @click="toggleMinimize" title="最小化">
          <el-icon><Minus /></el-icon>
        </el-button>
        <el-button size="small" text @click="closeWindow" title="关闭">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 窗口内容区域 -->
    <div class="monitor-content" v-show="!minimized">
      <!-- 节点信息概览 -->
      <div class="node-overview">
        <div class="info-section" v-if="nodeInfo.inputs && nodeInfo.inputs.length">
          <div class="section-title">
            <el-icon><Download /></el-icon>
            <span>输入变量</span>
          </div>
          <div class="variable-tags">
            <el-tag 
              v-for="input in nodeInfo.inputs" 
              :key="input" 
              size="small" 
              type="success"
              @click="addWatchForVariable(input)"
              class="clickable-tag"
            >
              {{ input }}
            </el-tag>
          </div>
        </div>
        
        <div class="info-section" v-if="nodeInfo.outputs && nodeInfo.outputs.length">
          <div class="section-title">
            <el-icon><Upload /></el-icon>
            <span>输出变量</span>
          </div>
          <div class="variable-tags">
            <el-tag 
              v-for="output in nodeInfo.outputs" 
              :key="output" 
              size="small" 
              type="warning"
              @click="addWatchForVariable(output)"
              class="clickable-tag"
            >
              {{ output }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 添加监控表达式 -->
      <div class="add-watch-section">
        <el-input
          v-model="newWatchExpression"
          placeholder="添加监控表达式..."
          size="small"
          @keyup.enter="addWatch"
        >
          <template #append>
            <el-button @click="addWatch" :disabled="!newWatchExpression.trim()">
              <el-icon><Plus /></el-icon>
            </el-button>
          </template>
        </el-input>
      </div>

      <!-- 监控变量列表 -->
      <div class="watch-list">
        <div v-if="watchList.length === 0" class="empty-state">
          <el-empty description="点击上方变量标签或添加表达式开始监控" :image-size="50">
            <el-button type="primary" size="small" @click="addNodeVariableWatches">
              监控所有节点变量
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
        节点: {{ nodeInfo.id }} | 监控 {{ watchList.length }} 个表达式
      </el-text>
    </div>

    <!-- 调整大小手柄 -->
    <div class="resize-handle" @mousedown="startResize" v-show="!minimized"></div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { Refresh, Delete, Plus, View, Warning, Close, Minus, Box, Download, Upload, DataAnalysis } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'NodeVariableMonitor',
  components: {
    Refresh,
    Delete,
    Plus,
    View,
    Warning,
    Close,
    Minus,
    Box,
    Download,
    Upload,
    DataAnalysis
  },
  props: {
    // 节点信息
    nodeInfo: {
      type: Object,
      default: () => ({
        id: '',
        type: '',
        inputs: [],
        outputs: []
      })
    },
    // 窗口配置
    windowConfig: {
      type: Object,
      required: true
    },
    // 是否显示窗口
    visible: {
      type: Boolean,
      default: true
    }
  },
  emits: ['close', 'minimize', 'position-change', 'size-change'],
  setup(props, { emit }) {
    console.log('NodeVariableMonitor setup called with props:', props)
    
    // 窗口状态
    const x = ref(props.windowConfig.x || 100)
    const y = ref(props.windowConfig.y || 100)
    const width = ref(props.windowConfig.width || 350)
    const height = ref(props.windowConfig.height || 450)
    const minimized = ref(props.windowConfig.minimized || false)
    const zIndex = ref(props.windowConfig.zIndex || 1000)
    
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
    const watchList = reactive([])

    // 计算窗口样式
    const windowStyle = computed(() => ({
      position: 'fixed',
      left: x.value + 'px',
      top: y.value + 'px',
      width: width.value + 'px',
      height: minimized.value ? 'auto' : height.value + 'px',
      zIndex: zIndex.value
    }))

    // 开始拖拽窗口
    const startDrag = (event) => {
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
      
      emit('position-change', props.nodeInfo.id, { x: x.value, y: y.value })
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
      
      width.value = Math.max(300, Math.min(800, resizeStartWidth.value + deltaX))
      height.value = Math.max(250, Math.min(600, resizeStartHeight.value + deltaY))
      
      emit('size-change', props.nodeInfo.id, { width: width.value, height: height.value })
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
      emit('minimize', props.nodeInfo.id, minimized.value)
    }

    // 关闭窗口
    const closeWindow = () => {
      emit('close', props.nodeInfo.id)
    }

    // 显示节点统计信息
    const showNodeStats = async () => {
      try {
        const response = await fetch(`/api/agents/duckdb/node/${props.nodeInfo.id}/variables`)
        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            const variables = data.variables
            const varNames = Object.keys(variables)
            const message = `节点 ${props.nodeInfo.id} 统计信息:\n` +
                          `• 总变量数: ${varNames.length}\n` +
                          `• 输入变量: ${varNames.filter(name => variables[name].type === 'input').length}\n` +
                          `• 输出变量: ${varNames.filter(name => variables[name].type === 'output').length}\n` +
                          `• 最后活动: ${Math.max(...varNames.map(name => variables[name].time))}`
            
            // 使用Element Plus的消息提示
            ElMessage.info({
              message: message.replace(/\n/g, '<br>'),
              dangerouslyUseHTMLString: true,
              duration: 5000
            })
          }
        }
      } catch (error) {
        ElMessage.error('获取节点统计信息失败')
      }
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
      
      evaluateWatch(watch)
      watchList.push(watch)
      newWatchExpression.value = ''
    }

    // 为特定变量添加监控
    const addWatchForVariable = (variableName) => {
      // 检查是否已存在
      const exists = watchList.some(watch => watch.expression === variableName)
      if (exists) return
      
      const watch = {
        expression: variableName,
        value: null,
        error: null,
        changed: false
      }
      
      evaluateWatch(watch)
      watchList.push(watch)
    }

    // 添加所有节点变量的监控
    const addNodeVariableWatches = () => {
      const allVariables = [...(props.nodeInfo.inputs || []), ...(props.nodeInfo.outputs || [])]
      allVariables.forEach(variable => {
        addWatchForVariable(variable)
      })
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

    // 从DuckDB获取节点变量的实际值
    const fetchVariableFromDuckDB = async (nodeId, variableName) => {
      try {
        // 调用后端API查询DuckDB中的最新数据
        const response = await fetch(`/api/agents/duckdb/latest/${nodeId}/${variableName}`)
        if (response.ok) {
          const data = await response.json()
          return data.success ? data.value : null
        }
      } catch (error) {
        console.warn(`Failed to fetch variable ${variableName} for node ${nodeId} from DuckDB:`, error)
      }
      return null
    }

    // 求值监控表达式 (集成DuckDB数据)
    const evaluateWatch = async (watch) => {
      try {
        let newValue = null
        
        // 首先尝试从DuckDB获取实际的节点变量值
        const dbValue = await fetchVariableFromDuckDB(props.nodeInfo.id, watch.expression)
        if (dbValue !== null) {
          newValue = dbValue
        } else {
          // 如果DuckDB中没有数据，使用模拟数据作为后备
          const mockNodeVariables = {
            'num1': Math.floor(Math.random() * 100),
            'num2': Math.floor(Math.random() * 100),
            'add_numbers_result': 150,
            'multiply_numbers_result': 2500,
            'terminal-input': 'Hello World'
          }
          
          if (mockNodeVariables.hasOwnProperty(watch.expression)) {
            newValue = mockNodeVariables[watch.expression]
          } else {
            // 对于未知变量，尝试作为JavaScript表达式求值
            try {
              newValue = eval(watch.expression)
            } catch (evalError) {
              newValue = '未定义'
            }
          }
        }
        
        // 检测值是否变化
        watch.changed = watch.value !== null && watch.value !== newValue
        watch.value = newValue
        watch.error = null
        
      } catch (error) {
        watch.error = error.message
        watch.value = null
        watch.changed = false
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
      // 可以在这里自动添加节点相关的默认监控
      if (props.nodeInfo.inputs && props.nodeInfo.inputs.length > 0) {
        // 自动监控第一个输入变量作为示例
        addWatchForVariable(props.nodeInfo.inputs[0])
      }
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

    return {
      windowStyle,
      minimized,
      newWatchExpression,
      isRefreshing,
      watchList,
      startDrag,
      startResize,  
      toggleMinimize,
      closeWindow,
      addWatch,
      addWatchForVariable,
      addNodeVariableWatches,
      removeWatch,
      clearWatch,
      refreshVariables,
      showNodeStats,
      formatValue
    }
  }
}
</script>

<style scoped>
.node-variable-monitor-window {
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

.node-variable-monitor-window:hover {
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.monitor-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: move;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  user-select: none;
}

.monitor-header:hover {
  background: linear-gradient(135deg, #d1e7dd 0%, #a3d5d9 100%);
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

.node-overview {
  padding: 8px;
  border-bottom: 1px solid var(--border-color);
  background-color: #fafafa;
}

.info-section {
  margin-bottom: 8px;
}

.info-section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}

.variable-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.clickable-tag {
  cursor: pointer;
  transition: all 0.2s ease;
}

.clickable-tag:hover {
  transform: scale(1.05);
  opacity: 0.8;
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