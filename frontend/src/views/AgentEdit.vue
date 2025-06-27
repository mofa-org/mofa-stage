<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="page-title">{{ agentName }}</h1>
        <el-tag v-if="isAgentRunning" type="success">运行中</el-tag>
      </div>
      
      <div class="header-actions">
        <el-button-group>
          <el-button 
            v-if="useNewEditor && vscodeStatus.running" 
            @click="installExtensions" 
            type="success" 
            size="small">
            <el-icon><Download /></el-icon>
            扩展
          </el-button>
          <el-button 
            v-if="useNewEditor && vscodeStatus.running" 
            @click="updateVSCodeConfig" 
            type="info" 
            size="small">
            <el-icon><Setting /></el-icon>
            配置
          </el-button>
          <el-button class="custom-save-btn" @click="saveCurrentFile" :disabled="!hasChanges" :loading="isSaving">
            <el-icon><Document /></el-icon>
            Save
          </el-button>
          <el-button v-if="!isAgentRunning" class="custom-run-btn" @click="runAgent">
            <el-icon><VideoPlay /></el-icon>
            Run
          </el-button>
          <el-button v-else type="danger" @click="stopAgent">
            <el-icon><VideoPause /></el-icon>
            Stop
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 加载中 -->
    <el-card v-if="isLoading" class="loading-container">
      <el-skeleton :rows="10" animated />
    </el-card>

    <!-- 主编辑区 -->
    <div v-else class="main-edit-area">
      <!-- 新版编辑器 - VS Code Web 嵌入 -->
      <div v-if="useNewEditor" class="vscode-full-container">
        <div v-if="vscodeStatus.loading" class="vscode-loading">
          <div v-loading="true" element-loading-text="正在启动 VS Code Web..." class="loading-container">
          </div>
        </div>
        <div v-else-if="vscodeStatus.error" class="vscode-error">
          <el-alert
            title="VS Code Web 启动失败"
            type="error"
            :description="vscodeStatus.error"
            show-icon
          />
          <el-button @click="startVSCodeServer" type="primary" style="margin-top: 10px;">
            重试启动
          </el-button>
        </div>
        <VSCodeEmbed 
          v-else-if="vscodeStatus.running"
          :folder-path="agentFolderPath" 
          :vscode-base-url="vscodeBaseUrl" 
        />
        <div v-else class="vscode-starting">
          <el-empty description="正在准备 VS Code Web...">
            <el-button @click="startVSCodeServer" type="primary">
              启动 VS Code
            </el-button>
            <el-button @click="installExtensions" type="success" style="margin-left: 10px;">
              安装推荐扩展
            </el-button>
            <el-button @click="updateVSCodeConfig" type="info" style="margin-left: 10px;">
              更新配置
            </el-button>
          </el-empty>
        </div>
      </div>
      <!-- 经典编辑器 -->
      <div v-else class="edit-container">
        <!-- 文件树侧边栏 -->
        <div v-if="!useNewEditor" class="file-tree-sidebar" :class="{ 'collapsed': fileTreeCollapsed }" :style="{ width: fileTreeCollapsed ? '40px' : fileSidebarWidth + 'px' }">
          <div class="file-tree-resize-handle" @mousedown="startResizeFileSidebar" v-if="!fileTreeCollapsed"></div>
          
          <!-- 折叠/展开按钮 -->
          <div class="file-tree-collapse-btn" @click="toggleFileTree">
            <el-icon class="collapse-icon" :class="{ 'collapsed': fileTreeCollapsed }">
              <ArrowLeft v-if="!fileTreeCollapsed" />
              <ArrowRight v-else />
            </el-icon>
          </div>
          
          <div v-if="!fileTreeCollapsed" class="sidebar-header">
            <h3>文件列表</h3>
            <el-input
              placeholder="搜索文件"
              v-model="fileSearchQuery"
              prefix-icon="Search"
              clearable
              size="small"
            />
          </div>
          
          <div v-if="!fileTreeCollapsed" class="file-tree-wrapper" ref="fileTreeWrapper" @scroll="rememberFileTreeScroll">
            <el-tree
              :data="fileTreeData"
              :props="defaultProps"
              :filter-node-method="filterNode"
              @node-click="handleFileClick"
              @node-contextmenu="handleFileRightClick"
              ref="fileTree"
              default-expand-all
              highlight-current
            />
          </div>

          <div v-if="!fileTreeCollapsed" class="sidebar-footer">
            <el-button-group>
              <el-button size="small" @click="addNewFile" :icon="Document">文件</el-button>
              <el-button size="small" @click="addNewFolder" :icon="FolderAdd">文件夹</el-button>
            </el-button-group>
          </div>
        </div>

        <!-- 编辑器区域 -->
        <div class="editor-area">
          <div v-if="currentFile" class="editor-container">
            <div class="editor-header">
              <div class="file-path">{{ currentFile.path }}</div>
              <div class="file-actions">
                <el-button-group>
                  <!-- 预览切换按钮，仅在支持预览的文件类型中显示 -->
                  <el-button 
                    v-if="isMarkdownFile || isMermaidHtml || isImageFile || isVideoFile"
                    size="small"
                    @click="togglePreviewMode"
                    :type="previewMode ? 'primary' : 'default'">
                    {{ previewMode ? '编辑' : '预览' }}
                  </el-button>
                  <el-button 
                    size="small" 
                    @click="saveCurrentFile" 
                    :disabled="!hasChanges"
                    :loading="isSaving">
                    保存
                  </el-button>
                </el-button-group>
              </div>
            </div>

            <!-- 代码编辑器/预览 -->
            <div class="editor-content">
              <div class="code-editor-wrapper">
                <!-- 对于 dataflow YAML，使用 Tab 形式同时展示代码与图形 -->
                <template v-if="showYamlTabs && isDataflowYaml">
                  <el-tabs v-model="activeYamlTab" type="border-card" class="yaml-preview-tabs" >
                    <el-tab-pane label="YAML" name="yaml">
                      <!-- 根据设置选择编辑器版本 -->
                      <CodeEditor
                        v-if="!useNewEditor"
                        v-model="editorContent"
                        :language="editorLanguage"
                        @save="saveCurrentFile"
                        ref="codeEditorRef"
                      />
                      <div v-else class="new-editor-placeholder">
                        <el-empty description="请选择文件或切换到新版编辑器" />
                      </div>
                    </el-tab-pane>
                    <el-tab-pane label="Graph" name="graph">
                      <MermaidViewer :code="mermaidCode" @node-click="handleMermaidNodeClick" />
                    </el-tab-pane>
                  </el-tabs>
                </template>

                <!-- 其他文件类型沿用原先的预览/编辑器切换逻辑 -->
                <template v-else>
                  <template v-if="previewMode">
                    <!-- Markdown 文件预览 -->
                    <div v-if="isMarkdownFile" class="markdown-preview" v-html="renderedMarkdown"></div>
                    <!-- Dataflow YAML -> Mermaid 预览 -->
                    <MermaidViewer v-else-if="isDataflowYaml" :code="mermaidCode" @node-click="handleMermaidNodeClick" />
                    <!-- Mermaid HTML 预览 -->
                    <iframe v-else-if="isMermaidHtml" class="mermaid-html-preview" :srcdoc="editorContent" />
                    <!-- 图片文件预览 -->
                    <div v-else-if="isImageFile" class="image-preview">
                      <div class="image-container">
                        <img 
                          :src="imageDataUrl" 
                          :alt="currentFile.path" 
                          class="preview-image"
                          @load="onImageLoad"
                          @error="onImageError"
                        />
                        <div class="image-info">
                          <div class="image-filename">{{ currentFile.path.split('/').pop() }}</div>
                          <div v-if="imageInfo.width && imageInfo.height" class="image-dimensions">
                            {{ imageInfo.width }} × {{ imageInfo.height }} 像素
                          </div>
                          <div v-if="imageInfo.size" class="image-size">
                            {{ formatFileSize(imageInfo.size) }}
                          </div>
                        </div>
                      </div>
                    </div>
                    <!-- 视频文件预览 -->
                    <div v-else-if="isVideoFile" class="video-preview">
                      <div class="video-container">
                        <video 
                          :src="videoDataUrl" 
                          class="preview-video"
                          controls
                          preload="metadata"
                          @loadedmetadata="onVideoLoad"
                          @error="onVideoError"
                        >
                          Your browser does not support the video tag.
                        </video>
                        <div class="video-info">
                          <div class="video-filename">{{ currentFile.path.split('/').pop() }}</div>
                          <div v-if="videoInfo.duration" class="video-duration">
                            时长: {{ formatDuration(videoInfo.duration) }}
                          </div>
                          <div v-if="videoInfo.width && videoInfo.height" class="video-dimensions">
                            {{ videoInfo.width }} × {{ videoInfo.height }} 像素
                          </div>
                          <div v-if="videoInfo.size" class="video-size">
                            {{ formatFileSize(videoInfo.size) }}
                          </div>
                        </div>
                      </div>
                    </div>
                    <!-- 其他文件暂不支持预览 -->
                    <div v-else class="empty-preview"></div>
                  </template>
                  <template v-else>
                    <!-- 根据设置选择编辑器版本 -->
                    <CodeEditor
                      v-if="!useNewEditor"
                      v-model="editorContent"
                      :language="editorLanguage"
                      @save="saveCurrentFile"
                      ref="codeEditorRef"
                    />
                    <div v-else class="new-editor-placeholder">
                      <el-empty description="请选择文件或切换到新版编辑器" />
                    </div>
                  </template>
                </template>
              </div>
            </div>
          </div>

          <div v-else class="empty-editor">
            <el-empty description="Please select a file or create a new file">
              <el-button @click="addNewFile" type="primary">Create New File</el-button>
            </el-empty>
          </div>
        </div>

                 <!-- 数据流图预览切换栏 -->
         <div v-if="!useNewEditor && isDataflowYaml" class="mermaid-toggle-bar" @click="toggleMermaidSidebar">
           <div class="toggle-content">
                           <el-icon class="toggle-icon" :class="{ 'expanded': showMermaidSidebar }">
                <ArrowLeft v-if="!showMermaidSidebar" />
                <ArrowRight v-else />
              </el-icon>
                           <div class="toggle-text" v-if="showMermaidSidebar">
                <span class="toggle-label-expanded">关闭</span>
              </div>
              <el-icon class="preview-icon" v-else>
                <View />
              </el-icon>
           </div>
         </div>
        
        <!-- Mermaid 预览面板 -->
        <transition name="mermaid-slide">
          <div v-if="!useNewEditor && isDataflowYaml && showMermaidSidebar" class="mermaid-preview-sidebar" :style="{ width: mermaidSidebarWidth + 'px' }">
           <div class="mermaid-resize-handle" @mousedown="startResizeMermaid"></div>
                     <div class="mermaid-sidebar-header">
             <h4>数据流图</h4>
             <div class="mermaid-toolbar">
               <el-tooltip content="放大" placement="top">
                 <el-button size="small" text @click="zoomIn"><el-icon><Plus /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="缩小" placement="top">
                 <el-button size="small" text @click="zoomOut"><el-icon><Minus /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="重置" placement="top">
                 <el-button size="small" text @click="resetZoom"><el-icon><Refresh /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="新标签页打开" placement="top">
                 <el-button size="small" text @click="openMermaidInNewTab"><el-icon><Document /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="关闭" placement="top">
                 <el-button size="small" text @click="toggleMermaidSidebar"><el-icon><Close /></el-icon></el-button>
               </el-tooltip>
             </div>
           </div>
          
          <div v-if="mermaidHtmlFiles.length > 1" class="mermaid-file-selector">
            <el-select v-model="selectedMermaidHtml" @change="loadMermaidContent" size="small" style="width: 100%">
              <el-option 
                v-for="file in mermaidHtmlFiles" 
                :key="file" 
                :label="file.split('/').pop()" 
                :value="file" 
              />
            </el-select>
          </div>
          
          <div class="mermaid-preview-content">
            <div v-if="loadingMermaidContent" v-loading="true" class="mermaid-loading">
              加载中...
            </div>
            <div v-else-if="mermaidHtmlContent"
                 class="mermaid-zoom-wrapper"
                 :style="{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }">
              <iframe class="mermaid-content-iframe" :srcdoc="mermaidHtmlContent" />
            </div>
                         <div v-else class="mermaid-empty">
               <el-empty description="未找到 HTML 文件" size="small" />
             </div>
          </div>
        </div>
        </transition>
      </div>
      
      <!-- 全局终端面板 -->
      <div v-if="!useNewEditor" class="terminal-collapse-container">
        <div class="terminal-collapse-header" @click="showTerminal = !showTerminal">
          <div class="collapse-header-content">
            <el-icon class="collapse-icon" :class="{ 'collapsed': !showTerminal }">
              <ArrowUp />
            </el-icon>
            <span class="collapse-title">Terminal</span>
            <div class="terminal-status" v-if="showTerminal">
              <span class="status-dot connected"></span>
              <span class="status-text">Connected</span>
            </div>
          </div>
        </div>
        <transition name="terminal-slide">
          <div v-show="showTerminal" class="terminal-panel" :style="{ height: terminalHeight + 'px' }">
          <div class="terminal-resize-handle" @mousedown="startResizeTerminal"></div>
          <keep-alive>
            <TtydTerminal :embedded="true" />
          </keep-alive>
        </div>
        </transition>
      </div>
    </div>

    <!-- 新建文件对话框 -->
    <el-dialog v-model="newFileDialogVisible" title="Create New File" width="30%">
      <el-form :model="newFileForm" label-width="80px">
        <el-form-item label="File Name" required>
          <el-input v-model="newFileForm.fullName" placeholder="Example: helper.py">
          </el-input>
        </el-form-item>
        <el-form-item label="Directory">
          <el-input v-model="newFileForm.path" placeholder="Leave blank for root directory" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="newFileDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="createNewFile" :loading="isCreatingFile">
            Create
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 新建文件夹对话框 -->
    <el-dialog v-model="newFolderDialogVisible" title="Create New Folder" width="30%">
      <el-form :model="newFolderForm" label-width="80px">
        <el-form-item label="Folder Name" required>
          <el-input v-model="newFolderForm.folderName" placeholder="Example: utils">
          </el-input>
        </el-form-item>
        <el-form-item label="Directory">
          <el-input v-model="newFolderForm.path" placeholder="Leave blank for root directory" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="newFolderDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="createNewFolder" :loading="isCreatingFolder">
            Create
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 右键菜单 -->
    <div 
      v-if="contextMenuVisible" 
      class="context-menu" 
      :style="{ left: contextMenuPosition.x + 'px', top: contextMenuPosition.y + 'px' }"
      ref="contextMenuEl"
      @click.stop
      @contextmenu.prevent
    >
      <div class="context-menu-item" v-if="contextMenuData && contextMenuData.isDirectory" @click="handleRenameItem">
        <el-icon><Edit /></el-icon>
        <span>重命名</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && contextMenuData.isDirectory" @click="handleDeleteItem">
        <el-icon><Delete /></el-icon>
        <span>删除文件夹</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleRenameItem">
        <el-icon><Edit /></el-icon>
        <span>重命名</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleCopyItem">
        <el-icon><CopyDocument /></el-icon>
        <span>复制文件</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleDeleteItem">
        <el-icon><Delete /></el-icon>
        <span>删除文件</span>
      </div>
    </div>

    <!-- 右键菜单遮罩 -->
    <div v-if="contextMenuVisible" class="context-menu-overlay" @click="hideContextMenu"></div>

    <!-- 重命名对话框 -->
    <el-dialog v-model="renameDialogVisible" title="Rename" width="30%">
      <el-form :model="renameForm" label-width="80px">
        <el-form-item label="New Name" required>
          <el-input v-model="renameForm.newName" placeholder="Enter new name">
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="renameDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="confirmRename" :loading="isRenaming">
            Rename
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '../store/agent'
import { useSettingsStore } from '../store/settings'
import CodeEditor from '../components/editor/CodeEditor.vue'
import { Document, ArrowLeft, VideoPlay, VideoPause, Search, Plus, Minus, Refresh, Download, Setting, ArrowUp, ArrowRight, Close, View, Hide, Delete, CopyDocument, Edit, Folder, FolderAdd } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import MermaidViewer from '../components/MermaidViewer.vue'
import VSCodeEmbed from '../components/editor/VSCodeEmbed.vue'
import vscodeApi from '../api/vscode'
import TtydTerminal from './TtydTerminal.vue'

export default {
  name: 'AgentEdit',
  components: {
    CodeEditor,
    Document,
    ArrowLeft,
    VideoPlay,
    VideoPause,
    Search,
    Plus,
    Minus,
    Refresh,
    Download,
    Setting,
    ArrowUp,
    ArrowRight,
    Close,
    View,
    Hide,
    Delete,
    CopyDocument,
    Edit,
    Folder,
    FolderAdd,
    MermaidViewer,
    VSCodeEmbed,
    TtydTerminal
  },
  props: {
    agentName: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const router = useRouter()
    const route = useRoute()
    const agentStore = useAgentStore()
    const settingsStore = useSettingsStore()
    const md = new MarkdownIt()

    // 状态变量
    const isLoading = computed(() => agentStore.isLoading)
    const error = computed(() => agentStore.error)
    const fileTree = ref(null)
    const fileSearchQuery = ref('')
    const fileTreeData = ref([])
    const currentFile = ref(null)
    const originalContent = ref('')
    const editorContent = ref('')
    const hasChanges = computed(() => editorContent.value !== originalContent.value)
    const isSaving = ref(false)
    const previewMode = ref(false)
    const activeYamlTab = ref('yaml')
    const showYamlTabs = ref(false)
    const isAgentRunning = computed(() => agentStore.isAgentRunning(props.agentName))
    
    // 是否使用新版编辑器
    const useNewEditor = computed(() => settingsStore.settings.editor_version === 'new')

    // 新建文件相关
    const newFileDialogVisible = ref(false)
    const newFileForm = ref({
      fullName: '',
      path: ''
    })
    const isCreatingFile = ref(false)
    
    // 新建文件夹相关
    const newFolderDialogVisible = ref(false)
    const newFolderForm = ref({
      folderName: '',
      path: ''
    })
    const isCreatingFolder = ref(false)
    
    // 右键菜单相关
    const contextMenuData = ref(null)
    const renameDialogVisible = ref(false)
    const renameForm = ref({
      newName: ''
    })
    const isRenaming = ref(false)

    // 计算属性
    const defaultProps = {
      children: 'children',
      label: 'label'
    }

    const editorLanguage = computed(() => {
      if (!currentFile.value) return 'python'
      
      const ext = currentFile.value.path.split('.').pop().toLowerCase()
      const langMap = {
        'py': 'python',
        'js': 'javascript',
        'md': 'markdown',
        'yml': 'yaml',
        'yaml': 'yaml',
        'json': 'json',
        'toml': 'toml',
        'env': 'plaintext',
        'txt': 'plaintext'
      }
      return langMap[ext] || 'plaintext'
    })
    
    const isMarkdownFile = computed(() => {
      if (!currentFile.value) return false
      return currentFile.value.path.toLowerCase().endsWith('.md')
    })
    
    const renderedMarkdown = computed(() => {
      return md.render(editorContent.value || '')
    })

    const isYaml = computed(() => currentFile.value && (currentFile.value.path.endsWith('.yml') || currentFile.value.path.endsWith('.yaml')))
    const isDataflowYaml = computed(() => {
      if (!isYaml.value) return false
      const pathMatch = currentFile.value.path.includes('dataflow')
      const contentMatch = editorContent.value && editorContent.value.trimStart().startsWith('nodes:')
      return pathMatch || contentMatch
    })
    const mermaidCode = ref('')
    // 新增：是否为 Mermaid HTML
    const isMermaidHtml = computed(() => {
      if (!currentFile.value) return false
      const lowerPath = currentFile.value.path.toLowerCase()
      return lowerPath.endsWith('.html') && lowerPath.includes('graph')
    })

    // 新增：检测图片文件
    const isImageFile = computed(() => {
      if (!currentFile.value) return false
      const lowerPath = currentFile.value.path.toLowerCase()
      const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico']
      return imageExtensions.some(ext => lowerPath.endsWith(ext))
    })

    // 新增：检测视频文件
    const isVideoFile = computed(() => {
      if (!currentFile.value) return false
      const lowerPath = currentFile.value.path.toLowerCase()
      const videoExtensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp']
      return videoExtensions.some(ext => lowerPath.endsWith(ext))
    })

    // 获取图片文件的数据 URL
    const imageDataUrl = ref('')
    
    // 图片信息
    const imageInfo = ref({
      width: null,
      height: null,
      size: null
    })

    // 获取视频文件的数据 URL
    const videoDataUrl = ref('')
    
    // 视频信息
    const videoInfo = ref({
      width: null,
      height: null,
      duration: null,
      size: null
    })

    // 计算 VSCode Web 需要打开的文件夹路径
    const agentFolderPath = computed(() => {
      let baseDir = settingsStore.settings.mofa_dir || ''
      const name = props.agentName
      // 判断 Agent 类型（hub / examples）
      if (agentStore.hubAgents.includes(name)) {
        baseDir = settingsStore.settings.agent_hub_path || baseDir
      } else if (agentStore.exampleAgents.includes(name)) {
        baseDir = settingsStore.settings.examples_path || baseDir
      }
      // 去除尾部斜杠
      const trimmed = baseDir.replace(/\/$/, '')
      return `${trimmed}/${name}`
    })

    const vscodePort = ref(null)

    const vscodeBaseUrl = computed(() => {
       // 使用动态端口优先
       if (vscodePort.value) {
         const host = window.location.hostname || 'localhost'
         const protocol = window.location.protocol || 'http:'
         return `${protocol}//${host}:${vscodePort.value}`
       }
       // 使用集成的 code-server，默认端口 8080
       const envUrl = import.meta.env.VITE_VSCODE_WEB_URL
       if (envUrl) return envUrl

       const envPort = import.meta.env.VITE_VSCODE_WEB_PORT || '8080'
       const host = window.location.hostname || 'localhost'
       const protocol = window.location.protocol || 'http:'
       return `${protocol}//${host}:${envPort}`
     })

    // VS Code 状态管理
    const vscodeStatus = ref({
      running: false,
      loading: false,
      error: null
    })

    // 新增：终端高度和 Mermaid 侧栏宽度，可拖拽调整
    const terminalHeight = ref(300)
    const mermaidSidebarWidth = ref(280)
    // 新增：文件树侧边栏宽度
    const fileSidebarWidth = ref(220)

    // 启动 VS Code 服务
    const startVSCodeServer = async () => {
      vscodeStatus.value.loading = true
      vscodeStatus.value.error = null
      
      try {
        const result = await vscodeApi.startVSCode(props.agentName)
        if (result.success) {
          vscodeStatus.value.running = true
          vscodePort.value = result.port || 8080
          ElMessage.success('VS Code Web 启动成功')
        } else {
          vscodeStatus.value.error = result.error
          ElMessage.error(`启动失败: ${result.error}`)
        }
      } catch (error) {
        vscodeStatus.value.error = error.message
        ElMessage.error(`启动失败: ${error.message}`)
      } finally {
        vscodeStatus.value.loading = false
      }
    }

    // 检查 VS Code 状态
    const checkVSCodeStatus = async () => {
      try {
        const result = await vscodeApi.getVSCodeStatus()
        if (result.success) {
          vscodeStatus.value.running = result.running
          if (result.port) vscodePort.value = result.port
        }
      } catch (error) {
        console.warn('Failed to check VS Code status:', error)
      }
    }

    // 安装推荐扩展
    const installExtensions = async () => {
      ElMessage.info('正在安装 VS Code 扩展...')
      try {
        const result = await vscodeApi.installExtensions(props.agentName)
        if (result.success) {
          ElMessage.success(`扩展安装完成: ${result.installed.length} 个成功, ${result.failed.length} 个失败`)
        } else {
          ElMessage.error(`扩展安装失败: ${result.error}`)
        }
      } catch (error) {
        ElMessage.error(`扩展安装失败: ${error.message}`)
      }
    }

    // 更新 VS Code 配置
    const updateVSCodeConfig = async () => {
      try {
        const result = await vscodeApi.updateConfig(props.agentName)
        if (result.success) {
          ElMessage.success('VS Code 配置已更新')
        } else {
          ElMessage.error(`配置更新失败: ${result.error}`)
        }
      } catch (error) {
        ElMessage.error(`配置更新失败: ${error.message}`)
      }
    }

    watch(editorContent, async (newVal) => {
      if (isDataflowYaml.value) {
        // call backend to generate mermaid
        try {
          const resp = await fetch('/api/mermaid/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ yaml: newVal })
          })
          const data = await resp.json()
          if (data.success) mermaidCode.value = data.mermaid
        } catch (e) { }
      }
    }, { immediate: true })

    // 方法
    const goBack = () => {
      // 如果有未保存的更改，提示保存
      if (hasChanges.value) {
        ElMessageBox.confirm(
          '有未保存的更改，是否保存后再离开？',
          '未保存的更改',
          {
            confirmButtonText: '保存并离开',
            cancelButtonText: '放弃更改',
            type: 'warning',
            distinguishCancelAndClose: true
          }
        )
          .then(async () => {
            await saveCurrentFile()
            router.push('/agents')
          })
          .catch((action) => {
            if (action === 'cancel') {
              router.push('/agents')
            }
          })
      } else {
        router.push('/agents')
      }
    }

    const loadAgentFiles = async () => {
      try {
        // 从路由查询参数中获取agent类型
        const agentType = route.query.type || null
        const files = await agentStore.fetchAgentFiles(props.agentName, agentType)
        generateFileTree(files)
      } catch (err) {
        ElMessage.error(`Failed to load Agent files: ${err.message}`)
      }
    }

    const generateFileTree = (files) => {
      const treeData = []
      const fileMap = {}
      
      // 创建根目录节点
      fileMap[''] = {
        label: props.agentName,
        path: '',
        children: [],
        isDirectory: true
      }
      treeData.push(fileMap[''])
      
      // 处理每个文件
      files.forEach(file => {
        const pathParts = file.path.split('/')
        const fileName = pathParts.pop()
        const dirPath = pathParts.join('/')
        
        // 确保目录路径存在
        if (dirPath && !fileMap[dirPath]) {
          // 创建缺失的目录路径
          let currentPath = ''
          pathParts.forEach(part => {
            const prevPath = currentPath
            currentPath = currentPath ? `${currentPath}/${part}` : part
            
            if (!fileMap[currentPath]) {
              const dirNode = {
                label: part,
                path: currentPath,
                children: [],
                isDirectory: true
              }
              fileMap[currentPath] = dirNode
              
              if (prevPath) {
                fileMap[prevPath].children.push(dirNode)
              } else {
                fileMap[''].children.push(dirNode)
              }
            }
          })
        }
        
        // 创建文件节点
        const fileNode = {
          label: fileName,
          path: file.path,
          isDirectory: false,
          fileType: file.type
        }
        
        // 添加到父目录
        const parentDir = fileMap[dirPath] || fileMap['']
        parentDir.children.push(fileNode)
      })
      
      // 排序 - 目录在前，文件在后，按字母排序
      const sortNodes = (nodes) => {
        nodes.sort((a, b) => {
          if (a.isDirectory && !b.isDirectory) return -1
          if (!a.isDirectory && b.isDirectory) return 1
          return a.label.localeCompare(b.label)
        })
        
        nodes.forEach(node => {
          if (node.children) {
            sortNodes(node.children)
          }
        })
      }
      
      sortNodes(treeData)
      fileTreeData.value = treeData
    }

    const fileTreeWrapper = ref(null)
    const fileTreeScrollTop = ref(0)

    const rememberFileTreeScroll = () => {
      if (fileTreeWrapper.value) {
        fileTreeScrollTop.value = fileTreeWrapper.value.scrollTop
      }
    }

    const restoreFileTreeScroll = () => {
      nextTick(() => {
        if (fileTreeWrapper.value) {
          fileTreeWrapper.value.scrollTop = fileTreeScrollTop.value
        }
      })
    }

    const handleFileClick = async (data) => {
      console.log('handleFileClick called with:', data)
      if (data.isDirectory) return
      
      // 如果当前有未保存的更改，提示保存
      if (currentFile.value && hasChanges.value) {
        try {
          await ElMessageBox.confirm(
            '有未保存的更改，是否保存？',
            '未保存的更改',
            {
              confirmButtonText: '保存',
              cancelButtonText: '放弃更改',
              type: 'warning'
            }
          )
          await saveCurrentFile()
        } catch (e) {
          // 用户选择放弃更改，继续打开新文件
        }
      }
      
      console.log('Loading file content for:', data.path)
      await loadFileContent(data.path)
      restoreFileTreeScroll()
    }

    const loadFileContent = async (filePath) => {
      try {
        // 从路由查询参数中获取agent类型
        const agentType = route.query.type || null
        
        // 检查是否为图片或视频文件
        const lowerPath = filePath.toLowerCase()
        const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.bmp', '.ico']
        const videoExtensions = ['.mp4', '.webm', '.ogg', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp']
        const isImage = imageExtensions.some(ext => lowerPath.endsWith(ext))
        const isVideo = videoExtensions.some(ext => lowerPath.endsWith(ext))
        
        if (isImage) {
          // 对于图片文件，直接设置文件信息，不获取文本内容
          currentFile.value = {
            path: filePath,
            type: 'image'
          }
          originalContent.value = '' // 图片文件没有文本内容
          editorContent.value = ''
          
          // 清空旧的图片数据
          if (imageDataUrl.value) {
            URL.revokeObjectURL(imageDataUrl.value)
            imageDataUrl.value = ''
          }
          imageInfo.value = { width: null, height: null, size: null }
          
          try {
            // 构建正确的API路径
            const encodedPath = filePath.split('/').map(segment => encodeURIComponent(segment)).join('/')
            const queryParams = agentType ? `?agent_type=${agentType}` : ''
            const response = await fetch(`/api/agents/${props.agentName}/files/${encodedPath}${queryParams}`)
            
            if (response.ok) {
              const blob = await response.blob()
              imageDataUrl.value = URL.createObjectURL(blob)
              // 保存图片大小信息
              imageInfo.value.size = blob.size
              previewMode.value = true // 图片文件自动进入预览模式
              console.log('图片加载成功:', filePath, '大小:', blob.size)
            } else {
              console.error('Failed to load image:', response.status, response.statusText)
              ElMessage.error('Failed to load image file')
            }
          } catch (e) {
            console.error('Failed to load image:', e)
            ElMessage.error('Failed to load image file')
          }
        } else if (isVideo) {
          // 对于视频文件，直接设置文件信息，不获取文本内容
          currentFile.value = {
            path: filePath,
            type: 'video'
          }
          originalContent.value = '' // 视频文件没有文本内容
          editorContent.value = ''
          
          // 清空旧的视频数据
          if (videoDataUrl.value) {
            URL.revokeObjectURL(videoDataUrl.value)
            videoDataUrl.value = ''
          }
          videoInfo.value = { width: null, height: null, duration: null, size: null }
          
          try {
            // 构建正确的API路径
            const encodedPath = filePath.split('/').map(segment => encodeURIComponent(segment)).join('/')
            const queryParams = agentType ? `?agent_type=${agentType}` : ''
            const response = await fetch(`/api/agents/${props.agentName}/files/${encodedPath}${queryParams}`)
            
            if (response.ok) {
              const blob = await response.blob()
              videoDataUrl.value = URL.createObjectURL(blob)
              // 保存视频大小信息
              videoInfo.value.size = blob.size
              previewMode.value = true // 视频文件自动进入预览模式
              console.log('视频加载成功:', filePath, '大小:', blob.size)
            } else {
              console.error('Failed to load video:', response.status, response.statusText)
              ElMessage.error('Failed to load video file')
            }
          } catch (e) {
            console.error('Failed to load video:', e)
            ElMessage.error('Failed to load video file')
          }
        } else {
          // 对于非图片/视频文件，使用原有逻辑获取文本内容
          const fileData = await agentStore.fetchFileContent(props.agentName, filePath, agentType)
          if (fileData) {
            currentFile.value = {
              path: filePath,
              type: fileData.type
            }
            originalContent.value = fileData.content
            editorContent.value = fileData.content
            
            // 清空图片和视频数据URL和信息
            if (imageDataUrl.value) {
              URL.revokeObjectURL(imageDataUrl.value)
              imageDataUrl.value = ''
            }
            if (videoDataUrl.value) {
              URL.revokeObjectURL(videoDataUrl.value)
              videoDataUrl.value = ''
            }
            imageInfo.value = { width: null, height: null, size: null }
            videoInfo.value = { width: null, height: null, duration: null, size: null }
            // 如果是 Mermaid HTML，则自动进入预览模式
            previewMode.value = isMermaidHtml.value
          }
        }
      } catch (err) {
        console.error('Failed to load file content:', err)
        ElMessage.error(`Failed to load file content: ${err.message}`)
      }
    }

    const saveCurrentFile = async () => {
      if (!currentFile.value || !hasChanges.value) return
      
      isSaving.value = true
      try {
        const result = await agentStore.saveFileContent(
          props.agentName,
          currentFile.value.path,
          editorContent.value
        )
        
        if (result) {
          originalContent.value = editorContent.value
          ElMessage.success('File saved successfully')

          // 如果是 dataflow YAML，调用后端导出 HTML
          if (isDataflowYaml.value) {
            try {
              const resp = await fetch('/api/mermaid/export', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  agent: props.agentName,
                  yaml_path: currentFile.value.path,
                  yaml: editorContent.value
                })
              })
              const data = await resp.json()
              if (data.success) {
                // ElMessage.success('Mermaid HTML 生成成功: ' + data.html_path)
                // 刷新 mermaidHtmlFiles，下次侧边栏可见
                scanMermaidHtmlFiles()
                await loadAgentFiles()
              } else {
                console.warn('Mermaid export failed', data)
              }
            } catch (e) {
              console.error('Mermaid export error', e)
            }
          }
        } else {
          ElMessage.error(`Failed to save file: ${error.value}`)
        }
      } catch (err) {
        ElMessage.error(`Failed to save file: ${err.message}`)
      } finally {
        isSaving.value = false
      }
    }

    const togglePreviewMode = () => {
      previewMode.value = !previewMode.value
    }

    const filterNode = (value, data) => {
      if (!value) return true
      return data.label.toLowerCase().includes(value.toLowerCase())
    }

    const addNewFile = () => {
      newFileForm.value = {
        fullName: '',
        path: ''
      }
      newFileDialogVisible.value = true
    }

    const createNewFile = async () => {
      if (!newFileForm.value.fullName.trim()) {
        ElMessage.warning('Please enter a file name')
        return
      }
      
      isCreatingFile.value = true
      try {
        const filePath = newFileForm.value.path 
          ? `${newFileForm.value.path}/${newFileForm.value.fullName}`
          : newFileForm.value.fullName
        
        // Extract file extension for default content
        const fileNameParts = newFileForm.value.fullName.split('.')
        const ext = fileNameParts.length > 1 ? fileNameParts.pop().toLowerCase() : ''
        const fileName = fileNameParts.join('.')
        
        // 对于图片或视频文件，不创建默认内容，直接创建空文件
        const imageExtensions = ['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'bmp', 'ico']
        const videoExtensions = ['mp4', 'webm', 'ogg', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', '3gp']
        if (imageExtensions.includes(ext)) {
          ElMessage.info('图片文件已创建，请使用外部工具编辑后上传')
          const result = await agentStore.saveFileContent(props.agentName, filePath, '')
          if (result) {
            ElMessage.success('图片文件占位符已创建')
            newFileDialogVisible.value = false
            await loadAgentFiles()
          } else {
            ElMessage.error(`Failed to create file: ${error.value}`)
          }
          isCreatingFile.value = false
          return
        } else if (videoExtensions.includes(ext)) {
          ElMessage.info('视频文件已创建，请使用外部工具编辑后上传')
          const result = await agentStore.saveFileContent(props.agentName, filePath, '')
          if (result) {
            ElMessage.success('视频文件占位符已创建')
            newFileDialogVisible.value = false
            await loadAgentFiles()
          } else {
            ElMessage.error(`Failed to create file: ${error.value}`)
          }
          isCreatingFile.value = false
          return
        }
        
        // 创建默认内容
        let defaultContent = ''
          
        switch (ext) {
          case 'py':
            defaultContent = `# ${fileName}.py\n# Created in MoFA_Stage\n\ndef main():\n    print("Hello from ${fileName}")\n\nif __name__ == "__main__":\n    main()\n`
            break
          case 'md':
            defaultContent = `# ${fileName}\n\n## Overview\n\nThis is a new file created in MoFA_Stage.\n`
            break
          case 'yml':
          case 'yaml':
            defaultContent = `# ${fileName}.${ext}\n# Configuration file\n\nname: ${props.agentName}\n`
            break
          case 'env':
            defaultContent = `# Environment variables for ${props.agentName}\n\nDEBUG=True\n`
            break
          case 'json':
            defaultContent = `{\n  "name": "${props.agentName}",\n  "description": "A MoFA agent",\n  "version": "1.0.0",\n  "created": "${new Date().toISOString()}"\n}\n`
            break
          case 'js':
            defaultContent = `// ${fileName}.js\n// Created in MoFA_Stage\n\nfunction main() {\n  console.log("Hello from ${fileName}");\n}\n\nmain();\n`
            break
          case 'ts':
            defaultContent = `// ${fileName}.ts\n// Created in MoFA_Stage\n\nfunction main(): void {\n  console.log("Hello from ${fileName}");\n}\n\nmain();\n`
            break
          case 'html':
            defaultContent = `<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>${fileName}</title>\n</head>\n<body>\n  <h1>Hello from ${props.agentName}</h1>\n</body>\n</html>\n`
            break
          case 'css':
            defaultContent = `/* ${fileName}.css */\n/* Created in MoFA_Stage */\n\nbody {\n  font-family: Arial, sans-serif;\n  margin: 0;\n  padding: 20px;\n}\n`
            break
          case 'sh':
            defaultContent = `#!/bin/bash\n# ${fileName}.sh\n# Created in MoFA_Stage\n\necho "Hello from ${props.agentName}"\n`
            break
          case 'toml':
            defaultContent = `# ${fileName}.toml\n# Created in MoFA_Stage\n\n[package]\nname = "${props.agentName}"\nversion = "0.1.0"\n`
            break
          default:
            // 对于未知扩展名或无扩展名，提供一个通用的默认内容
            defaultContent = `# ${newFileForm.value.fullName}\n# Created in MoFA_Stage for ${props.agentName}\n\n`
            break
        }
        
        const result = await agentStore.saveFileContent(
          props.agentName,
          filePath,
          defaultContent
        )
        
        if (result) {
          ElMessage.success('File created successfully')
          newFileDialogVisible.value = false
          
          // 重新加载文件列表并打开新文件
          await loadAgentFiles()
          loadFileContent(filePath)
        } else {
          ElMessage.error(`Failed to create file: ${error.value}`)
        }
      } catch (err) {
        ElMessage.error(`Failed to create file: ${err.message}`)
      } finally {
        isCreatingFile.value = false
      }
    }

    // 新建文件夹
    const addNewFolder = () => {
      newFolderForm.value = {
        folderName: '',
        path: ''
      }
      newFolderDialogVisible.value = true
    }

    const createNewFolder = async () => {
      if (!newFolderForm.value.folderName.trim()) {
        ElMessage.warning('Please enter a folder name')
        return
      }
      
      isCreatingFolder.value = true
      try {
        const folderPath = newFolderForm.value.path 
          ? `${newFolderForm.value.path}/${newFolderForm.value.folderName}`
          : newFolderForm.value.folderName
        
        // 创建一个临时文件在文件夹内，然后删除，这样可以创建文件夹
        const tempFilePath = `${folderPath}/.gitkeep`
        
        const result = await agentStore.saveFileContent(
          props.agentName,
          tempFilePath,
          '# This file keeps the folder in git\n'
        )
        
        if (result) {
          ElMessage.success('Folder created successfully')
          newFolderDialogVisible.value = false
          
          // 重新加载文件列表
          await loadAgentFiles()
        } else {
          ElMessage.error(`Failed to create folder: ${error.value}`)
        }
      } catch (err) {
        ElMessage.error(`Failed to create folder: ${err.message}`)
      } finally {
        isCreatingFolder.value = false
      }
    }

    // 右键菜单处理
    const contextMenuVisible = ref(false)
    const contextMenuPosition = ref({ x: 0, y: 0 })
    
    const contextMenuEl = ref(null)

    const handleFileRightClick = (event, data) => {
      event.preventDefault()
      event.stopPropagation()
      
      contextMenuData.value = data
      
      // 优先使用鼠标位置作为菜单定位起点
      let x = event.clientX - 220
      let y = event.clientY - 60
      
      contextMenuPosition.value = { x, y }
      contextMenuVisible.value = true
      
      // 下一帧调整位置，确保不超出视口
      nextTick(() => {
        const el = contextMenuEl.value
        if (!el) return
        
        const menuRect = el.getBoundingClientRect()
        let adjustedX = x
        let adjustedY = y
        const padding = 8
        
        // 防止菜单超出右边界
        if (adjustedX + menuRect.width > window.innerWidth) {
          adjustedX = window.innerWidth - menuRect.width - padding
        }
        
        // 防止菜单超出左边界
        if (adjustedX < 0) {
          adjustedX = padding
        }
        
        // 防止菜单超出下边界
        if (adjustedY + menuRect.height > window.innerHeight) {
          adjustedY = window.innerHeight - menuRect.height - padding
        }
        
        // 防止菜单超出上边界
        if (adjustedY < 0) {
          adjustedY = padding
        }
        
        contextMenuPosition.value = { x: adjustedX, y: adjustedY }
      })
    }

    const hideContextMenu = () => {
      contextMenuVisible.value = false
    }

    const handleRenameItem = () => {
      if (!contextMenuData.value) return
      
      renameForm.value.newName = contextMenuData.value.label
      renameDialogVisible.value = true
      hideContextMenu()
    }

    const handleCopyItem = async () => {
      if (!contextMenuData.value || contextMenuData.value.isDirectory) return
      hideContextMenu()
      
      try {
        const fileData = await agentStore.fetchFileContent(props.agentName, contextMenuData.value.path)
        if (fileData) {
          // 生成新文件名 - 改进文件名处理逻辑
          const pathParts = contextMenuData.value.path.split('/')
          const fileName = pathParts.pop()
          const filePath = pathParts.join('/')
          
          // 更好的文件扩展名处理
          const lastDotIndex = fileName.lastIndexOf('.')
          let baseName, ext
          
          if (lastDotIndex > 0 && lastDotIndex < fileName.length - 1) {
            // 有有效的扩展名
            baseName = fileName.substring(0, lastDotIndex)
            ext = fileName.substring(lastDotIndex) // 包含点号
          } else {
            // 没有扩展名或点号在开头/结尾
            baseName = fileName
            ext = ''
          }
          
          const newFileName = `${baseName}_copy${ext}`
          const newFilePath = filePath ? `${filePath}/${newFileName}` : newFileName
          
          const result = await agentStore.saveFileContent(
            props.agentName,
            newFilePath,
            fileData.content
          )
          
          if (result) {
            ElMessage.success('File copied successfully')
            await loadAgentFiles()
          } else {
            ElMessage.error('Failed to copy file')
          }
        }
      } catch (err) {
        ElMessage.error(`Failed to copy file: ${err.message}`)
      }
    }

    const handleDeleteItem = async () => {
      if (!contextMenuData.value) return
      hideContextMenu()
      
      const itemType = contextMenuData.value.isDirectory ? '文件夹' : '文件'
      const itemName = contextMenuData.value.label
      
      try {
        await ElMessageBox.confirm(
          `确定要删除这个${itemType}吗: ${itemName}?`,
          `删除${itemType}`,
          {
            confirmButtonText: '删除',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        // 调用后端删除接口
        const success = await agentStore.deleteFileOrFolder(props.agentName, contextMenuData.value.path)
        if (success) {
          ElMessage.success(`${itemType}已删除`)
          await loadAgentFiles()
          // 如果删除的是当前打开文件，清空编辑器
          if (currentFile.value && currentFile.value.path === contextMenuData.value.path) {
            currentFile.value = null
            editorContent.value = ''
          }
        } else {
          ElMessage.error(`删除${itemType}失败`)
        }
        
      } catch (e) {
        // 用户取消删除
      }
    }

    const confirmRename = async () => {
      if (!contextMenuData.value || !renameForm.value.newName.trim()) {
        ElMessage.warning('请输入新名称')
        return
      }
      
      if (renameForm.value.newName === contextMenuData.value.label) {
        renameDialogVisible.value = false
        return
      }
      
      isRenaming.value = true
      try {
        // 调用后端重命名API
        const result = await agentStore.renameFileOrFolder(
          props.agentName, 
          contextMenuData.value.path, 
          renameForm.value.newName
        )
        
        if (result.success) {
          ElMessage.success(`${result.message}`)
          renameDialogVisible.value = false
          // 重新加载文件列表以反映更改
          await loadAgentFiles()
          
          // 如果重命名的是当前打开的文件，更新当前文件路径
          if (currentFile.value && currentFile.value.path === contextMenuData.value.path) {
            currentFile.value.path = result.newPath
          }
        } else {
          ElMessage.error(`重命名失败: ${result.error}`)
        }
        
      } catch (err) {
        ElMessage.error(`重命名失败: ${err.message}`)
      } finally {
        isRenaming.value = false
      }
    }

    const runAgent = async () => {
      const result = await agentStore.runAgent(props.agentName)
      if (result.success) {
        ElMessage.success(`Agent ${props.agentName} started successfully`)
      } else {
        ElMessage.error(`Failed to start Agent: ${result.error}`)
      }
    }

    const stopAgent = async () => {
      const result = await agentStore.stopAgent(props.agentName)
      if (result.success) {
        ElMessage.success(`Agent ${props.agentName} stopped successfully`)
      } else {
        ElMessage.error(`Failed to stop Agent: ${result.error}`)
      }
    }

    // 监听搜索词变化
    watch(fileSearchQuery, (val) => {
      fileTree.value?.filter(val)
    })

    const showTerminal = ref(false)

    // Mermaid 预览相关
    const showMermaidSidebar = ref(false)
    const mermaidHtmlFiles = ref([])
    const selectedMermaidHtml = ref('')
    const mermaidHtmlContent = ref('')
    const loadingMermaidContent = ref(false)
    const zoomLevel = ref(1)

    const zoomIn = () => {
      zoomLevel.value = Math.min(zoomLevel.value + 0.1, 3)
    }

    const zoomOut = () => {
      zoomLevel.value = Math.max(zoomLevel.value - 0.1, 0.3)
    }

    const resetZoom = () => {
      zoomLevel.value = 1
    }

    // 当切换到非 dataflow YAML 文件时，自动关闭 Mermaid 侧边栏
    watch(isDataflowYaml, (val) => {
      if (!val) {
        showMermaidSidebar.value = false
      }
    })

    const openMermaidInNewTab = () => {
      if (!mermaidHtmlContent.value) return
      try {
        const blob = new Blob([mermaidHtmlContent.value], { type: 'text/html' })
        const url = URL.createObjectURL(blob)
        window.open(url, '_blank')
      } catch (e) {
        console.error('Failed to open Mermaid HTML in new tab', e)
      }
    }

    // 切换 Mermaid 侧边栏
    const toggleMermaidSidebar = async () => {
      showMermaidSidebar.value = !showMermaidSidebar.value
      
      if (showMermaidSidebar.value && mermaidHtmlFiles.value.length === 0) {
        // 首次打开时，扫描 mermaid HTML 文件
        await scanMermaidHtmlFiles()
      }
      
      if (showMermaidSidebar.value && selectedMermaidHtml.value && !mermaidHtmlContent.value) {
        // 加载选中文件内容
        await loadMermaidContent()
      }
    }

    // 扫描当前 agent 目录中的 HTML 文件
    const scanMermaidHtmlFiles = async () => {
      try {
        const files = await agentStore.fetchAgentFiles(props.agentName)
        const htmlFiles = files.filter(file => {
          const lowerPath = file.path.toLowerCase()
          return lowerPath.endsWith('.html')
        }).map(file => file.path)
        
        mermaidHtmlFiles.value = htmlFiles
        
        if (htmlFiles.length > 0) {
          selectedMermaidHtml.value = htmlFiles[0]
          await loadMermaidContent()
        }
      } catch (err) {
        console.error('Failed to scan HTML files:', err)
      }
    }

    // 加载 mermaid HTML 内容
    const loadMermaidContent = async () => {
      if (!selectedMermaidHtml.value) return
      
      loadingMermaidContent.value = true
      try {
        const fileData = await agentStore.fetchFileContent(props.agentName, selectedMermaidHtml.value)
        if (fileData) {
          mermaidHtmlContent.value = fileData.content
        }
             } catch (err) {
         ElMessage.error(`加载 HTML 失败: ${err.message}`)
       } finally {
        loadingMermaidContent.value = false
      }
    }

    // 拖拽调整终端高度
    const startResizeTerminal = (e) => {
      e.preventDefault()
      const startY = e.clientY
      const startH = terminalHeight.value
      const onMove = (m) => {
        terminalHeight.value = Math.min(600, Math.max(150, startH + (startY - m.clientY)))
      }
      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
      }
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    }

    // 拖拽调整 Mermaid 侧栏宽度
    const startResizeMermaid = (e) => {
      e.preventDefault()
      const startX = e.clientX
      const startW = mermaidSidebarWidth.value
      const onMove = (m) => {
        mermaidSidebarWidth.value = Math.min(600, Math.max(200, startW + (startX - m.clientX)))
      }
      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
      }
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    }

    // 拖拽调整文件树侧边栏宽度
    const startResizeFileSidebar = (e) => {
      e.preventDefault()
      const startX = e.clientX
      const startW = fileSidebarWidth.value
      const onMove = (m) => {
        fileSidebarWidth.value = Math.min(400, Math.max(180, startW + (m.clientX - startX)))
      }
      const onUp = () => {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
      }
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    }

    // add ref to CodeEditor
    const codeEditorRef = ref(null)

    const handleMermaidNodeClick = (nodeId) => {
      if (!codeEditorRef.value) return
      
      const lines = editorContent.value.split('\n')
      let start = -1
      
      // 查找包含指定nodeId的行
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const trimmed = line.trim()
        
        // 查找 "- id: nodeId" 这样的行
        if (trimmed.startsWith('- id:')) {
          const idPart = trimmed.substring(5).trim() // 去掉 "- id:" 部分
          if (idPart === nodeId) {
            start = i
            break
          }
        }
      }
      
      if (start === -1) return
      
      // 查找下一个 "- id:" 开始的行作为结束位置
      let end = lines.length - 1
      for (let j = start + 1; j < lines.length; j++) {
        const trimmed = lines[j].trim()
        if (trimmed.startsWith('- id:')) {
          end = j - 1
          break
        }
      }
      
      // monaco uses 1-based line numbers
      codeEditorRef.value.selectLines(start + 1, end + 2)
      
      // Switch to YAML tab if graph tab is active
      if (showYamlTabs.value) activeYamlTab.value = 'yaml'
    }

    // 监听来自Mermaid HTML iframe的消息
    const handleMermaidMessage = (event) => {
      if (event.data && event.data.type === 'mermaid-node-click') {
        const nodeId = event.data.nodeId
        handleMermaidNodeClick(nodeId)
      }
    }

    const fileTreeCollapsed = ref(false)

    const toggleFileTree = () => {
      fileTreeCollapsed.value = !fileTreeCollapsed.value
    }

    // 图片加载事件处理
    const onImageLoad = (event) => {
      const img = event.target
      imageInfo.value.width = img.naturalWidth
      imageInfo.value.height = img.naturalHeight
    }

    const onImageError = (event) => {
      console.error('Image load error:', event)
    }

    // 视频加载事件处理
    const onVideoLoad = (event) => {
      const video = event.target
      videoInfo.value.width = video.videoWidth
      videoInfo.value.height = video.videoHeight
      videoInfo.value.duration = video.duration
    }

    const onVideoError = (event) => {
      console.error('Video load error:', event)
    }

    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (!bytes) return ''
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(1024))
      return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
    }

    // 格式化时长
    const formatDuration = (seconds) => {
      if (!seconds || isNaN(seconds)) return ''
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      const secs = Math.floor(seconds % 60)
      
      if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
      } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`
      }
    }

    onMounted(async () => {
      await loadAgentFiles()
      // 如果使用新版编辑器，检查并启动 VS Code 服务
      if (useNewEditor.value) {
        await checkVSCodeStatus()
        if (!vscodeStatus.value.running) {
          await startVSCodeServer()
        }
      }
      
      // 监听全局点击事件，隐藏右键菜单
      document.addEventListener('click', hideContextMenu)
      
      // 监听来自Mermaid HTML iframe的消息
      window.addEventListener('message', handleMermaidMessage)
      
      // 临时：暴露selectLines方法到全局，方便控制台测试
      window.testSelectLines = (start, end) => {
        if (codeEditorRef.value) {
          codeEditorRef.value.selectLines(start, end)
        } else {
          console.log('编辑器未初始化或不可用')
        }
      }
    })
    
    onBeforeUnmount(() => {
      // 清理事件监听器
      document.removeEventListener('click', hideContextMenu)
      window.removeEventListener('message', handleMermaidMessage)
      // 清理图片和视频数据URL，防止内存泄漏
      if (imageDataUrl.value) {
        URL.revokeObjectURL(imageDataUrl.value)
      }
      if (videoDataUrl.value) {
        URL.revokeObjectURL(videoDataUrl.value)
      }
    })

    return {
      isLoading,
      fileTree,
      fileSearchQuery,
      fileTreeData,
      defaultProps,
      currentFile,
      editorContent,
      editorLanguage,
      hasChanges,
      isSaving,
      isMarkdownFile,
      previewMode,
      renderedMarkdown,
      isAgentRunning,
      newFileDialogVisible,
      newFileForm,
      isCreatingFile,
      goBack,
      handleFileClick,
      saveCurrentFile,
      togglePreviewMode,
      filterNode,
      addNewFile,
      createNewFile,
      runAgent,
      stopAgent,
      isYaml,
      isDataflowYaml,
      mermaidCode,
      useNewEditor,
      agentFolderPath,
      vscodeBaseUrl,
      vscodeStatus,
      startVSCodeServer,
      installExtensions,
      updateVSCodeConfig,
      showTerminal,
      isMermaidHtml,
      showMermaidSidebar,
      mermaidHtmlFiles,
      selectedMermaidHtml,
      mermaidHtmlContent,
      loadingMermaidContent,
      toggleMermaidSidebar,
      loadMermaidContent,
      activeYamlTab,
      showYamlTabs,
      zoomLevel,
      zoomIn,
      zoomOut,
      resetZoom,
      openMermaidInNewTab,
      fileTreeWrapper,
      rememberFileTreeScroll,
      restoreFileTreeScroll,
      terminalHeight,
      mermaidSidebarWidth,
      fileSidebarWidth,
      startResizeTerminal,
      startResizeMermaid,
      startResizeFileSidebar,
      codeEditorRef,
      handleMermaidNodeClick,
      // 新建文件夹相关
      newFolderDialogVisible,
      newFolderForm,
      isCreatingFolder,
      addNewFolder,
      createNewFolder,
      // 右键菜单相关
      contextMenuVisible,
      contextMenuPosition,
      contextMenuData,
      renameDialogVisible,
      renameForm,
      isRenaming,
      handleFileRightClick,
      handleRenameItem,
      handleCopyItem,
      handleDeleteItem,
      confirmRename,
      hideContextMenu,
      fileTreeCollapsed,
      toggleFileTree,
      contextMenuEl,
      // 图片预览相关
      isImageFile,
      imageDataUrl,
      imageInfo,
      onImageLoad,
      onImageError,
      formatFileSize,
      // 视频预览相关
      isVideoFile,
      videoDataUrl,
      videoInfo,
      onVideoLoad,
      onVideoError,
      formatDuration
    }
  }
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background-color: var(--background-color);
}

.page-header {
  margin-bottom: 12px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.main-edit-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.edit-container {
  display: flex;
  flex: 1;
  background-color: #fff;
  border-radius: 4px;
  box-shadow: var(--card-shadow);
  overflow: hidden;
  min-height: 0;
}

.file-tree-sidebar {
  width: 220px;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative; /* 使手柄绝对定位 */
  transition: width .2s ease;
}

.file-tree-sidebar.collapsed {
  overflow: hidden;
}

.file-tree-resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 6px;
  cursor: col-resize;
  background-color: var(--border-color);
  z-index: 5;
}

.file-tree-collapse-btn {
  position: absolute;
  top: 12px;
  right: 8px;
  z-index: 10;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.file-tree-collapse-btn:hover {
  background-color: rgba(0, 0, 0, 0.1);
}

.file-tree-sidebar.collapsed .file-tree-collapse-btn {
  top: 50%;
  left: 0;
  right: 0;
  text-align: center;
  transform: translateY(-50%);
}

.sidebar-header {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.sidebar-footer {
  padding: 8px;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

/* 使文件树内容区域可滚动并占据剩余高度 */
.file-tree-wrapper {
  flex: 1;
  overflow-y: scroll; /* 始终显示滚动条 */
  overflow-x: hidden;
  /* 将滚动条放在左侧 */
  direction: rtl;
}

/* 还原文件树内容方向，避免文字颠倒 */
.file-tree-wrapper .el-tree {
  direction: ltr;
}

/* 自定义滚动条样式，确保在 macOS 上可见 */
.file-tree-wrapper::-webkit-scrollbar {
  width: 8px;
}

.file-tree-wrapper::-webkit-scrollbar-track {
  background: transparent;
}

.file-tree-wrapper::-webkit-scrollbar-thumb {
  background-color: rgba(0,0,0,0.25);
  border-radius: 4px;
}

/* Firefox */
.file-tree-wrapper {
  scrollbar-width: thin;
  scrollbar-color: rgba(0,0,0,0.25) transparent;
}

.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  background-color: #f9f9f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-path {
  font-family: monospace;
  font-size: 13px;
  color: var(--text-color-secondary);
}

.editor-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.code-editor-wrapper {
  flex: 1;
  overflow: hidden;
}

.empty-editor {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f9f9f9;
}

.markdown-preview {
  padding: 20px;
  overflow: auto;
  height: 100%;
}

.loading-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

/* VS Code Web 全屏容器 */
.vscode-full-container {
  width: 100%;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.new-editor-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f9f9f9;
}

.vscode-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.vscode-error {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.vscode-starting {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.terminal-panel {
  transition: height .2s ease;
  position: relative; /* 为拖拽手柄定位 */
  border-top: 1px solid var(--border-color);
}

.terminal-resize-handle {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
  cursor: row-resize;
  background-color: var(--border-color);
  z-index: 5;
}

.terminal-collapse-container {
  border-top: 1px solid var(--border-color);
}

.terminal-collapse-header {
  padding: 8px 10px;
  cursor: pointer;
  background-color: #f8f9fa;
  border-bottom: 1px solid var(--border-color);
  user-select: none;
}

.terminal-collapse-header:hover {
  background-color: #e9ecef;
}

.collapse-header-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.collapse-icon {
  transition: transform 0.3s ease;
}

.collapsed {
  transform: rotate(180deg);
}

.collapse-title {
  font-weight: 600;
  font-size: 14px;
}

.terminal-status {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.connected {
  background-color: #5cb85c;
}

.status-text {
  font-size: 11px;
  color: var(--text-color-secondary);
}

/* Mermaid HTML 预览 iframe */
.mermaid-html-preview {
  width: 100%;
  height: 100%;
  border: 0;
}

/* 图片预览样式 */
.image-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f9f9f9;
  padding: 20px;
  overflow: auto;
}

.image-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 100%;
  max-height: 100%;
}

.preview-image {
  max-width: 100%;
  max-height: calc(100% - 40px);
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  background-color: white;
  padding: 4px;
}

.image-info {
  margin-top: 12px;
  text-align: center;
}

.image-filename {
  font-size: 14px;
  color: var(--text-color);
  font-family: monospace;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  margin-bottom: 4px;
  font-weight: 600;
}

.image-dimensions, .image-size {
  font-size: 12px;
  color: var(--text-color-secondary);
  background-color: rgba(255, 255, 255, 0.8);
  padding: 3px 6px;
  border-radius: 4px;
  margin: 2px 0;
  display: inline-block;
  margin-right: 8px;
}

/* 视频预览样式 */
.video-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background-color: #f9f9f9;
  padding: 20px;
  overflow: auto;
}

.video-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 100%;
  max-height: 100%;
}

.preview-video {
  max-width: 100%;
  max-height: calc(100% - 40px);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  background-color: black;
}

.video-info {
  margin-top: 12px;
  text-align: center;
}

.video-filename {
  font-size: 14px;
  color: var(--text-color);
  font-family: monospace;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  margin-bottom: 4px;
  font-weight: 600;
}

.video-dimensions, .video-size, .video-duration {
  font-size: 12px;
  color: var(--text-color-secondary);
  background-color: rgba(255, 255, 255, 0.8);
  padding: 3px 6px;
  border-radius: 4px;
  margin: 2px 0;
  display: inline-block;
  margin-right: 8px;
}

/* 数据流图预览切换栏 */
.mermaid-toggle-bar {
  width: 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-left: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  position: relative;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

.mermaid-toggle-bar:hover {
  background: linear-gradient(135deg, #e9ecef 0%, #dee2e6 100%);
  box-shadow: 0 4px 8px rgba(0,0,0,0.12);
}

.toggle-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1px;
  padding: 4px 1px;
}

.toggle-icon {
  font-size: 11px;
  color: var(--primary-color);
  transition: all 0.3s ease;
}

.toggle-icon.expanded {
  color: var(--mofa-orange);
}

.toggle-text {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.toggle-text.vertical {
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.toggle-label {
  font-size: 9px;
  color: #666;
  font-weight: 500;
  line-height: 1.1;
  text-align: center;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.toggle-label-expanded {
  font-size: 10px;
  color: var(--mofa-orange);
  font-weight: 600;
}

.preview-icon {
  font-size: 9px;
  color: #999;
  opacity: 0.8;
}

.mermaid-toggle-bar:hover .toggle-icon {
  transform: scale(1.1);
}

.mermaid-toggle-bar:hover .toggle-label {
  color: var(--primary-color);
}

.mermaid-toggle-bar:hover .preview-icon {
  opacity: 1;
  color: var(--primary-color);
}

/* Mermaid 预览面板 */
.mermaid-preview-sidebar {
  position: relative; /* 为拖拽手柄定位 */
  transition: width .2s ease;
  width: 280px;
  border-left: 1px solid var(--border-color);
  background-color: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
}

.mermaid-resize-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 6px;
  cursor: col-resize;
  background-color: var(--border-color);
  z-index: 5;
}

.mermaid-sidebar-header {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #f9f9f9;
}

.mermaid-sidebar-header h4 {
  margin: 0;
  font-size: 13px;
  color: var(--text-color);
}

.mermaid-file-selector {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}

.mermaid-preview-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
}

.mermaid-content-iframe {
  width: 100%;
  height: 100%;
  border: 0;
}

.mermaid-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: var(--text-color-secondary);
}

.mermaid-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.yaml-preview-tabs, .yaml-preview-tabs > .el-tabs__content, .yaml-preview-tabs .el-tab-pane {
  height: 100%;
}

.yaml-preview-tabs .el-tab-pane {
  padding: 0;
}

.mermaid-toolbar .el-button {
  margin-left: 2px;
  padding: 6px 8px;
}

.mermaid-zoom-wrapper {
  overflow: auto;
  height: 100%;
}

/* 自定义按钮颜色 */
.custom-save-btn {
  background-color: #6DCACE !important;
  border-color: #6DCACE !important;
  color: white !important;
}

.custom-save-btn:hover {
  background-color: #5bb5b8 !important;
  border-color: #5bb5b8 !important;
  color: white !important;
}

.custom-save-btn:active,
.custom-save-btn:focus {
  background-color: #4da0a3 !important;
  border-color: #4da0a3 !important;
  color: white !important;
}

.custom-save-btn.is-disabled {
  background-color: #a8d8da !important;
  border-color: #a8d8da !important;
  color: white !important;
  opacity: 0.6;
}

.custom-run-btn {
  background-color: #FF5640 !important;
  border-color: #FF5640 !important;
  color: white !important;
}

.custom-run-btn:hover {
  background-color: #e6492e !important;
  border-color: #e6492e !important;
  color: white !important;
}

.custom-run-btn:active,
.custom-run-btn:focus {
  background-color: #cc3d1f !important;
  border-color: #cc3d1f !important;
  color: white !important;
}

/* 全局优化按钮和输入框尺寸 */
:deep(.el-button.el-button--small) {
  padding: 6px 12px;
  font-size: 13px;
}

:deep(.el-input.el-input--small .el-input__wrapper) {
  padding: 1px 8px;
}

:deep(.el-input.el-input--small .el-input__inner) {
  font-size: 13px;
  height: 28px;
}

:deep(.el-tree-node__content) {
  height: 24px;
  font-size: 13px;
}

:deep(.el-tree-node__label) {
  font-size: 13px;
}

:deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 16px;
  height: 36px;
  line-height: 36px;
}

/* Markdown 预览内容优化 */
.markdown-preview {
  padding: 16px;
  overflow: auto;
  height: 100%;
}

.markdown-preview h1 { font-size: 1.5em; margin: 0.5em 0; }
.markdown-preview h2 { font-size: 1.3em; margin: 0.4em 0; }
.markdown-preview h3 { font-size: 1.1em; margin: 0.3em 0; }
.markdown-preview p { margin: 0.3em 0; line-height: 1.4; }
.markdown-preview code { font-size: 12px; }
.markdown-preview pre { font-size: 12px; line-height: 1.3; }

/* 终端展开动画 */
.terminal-slide-enter-active,
.terminal-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: top;
}

.terminal-slide-enter-from {
  height: 0px !important;
  opacity: 0;
  transform: scaleY(0);
}

.terminal-slide-leave-to {
  height: 0px !important;
  opacity: 0;
  transform: scaleY(0);
}

/* Mermaid 侧边栏展开动画 */
.mermaid-slide-enter-active,
.mermaid-slide-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: left;
}

.mermaid-slide-enter-from {
  width: 0px !important;
  opacity: 0;
  transform: scaleX(0);
}

.mermaid-slide-leave-to {
  width: 0px !important;
  opacity: 0;
  transform: scaleX(0);
}

/* 切换栏图标动画优化 */
.toggle-icon {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.toggle-icon.expanded {
  transform: rotate(180deg);
}

/* 右键菜单样式 */
.context-menu {
  position: fixed;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.15);
  z-index: 9999;
  min-width: 140px;
  padding: 6px 0;
  font-size: 14px;
}

.context-menu-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  color: #606266;
  transition: background-color 0.2s;
}

.context-menu-item:hover {
  background-color: #f5f7fa;
}

.context-menu-item .el-icon {
  margin-right: 8px;
  font-size: 16px;
}

.context-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9998;
  background: transparent;
}
</style>
