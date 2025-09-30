<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Generate Dataflow</h1>
      <div class="page-actions">
        <el-button @click="goBack">Back</el-button>
      </div>
    </div>

    <el-card class="generator-card">
      <el-form :model="form" label-width="120px" class="generator-form">
        <el-form-item label="Dataflow Name" required>
          <el-input 
            v-model="form.flowName" 
            placeholder="Enter a dataflow name (e.g., my_workflow)"
            :disabled="isGenerating"
          />
        </el-form-item>

        <el-form-item label="Description" required>
          <el-input 
            v-model="form.flowDescription" 
            type="textarea"
            :rows="4"
            placeholder="Describe the workflow you want to build, e.g., search papers, analyze content, and generate a report"
            :disabled="isGenerating"
          />
        </el-form-item>

        <el-form-item label="Node Recommendations">
          <el-button 
            type="primary" 
            plain
            @click="requestNodeSuggestions"
            :loading="isRecommending"
            :disabled="isGenerating || !form.flowDescription.trim()"
          >
            <el-icon><Opportunity /></el-icon>
            Recommend Nodes
          </el-button>
          <span class="recommend-hint">
            Automatically suggests candidate nodes based on your description; you can refine the selection manually.
          </span>
        </el-form-item>

        <el-form-item label="Select Nodes">
          <div class="nodes-selection">
            <div class="nodes-search">
              <el-input 
                v-model="searchQuery" 
                placeholder="Search nodes..."
                prefix-icon="el-icon-search"
                clearable
                :disabled="isGenerating"
              />
            </div>
            
            <div class="nodes-grid">
              <div 
                v-for="node in filteredNodes" 
                :key="node.name"
                class="node-card"
                :class="{ 'selected': isNodeSelected(node.name), 'recommended': isNodeRecommended(node.name) }"
                @click="toggleNode(node.name)"
              >
                <div class="node-header">
                  <el-checkbox 
                    :model-value="isNodeSelected(node.name)"
                    @change="() => toggleNode(node.name)"
                    :disabled="isGenerating"
                  />
                  <span class="node-name">{{ node.name }}</span>
                  <el-button 
                    type="text"
                    class="node-info-btn"
                    @click.stop="openNodeDetails(node.name)"
                    :disabled="nodeDetailLoading"
                  >
                    <el-icon><InfoFilled /></el-icon>
                  </el-button>
                  <el-tag 
                    v-if="isNodeRecommended(node.name)"
                    type="success"
                    size="small"
                    effect="light"
                    class="recommend-tag"
                  >
                    Recommended
                    <span v-if="recommendationScore(node.name)" class="recommend-score">({{ recommendationScore(node.name) }})</span>
                  </el-tag>
                </div>
                <div class="node-description">
                  {{ node.description }}
                </div>
                <div v-if="node.metadata" class="node-flags">
                  <el-tag v-if="node.metadata.has_agent_package" size="small" type="info" effect="light">agent/</el-tag>
                  <el-tag v-if="node.metadata.has_dataflow" size="small" type="success" effect="light">dataflow</el-tag>
                  <el-tag v-if="node.metadata.has_configs" size="small" type="warning" effect="light">configs</el-tag>
                  <el-tag v-if="node.metadata.has_tests" size="small" type="danger" effect="light">tests</el-tag>
                </div>
                <div v-if="node.metadata && node.metadata.primary_files" class="node-meta-line">
                  <strong>Key Files:</strong> {{ node.metadata.primary_files.slice(0, 2).join(', ') }}
                </div>
                <div v-if="node.metadata && node.metadata.entry_points" class="node-meta-line">
                  <strong>Commands:</strong> {{ node.metadata.entry_points.slice(0, 2).join(', ') }}
                </div>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            @click="generateDataflow"
            :loading="isGenerating"
            :disabled="!canGenerate"
          >
            <el-icon><MagicStick /></el-icon>
            Generate Dataflow
          </el-button>
          <span class="selected-count">
            Selected {{ form.selectedNodes.length }} nodes
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog
      v-model="nodeDetailDialog"
      :title="activeNodeName ? `${activeNodeName} Node Details` : 'Node Details'"
      width="55%"
      :close-on-click-modal="false"
      append-to-body
    >
      <div v-if="nodeDetailLoading" class="node-detail-loading">
        <el-skeleton :rows="8" animated />
      </div>
      <div v-else-if="activeNodeDetails" class="node-detail-content">
        <p class="detail-description">{{ activeNodeDetails.description }}</p>

        <div class="detail-meta" v-if="activeNodeDetails.metadata">
          <div v-if="activeNodeDetails.metadata.dependencies" class="detail-meta-row">
            <strong>Dependencies:</strong>
            <span>{{ activeNodeDetails.metadata.dependencies.join(', ') }}</span>
          </div>
          <div v-if="activeNodeDetails.metadata.entry_points" class="detail-meta-row">
            <strong>Entry Points:</strong>
            <span>{{ activeNodeDetails.metadata.entry_points.join(', ') }}</span>
          </div>
          <div v-if="activeNodeDetails.metadata.primary_files" class="detail-meta-row">
            <strong>Core Files:</strong>
            <span>{{ activeNodeDetails.metadata.primary_files.join(', ') }}</span>
          </div>
          <div v-if="activeNodeDetails.metadata.config_files" class="detail-meta-row">
            <strong>Configs:</strong>
            <span>{{ activeNodeDetails.metadata.config_files.join(', ') }}</span>
          </div>
          <div v-if="activeNodeDetails.metadata.tests" class="detail-meta-row">
            <strong>Tests:</strong>
            <span>{{ activeNodeDetails.metadata.tests.join(', ') }}</span>
          </div>
        </div>

        <el-divider v-if="contextSnippets.length" content-position="left">Context Snippets</el-divider>
        <div v-for="snippet in contextSnippets" :key="snippet.path" class="detail-snippet">
          <div class="snippet-header">
            <el-tag size="small" type="info" effect="dark">{{ snippet.type }}</el-tag>
            <span class="snippet-path">{{ snippet.path }}</span>
          </div>
          <pre class="snippet-content">{{ snippet.content }}</pre>
        </div>
      </div>
      <div v-else class="node-detail-empty">
        <el-empty description="No node details available" />
      </div>
    </el-dialog>

    <!-- 生成结果对话框 -->
    <el-dialog 
      v-model="resultDialog"
      title="Dataflow Result"
      width="60%"
      :close-on-click-modal="false"
      append-to-body
    >
      <div v-if="generationResult.success">
        <el-alert
          title="Generated successfully!"
          :description="generationResult.message"
          type="success"
          :closable="false"
          show-icon
        />
        
        <div class="result-content">
          <h4>Generated YAML configuration:</h4>
          <el-input
            v-model="generationResult.yamlContent"
            type="textarea"
            :rows="15"
            readonly
            class="yaml-content"
          />
        </div>
      </div>
      <div v-else>
        <el-alert
          title="Generation failed"
          :description="generationResult.message"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resultDialog = false">Close</el-button>
          <el-button 
            v-if="generationResult.success" 
            type="primary" 
            @click="goToAgentList"
          >
            Edit Dataflow
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '../store/agent'
import { ElMessage } from 'element-plus'
import { MagicStick, Opportunity, InfoFilled } from '@element-plus/icons-vue'

export default {
  name: 'DataflowGenerator',
  components: {
    MagicStick,
    Opportunity,
    InfoFilled
  },
  setup() {
    const router = useRouter()
    const agentStore = useAgentStore()
    
    const isGenerating = ref(false)
    const isRecommending = ref(false)
    const resultDialog = ref(false)
    const searchQuery = ref('')
    const recommendedNodes = ref([])
    const nodeDetailDialog = ref(false)
    const nodeDetailLoading = ref(false)
    const activeNodeDetails = ref(null)
    const activeNodeName = ref('')

    const form = ref({
      flowName: '',
      flowDescription: '',
      selectedNodes: []
    })
    
    const generationResult = ref({
      success: false,
      message: '',
      yamlContent: '',
      dataflowPath: ''
    })
    
    // 过滤后的nodes
    const recommendedMap = computed(() => {
      const map = new Map()
      recommendedNodes.value.forEach(item => {
        if (item && item.name) {
          map.set(item.name, item)
        }
      })
      return map
    })

    const filteredNodes = computed(() => {
      const nodes = agentStore.availableNodes || []
      if (!searchQuery.value) {
        return nodes
      }
      const term = searchQuery.value.toLowerCase()
      return nodes.filter(node => {
        const description = (node.description || '').toLowerCase()
        return node.name.toLowerCase().includes(term) || description.includes(term)
      })
    })
    
    // 是否可以生成
    const canGenerate = computed(() => {
      return form.value.flowName.trim() && 
             form.value.flowDescription.trim() && 
             form.value.selectedNodes.length > 0 &&
             !isGenerating.value
    })
    
    // 检查node是否被选中
    const isNodeSelected = (nodeName) => {
      return form.value.selectedNodes.includes(nodeName)
    }
    
    // 切换node选择状态
    const toggleNode = (nodeName) => {
      if (isGenerating.value) return
      
      const index = form.value.selectedNodes.indexOf(nodeName)
      if (index > -1) {
        form.value.selectedNodes.splice(index, 1)
      } else {
        form.value.selectedNodes.push(nodeName)
      }
    }

    const isNodeRecommended = (nodeName) => recommendedMap.value.has(nodeName)

    const recommendationScore = (nodeName) => {
      const item = recommendedMap.value.get(nodeName)
      if (!item || item.score === undefined || item.score === null) {
        return null
      }
      const score = Number(item.score)
      if (Number.isNaN(score)) {
        return null
      }
      return score.toFixed(2)
    }

    const applyRecommendationSelection = (suggestions) => {
      if (!Array.isArray(suggestions) || suggestions.length === 0) {
        return
      }
      const names = suggestions
        .map(item => item?.name)
        .filter(Boolean)
      if (names.length === 0) {
        return
      }
      const merged = new Set(form.value.selectedNodes)
      names.forEach(name => merged.add(name))
      form.value.selectedNodes = Array.from(merged)
    }

    const requestNodeSuggestions = async () => {
      if (!form.value.flowDescription.trim()) {
        ElMessage.warning('Enter a description before requesting recommendations')
        return
      }
      isRecommending.value = true
      try {
        const suggestions = await agentStore.suggestNodes(form.value.flowDescription, 6)
        recommendedNodes.value = suggestions
        if (!suggestions || suggestions.length === 0) {
          ElMessage.info('No suitable recommendations found. Try a more specific description.')
          return
        }
        applyRecommendationSelection(suggestions)
        ElMessage.success(`Recommended ${suggestions.length} nodes. Adjust the selection as needed.`)
      } catch (error) {
        console.error(error)
        ElMessage.error('Failed to fetch node recommendations. Please try again later.')
      } finally {
        isRecommending.value = false
      }
    }

    const openNodeDetails = async (nodeName) => {
      if (!nodeName) {
        return
      }
      nodeDetailLoading.value = true
      activeNodeName.value = nodeName
      try {
        const details = await agentStore.fetchNodeDetails(nodeName)
        if (details) {
          activeNodeDetails.value = details
          nodeDetailDialog.value = true
        } else {
          ElMessage.error('Unable to retrieve node details')
        }
      } catch (error) {
        console.error(error)
        ElMessage.error('Failed to fetch node details')
      } finally {
        nodeDetailLoading.value = false
      }
    }

    const contextSnippets = computed(() => {
      if (!activeNodeDetails.value || !activeNodeDetails.value.metadata) {
        return []
      }
      return (activeNodeDetails.value.metadata.context_snippets || []).slice(0, 5).map(item => ({
        path: item.path,
        type: item.type,
        content: item.snippet || item.excerpt || ''
      }))
    })
    
    // 生成dataflow
    const generateDataflow = async () => {
      if (!canGenerate.value) {
        ElMessage.warning('Fill in all information and select at least one node')
        return
      }
      
      isGenerating.value = true
      
      try {
        const result = await agentStore.generateDataflow(
          form.value.selectedNodes,
          form.value.flowDescription,
          form.value.flowName
        )
        
        generationResult.value = result
        resultDialog.value = true
        
        if (result.success) {
          ElMessage.success('Dataflow generated successfully')
        } else {
          ElMessage.error('Dataflow generation failed')
        }
      } catch (error) {
        ElMessage.error('An error occurred during generation')
        console.error(error)
      } finally {
        isGenerating.value = false
      }
    }
    
    // 导航方法
    const goBack = () => {
      router.push('/agents')
    }
    
    const goToAgentList = () => {
      resultDialog.value = false
      // 直接跳转到生成的dataflow的编辑页面
      router.push(`/agents/${form.value.flowName}/edit?type=examples`)
    }
    
    // 初始化
    onMounted(async () => {
      await agentStore.fetchAvailableNodes()
    })

    watch(nodeDetailDialog, (open) => {
      if (!open) {
        activeNodeDetails.value = null
        activeNodeName.value = ''
        nodeDetailLoading.value = false
      }
    })

    return {
      form,
      isGenerating,
      resultDialog,
      searchQuery,
      filteredNodes,
      canGenerate,
      generationResult,
      isNodeSelected,
      toggleNode,
      isNodeRecommended,
      recommendationScore,
      requestNodeSuggestions,
      isRecommending,
      recommendedNodes,
      openNodeDetails,
      nodeDetailDialog,
      nodeDetailLoading,
      activeNodeDetails,
      activeNodeName,
      contextSnippets,
      generateDataflow,
      goBack,
      goToAgentList
    }
  }
}
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  color: #303133;
}

.generator-card {
  margin-bottom: 20px;
}

.generator-form {
  max-width: 800px;
}

.nodes-selection {
  width: 100%;
}

.nodes-search {
  margin-bottom: 15px;
}

.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 15px;
}

.node-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.node-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 4px rgba(64, 158, 255, 0.1);
}

.node-card.selected {
  border-color: #409eff;
  background-color: #f0f9ff;
}

.node-card.recommended {
  border-color: #67c23a;
  box-shadow: 0 2px 6px rgba(103, 194, 58, 0.18);
}

.node-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.node-name {
  font-weight: 500;
  color: #303133;
  margin-left: 8px;
}

.node-info-btn {
  margin-left: auto;
  color: #909399;
  padding: 0;
}

.node-info-btn :deep(.el-icon) {
  font-size: 16px;
}

.node-info-btn:hover {
  color: #409eff;
}

.recommend-tag {
  margin-left: auto;
}

.recommend-score {
  margin-left: 4px;
  font-size: 12px;
  color: #67c23a;
}

.node-description {
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
}

.node-flags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.node-meta-line {
  margin-top: 6px;
  color: #606266;
  font-size: 12px;
}

.selected-count {
  margin-left: 15px;
  color: #909399;
  font-size: 14px;
}

.recommend-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}

.node-detail-loading {
  padding: 12px 0;
}

.node-detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-description {
  margin: 0;
  line-height: 1.6;
  color: #303133;
}

.detail-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}

.detail-meta-row strong {
  margin-right: 6px;
  color: #303133;
}

.detail-snippet {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}

.snippet-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.snippet-path {
  font-size: 12px;
  color: #909399;
}

.snippet-content {
  margin: 0;
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #303133;
}

.node-detail-empty {
  padding: 24px 0;
}

.result-content {
  margin-top: 20px;
}

.yaml-content {
  margin-top: 10px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.yaml-content :deep(textarea) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
}
</style> 
