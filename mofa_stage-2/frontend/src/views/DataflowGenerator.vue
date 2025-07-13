<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">智能生成 Dataflow</h1>
      <div class="page-actions">
        <el-button @click="goBack">返回</el-button>
      </div>
    </div>

    <el-card class="generator-card">
      <el-form :model="form" label-width="120px" class="generator-form">
        <el-form-item label="Dataflow 名称" required>
          <el-input 
            v-model="form.flowName" 
            placeholder="输入 Dataflow 名称（例如：my_workflow）"
            :disabled="isGenerating"
          />
        </el-form-item>

        <el-form-item label="功能描述" required>
          <el-input 
            v-model="form.flowDescription" 
            type="textarea"
            :rows="4"
            placeholder="详细描述你想要实现的功能，例如：我想要一个能够搜索论文、分析内容并生成报告的工作流"
            :disabled="isGenerating"
          />
        </el-form-item>

        <el-form-item label="选择 Nodes">
          <div class="nodes-selection">
            <div class="nodes-search">
              <el-input 
                v-model="searchQuery" 
                placeholder="搜索 nodes..."
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
                :class="{ 'selected': isNodeSelected(node.name) }"
                @click="toggleNode(node.name)"
              >
                <div class="node-header">
                  <el-checkbox 
                    :model-value="isNodeSelected(node.name)"
                    @change="() => toggleNode(node.name)"
                    :disabled="isGenerating"
                  />
                  <span class="node-name">{{ node.name }}</span>
                </div>
                <div class="node-description">
                  {{ node.description }}
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
            生成 Dataflow
          </el-button>
          <span class="selected-count">
            已选择 {{ form.selectedNodes.length }} 个 nodes
          </span>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 生成结果对话框 -->
    <el-dialog 
      v-model="resultDialog"
      title="Dataflow 生成结果"
      width="60%"
      :close-on-click-modal="false"
      append-to-body
    >
      <div v-if="generationResult.success">
        <el-alert
          title="生成成功！"
          :description="generationResult.message"
          type="success"
          :closable="false"
          show-icon
        />
        
        <div class="result-content">
          <h4>生成的 YAML 配置：</h4>
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
          title="生成失败"
          :description="generationResult.message"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resultDialog = false">关闭</el-button>
          <el-button 
            v-if="generationResult.success" 
            type="primary" 
            @click="goToAgentList"
          >
            编辑 Dataflow
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAgentStore } from '../store/agent'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'

export default {
  name: 'DataflowGenerator',
  components: {
    MagicStick
  },
  setup() {
    const router = useRouter()
    const agentStore = useAgentStore()
    
    const isGenerating = ref(false)
    const resultDialog = ref(false)
    const searchQuery = ref('')
    
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
    const filteredNodes = computed(() => {
      if (!searchQuery.value) {
        return agentStore.availableNodes
      }
      return agentStore.availableNodes.filter(node => 
        node.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
        node.description.toLowerCase().includes(searchQuery.value.toLowerCase())
      )
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
    
    // 生成dataflow
    const generateDataflow = async () => {
      if (!canGenerate.value) {
        ElMessage.warning('请填写完整信息并选择至少一个 node')
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
          ElMessage.success('Dataflow 生成成功')
        } else {
          ElMessage.error('Dataflow 生成失败')
        }
      } catch (error) {
        ElMessage.error('生成过程中出现错误')
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

.node-description {
  color: #606266;
  font-size: 12px;
  line-height: 1.4;
}

.selected-count {
  margin-left: 15px;
  color: #909399;
  font-size: 14px;
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