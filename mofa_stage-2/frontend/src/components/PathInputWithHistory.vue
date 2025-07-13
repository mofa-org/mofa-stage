<template>
  <div class="path-input-container">
    <el-autocomplete
      v-model="inputValue"
      :fetch-suggestions="fetchSuggestions"
      :placeholder="placeholder"
      @select="handleSelect"
      @input="handleInput"
      @blur="handleBlur"
      class="path-input"
      :clearable="true"
      style="width: 100%"
    >
      <template #default="{ item }">
        <div class="suggestion-item">
          <el-icon class="suggestion-icon">
            <Folder v-if="isRecentPath(item.value)" />
            <Document v-else />
          </el-icon>
          <span class="suggestion-path">{{ item.value }}</span>
          <span v-if="isRecentPath(item.value)" class="suggestion-tag">最近使用</span>
        </div>
      </template>
      
      <template #append>
        <el-dropdown @command="handleDropdownCommand" placement="bottom-end">
          <el-button>
            <el-icon><More /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="browse">
                <el-icon><Folder /></el-icon>
                {{ $t('settings.inputPath') || '输入路径' }}
              </el-dropdown-item>
              <el-dropdown-item command="clear-history" v-if="pathHistory.length > 0">
                <el-icon><Delete /></el-icon>
                清除历史记录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </el-autocomplete>
    
    <!-- 历史记录快捷选择 -->
    <div v-if="showQuickHistory && pathHistory.length > 0" class="quick-history">
      <span class="quick-history-label">最近使用:</span>
      <el-tag
        v-for="(path, index) in pathHistory.slice(0, 3)"
        :key="index"
        @click="selectHistoryPath(path)"
        class="history-tag"
        size="small"
        type="info"
        effect="plain"
      >
        {{ getShortPath(path) }}
      </el-tag>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Folder, Document, More, Delete } from '@element-plus/icons-vue'
import PathHistory from '../utils/pathHistory'
import { smartSelectPath } from '../utils/fileBrowser'

export default {
  name: 'PathInputWithHistory',
  components: {
    Folder,
    Document, 
    More,
    Delete
  },
  props: {
    modelValue: {
      type: String,
      default: ''
    },
    pathType: {
      type: String,
      required: true
    },
    placeholder: {
      type: String,
      default: ''
    },
    context: {
      type: Object,
      default: () => ({})
    },
    showQuickHistory: {
      type: Boolean,
      default: true
    }
  },
  emits: ['update:modelValue', 'browse'],
  setup(props, { emit }) {
    const inputValue = ref(props.modelValue)
    const pathHistory = ref([])
    
    // 监听props.modelValue变化
    watch(() => props.modelValue, (newValue) => {
      inputValue.value = newValue
    })
    
    // 监听输入值变化并向上传递
    watch(inputValue, (newValue) => {
      emit('update:modelValue', newValue)
    })
    
    // 加载历史记录
    const loadHistory = () => {
      pathHistory.value = PathHistory.getHistory(props.pathType)
    }
    
    // 获取建议列表
    const fetchSuggestions = (queryString, callback) => {
      const suggestions = PathHistory.getPathSuggestions(
        props.pathType, 
        queryString, 
        props.context
      )
      
      const result = suggestions.map(path => ({
        value: path,
        label: path
      }))
      
      callback(result)
    }
    
    // 处理选择建议
    const handleSelect = (item) => {
      inputValue.value = item.value
      addToHistory(item.value)
    }
    
    // 处理输入
    const handleInput = (value) => {
      inputValue.value = value
    }
    
    // 处理失去焦点
    const handleBlur = () => {
      if (inputValue.value && inputValue.value.trim() !== '') {
        addToHistory(inputValue.value.trim())
      }
    }
    
    // 添加到历史记录
    const addToHistory = (path) => {
      PathHistory.addToHistory(props.pathType, path)
      loadHistory()
    }
    
    // 选择历史记录中的路径
    const selectHistoryPath = (path) => {
      inputValue.value = path
      addToHistory(path)
    }
    
    // 判断是否为最近使用的路径
    const isRecentPath = (path) => {
      return pathHistory.value.includes(path)
    }
    
    // 获取路径的简短显示形式
    const getShortPath = (path) => {
      if (path.length <= 30) {
        return path
      }
      return '...' + path.slice(-27)
    }
    
    // 处理下拉菜单命令
    const handleDropdownCommand = async (command) => {
      switch (command) {
        case 'browse':
          try {
            const selectedPath = await smartSelectPath(inputValue.value, props.pathType)
            if (selectedPath) {
              inputValue.value = selectedPath
              addToHistory(selectedPath)
              ElMessage.success('路径设置成功')
            }
          } catch (error) {
            console.error('Path selection error:', error)
            ElMessage.error('路径选择失败，请手动输入')
          }
          break
        case 'clear-history':
          PathHistory.clearHistory(props.pathType)
          loadHistory()
          ElMessage.success('历史记录已清除')
          break
      }
    }
    
    onMounted(() => {
      loadHistory()
    })
    
    return {
      inputValue,
      pathHistory,
      fetchSuggestions,
      handleSelect,
      handleInput,
      handleBlur,
      selectHistoryPath,
      isRecentPath,
      getShortPath,
      handleDropdownCommand
    }
  }
}
</script>

<style scoped>
.path-input-container {
  width: 100%;
}

.path-input {
  width: 100%;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.suggestion-icon {
  color: var(--el-color-primary);
  font-size: 14px;
}

.suggestion-path {
  flex: 1;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.suggestion-tag {
  font-size: 11px;
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
  padding: 2px 6px;
  border-radius: 4px;
}

.quick-history {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-history-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.history-tag {
  cursor: pointer;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-tag:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
}

/* Dark theme adjustments */
[data-theme="dark"] .suggestion-tag {
  background: rgba(103, 194, 58, 0.2);
}

[data-theme="dark"] .quick-history-label {
  color: var(--el-text-color-secondary);
}
</style> 