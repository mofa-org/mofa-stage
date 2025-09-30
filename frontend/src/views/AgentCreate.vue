<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Create New Agent</h1>
      <div class="page-actions">
        <el-button @click="goBack">Back</el-button>
      </div>
    </div>

    <el-card class="create-options">
      <el-tabs v-model="activeTab">
        <!-- 创建方式：模板库 -->
        <el-tab-pane label="Template Library" name="templates">
          <div class="tab-content">
            <h3>Start from a Curated Template</h3>
            <p>Select a MoFA node or dataflow template to bootstrap your agent with best-practice wiring.</p>

            <el-form :model="templateForm" label-width="120px" class="create-form">
              <el-form-item label="Agent Name" required>
                <el-input v-model="templateForm.name" placeholder="Enter a unique agent name" />
              </el-form-item>
              <el-form-item label="Version">
                <el-input v-model="templateForm.version" placeholder="e.g., 0.0.1" />
              </el-form-item>
              <el-form-item label="Author">
                <el-input v-model="templateForm.authors" placeholder="Your name" />
              </el-form-item>
              <el-form-item label="Agent Type">
                <el-radio-group v-model="templateForm.agentType">
                  <el-radio label="agent-hub">{{ $t('settings.agentHubDir') }}</el-radio>
                  <el-radio label="examples">{{ $t('settings.examplesDir') }}</el-radio>
                </el-radio-group>
                <div class="form-help">{{ $t('agent.agentTypeHelp') }}</div>
              </el-form-item>
              <el-form-item label="Template">
                <div v-if="filteredTemplates.length" class="template-grid">
                  <el-card
                    v-for="template in filteredTemplates"
                    :key="template.name"
                    class="template-card"
                    :class="{ selected: templateForm.template === template.name }"
                    @click="selectTemplate(template.name)"
                  >
                    <div class="template-card-header">
                      <h4>{{ template.name }}</h4>
                      <el-tag v-if="templateForm.template === template.name" type="success" size="small">Selected</el-tag>
                    </div>
                    <p class="template-description">{{ template.description }}</p>
                    <div v-if="template.metadata" class="template-meta">
                      <el-tag
                        v-if="template.metadata.entry_points && template.metadata.entry_points.length"
                        size="small"
                        type="info"
                        effect="light"
                      >{{ template.metadata.entry_points[0] }}</el-tag>
                      <el-tag
                        v-if="template.metadata.dependencies && template.metadata.dependencies.length"
                        size="small"
                        type="warning"
                        effect="light"
                      >deps: {{ template.metadata.dependencies.length }}</el-tag>
                      <el-tag
                        v-if="template.metadata.tests && template.metadata.tests.length"
                        size="small"
                        type="success"
                        effect="light"
                      >tests</el-tag>
                    </div>
                  </el-card>
                </div>
                <el-empty v-else description="No templates detected for current agent type" />
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  @click="createTemplateAgent"
                  :loading="isCreating"
                  :disabled="isCreating || !templateForm.template || !templateForm.name.trim()"
                >
                  Create Agent
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 创建方式：复制现有 Agent -->
        <el-tab-pane label="Copy Existing Agent" name="copy">
          <div class="tab-content">
            <h3>Create from an Existing Agent</h3>
            <p>Duplicate an existing agent as the starting point. Great for extending current functionality.</p>

            <el-form :model="copyForm" label-width="100px" class="create-form">
              <el-form-item label="Source Agent" required>
                <el-select v-model="copyForm.source" placeholder="Select an existing agent" style="width: 100%;">
                  <el-option v-for="agent in agents" :key="agent" :label="agent" :value="agent" />
                </el-select>
              </el-form-item>
              <el-form-item label="New Agent Name" required>
                <el-input v-model="copyForm.target" placeholder="Enter a unique agent name" />
              </el-form-item>
              <el-form-item label="Agent Type">
                <el-radio-group v-model="copyForm.agentType">
                  <el-radio label="auto">{{ $t('agent.autoDetect') }}</el-radio>
                  <el-radio label="agent-hub">{{ $t('settings.agentHubDir') }}</el-radio>
                  <el-radio label="examples">{{ $t('settings.examplesDir') }}</el-radio>
                </el-radio-group>
                <div class="form-help">{{ $t('agent.agentTypeHelp') }}</div>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="createCopyAgent" :loading="isCreating">
                  Create Agent
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog 
      v-model="creationSuccessDialog"
      title="Agent Created"
      width="30%">
      <span>Agent "{{ newAgentName }}" was created successfully!</span>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="goBack">Back to List</el-button>
          <el-button type="primary" @click="goToEdit">
            Edit Agent
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

export default {
  name: 'AgentCreate',
  setup() {
    const router = useRouter()
    const agentStore = useAgentStore()
    
    const activeTab = ref('templates')
    const isCreating = ref(false)
    const creationSuccessDialog = ref(false)
    const newAgentName = ref('')
    
    const templateForm = ref({
      name: '',
      version: '0.0.1',
      authors: 'MoFA_Stage User',
      agentType: 'agent-hub',
      template: ''
    })
    
    const copyForm = ref({
      source: '',
      target: '',
      agentType: 'auto' // 默认为自动检测类型
    })
    
    const agents = computed(() => agentStore.allAgents)
    const templatesByType = computed(() => agentStore.agentTemplates || { 'agent-hub': [], examples: [] })
    const filteredTemplates = computed(() => templatesByType.value[templateForm.value.agentType] || [])
    
    const selectTemplate = (templateName) => {
      templateForm.value.template = templateName
    }

    // 从模板创建 Agent
    const createTemplateAgent = async () => {
      if (!templateForm.value.name.trim()) {
        ElMessage.warning('Please enter the Agent name')
        return
      }
      if (!templateForm.value.template) {
        ElMessage.warning('Please select a template')
        return
      }
      
      isCreating.value = true
      const payload = {
        name: templateForm.value.name.trim(),
        version: templateForm.value.version || '0.0.1',
        authors: templateForm.value.authors || 'MoFA_Stage User',
        agent_type: templateForm.value.agentType,
        template: templateForm.value.template
      }
      const result = await agentStore.createAgent(payload)
      isCreating.value = false
      
      if (result) {
        newAgentName.value = payload.name
        creationSuccessDialog.value = true
      } else {
        ElMessage.error(`Failed to create Agent: ${agentStore.error}`)
      }
    }
    
    // 复制现有 Agent 创建新 Agent
    const createCopyAgent = async () => {
      if (!copyForm.value.source || !copyForm.value.target) {
        ElMessage.warning('Please select a source Agent and enter a new Agent name')
        return
      }
      
      isCreating.value = true
      // 如果选择了 'auto'，则传递 null 作为 agentType
      const agentType = copyForm.value.agentType === 'auto' ? null : copyForm.value.agentType
      const result = await agentStore.copyAgent(
        copyForm.value.source,
        copyForm.value.target,
        agentType // 传递 Agent 类型
      )
      isCreating.value = false
      
      if (result) {
        newAgentName.value = copyForm.value.target
        creationSuccessDialog.value = true
      } else {
        ElMessage.error(`Failed to copy Agent: ${agentStore.error}`)
      }
    }
    
    // 导航方法
    const goBack = () => {
      router.push('/agents')
    }
    
    const goToEdit = () => {
      router.push(`/agents/${newAgentName.value}/edit`)
    }
    
    watch(filteredTemplates, (list) => {
      if (!list.length) {
        templateForm.value.template = ''
        return
      }
      if (!list.some(item => item.name === templateForm.value.template)) {
        templateForm.value.template = list[0].name
      }
    }, { immediate: true })

    onMounted(async () => {
      // 确保已加载 agent 列表
      if (agents.value.length === 0) {
        await agentStore.fetchAgents()
      }
      await agentStore.fetchAgentTemplates()
    })
    
    return {
      activeTab,
      isCreating,
      templateForm,
      copyForm,
      agents,
      creationSuccessDialog,
      newAgentName,
      filteredTemplates,
      selectTemplate,
      createTemplateAgent,
      createCopyAgent,
      goBack,
      goToEdit
    }
  }
}
</script>

<style scoped>
.create-options {
  max-width: 900px;
  margin: 0 auto;
}

.tab-content {
  padding: 20px 0;
}

.create-form {
  margin-top: 20px;
  max-width: 560px;
}

h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

p {
  color: var(--text-color-secondary);
  margin-bottom: 20px;
}

.form-help {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-top: 4px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  width: 100%;
}

.template-card {
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  height: 100%;
}

.template-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.12);
}

.template-card.selected {
  border-color: #67c23a;
  box-shadow: 0 4px 14px rgba(103, 194, 58, 0.18);
}

.template-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.template-card h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.template-description {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 12px;
}

.template-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
