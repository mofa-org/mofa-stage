<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="page-title">{{ agentName }}</h1>
        <el-tag v-if="isAgentRunning" type="success">Running</el-tag>
      </div>
      
      <div class="header-actions">
        <el-button
          class="code-search-btn"
          size="small"
          type="primary"
          plain
          @click="openCodeSearch"
        >
          <el-icon><Search /></el-icon>
          Code Search
        </el-button>
        <el-button-group>
          <el-button 
            v-if="useNewEditor && vscodeStatus.running" 
            @click="installExtensions" 
            type="success" 
            size="small">
            <el-icon><Download /></el-icon>
            Extensions
          </el-button>
          <el-button 
            v-if="useNewEditor && vscodeStatus.running" 
            @click="updateVSCodeConfig" 
            type="info" 
            size="small">
            <el-icon><Setting /></el-icon>
            Config
          </el-button>
          <el-button 
            @click="toggleVariableMonitor" 
            :style="{ backgroundColor: showVariableMonitor ? '#ffc53d' : '', color: showVariableMonitor ? '#fff' : '', borderColor: showVariableMonitor ? '#ffc53d' : '' }">
            <el-icon><View /></el-icon>
            Variables
          </el-button>
          <el-button 
            v-if="nodeMonitorWindows.size > 0" 
            @click="closeAllNodeMonitors"
            type="warning"
            size="small">
            <el-icon><Close /></el-icon>
            Close Node Monitors ({{ nodeMonitorWindows.size }})
          </el-button>
          <el-button class="custom-save-btn" @click="saveCurrentFile" :disabled="!hasChanges" :loading="isSaving">
            <el-icon><Document /></el-icon>
            Save
          </el-button>
          <el-button 
            v-if="!isAgentRunning" 
            class="custom-run-btn" 
            @click="runAgent"
            :disabled="isNodeAgent"
          >
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
          <div v-loading="true" element-loading-text="Starting VS Code Web..." class="loading-container">
          </div>
        </div>
        <div v-else-if="vscodeStatus.error" class="vscode-error">
          <el-alert
            title="VS Code Web Failed to Start"
            type="error"
            :description="vscodeStatus.error"
            show-icon
          />
          <el-button @click="startVSCodeServer" type="primary" style="margin-top: 10px;">
            Retry Launch
          </el-button>
        </div>
        <VSCodeEmbed 
          v-else-if="vscodeStatus.running"
          :folder-path="agentFolderPath" 
          :vscode-base-url="vscodeBaseUrl" 
        />
        <div v-else class="vscode-starting">
          <el-empty description="Preparing VS Code Web...">
            <el-button @click="startVSCodeServer" type="primary">
              Launch VS Code
            </el-button>
            <el-button @click="installExtensions" type="success" style="margin-left: 10px;">
              Install Recommended Extensions
            </el-button>
            <el-button @click="updateVSCodeConfig" type="info" style="margin-left: 10px;">
              Update Config
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
            <h3>File List</h3>
            <el-input
              placeholder="Search files"
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
              <el-button size="small" @click="addNewFile" :icon="Document">New File</el-button>
              <el-button size="small" @click="addNewFolder" :icon="FolderAdd">New Folder</el-button>
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
                    v-if="isMarkdownFile || isMermaidHtml || isImageFile || isVideoFile || isDuckDBFile || isDuckDBWALFile"
                    size="small"
                    @click="togglePreviewMode"
                    :type="previewMode ? 'primary' : 'default'">
                    {{ previewMode ? 'Edit' : 'Preview' }}
                  </el-button>
                  <!-- 保存按钮已移至顶部工具栏，此处注释掉
                  <el-button 
                    size="small" 
                    @click="saveCurrentFile" 
                    :disabled="!hasChanges"
                    :loading="isSaving">
                    保存
                  </el-button>
                  -->
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
                        <el-empty description="Select a file or switch to the new editor" />
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
                            {{ imageInfo.width }} × {{ imageInfo.height }} pixels
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
                            Duration: {{ formatDuration(videoInfo.duration) }}
                          </div>
                          <div v-if="videoInfo.width && videoInfo.height" class="video-dimensions">
                            {{ videoInfo.width }} × {{ videoInfo.height }} pixels
                          </div>
                          <div v-if="videoInfo.size" class="video-size">
                            {{ formatFileSize(videoInfo.size) }}
                          </div>
                        </div>
                      </div>
                    </div>
                    <!-- DuckDB数据库预览 -->
                    <div v-else-if="isDuckDBFile || isDuckDBWALFile" class="duckdb-preview">
                      <div class="duckdb-container">
                        <!-- DuckDB 头部信息 -->
                        <div class="duckdb-header">
                          <h3>
                            <el-icon class="duckdb-icon"><DataAnalysis /></el-icon>
                            {{ isDuckDBWALFile ? 'DuckDB Write-Ahead Log' : 'DuckDB Database' }}
                          </h3>
                          <div class="duckdb-path">{{ currentFile.path }}</div>
                        </div>

                        <!-- DuckDB WAL 文件说明 -->
                        <div v-if="isDuckDBWALFile" class="wal-info">
                          <el-alert type="info" :closable="false" show-icon>
                            <template #title>
                              DuckDB Write-Ahead Log (WAL) File
                            </template>
                            <p>This DuckDB transaction log file preserves durability and consistency.</p>
                            <ul>
                              <li>Contains uncommitted transaction records</li>
                              <li>Used automatically during database recovery</li>
                              <li>Do not modify this file manually</li>
                              <li>Managed automatically by DuckDB</li>
                            </ul>
                          </el-alert>
                        </div>

                        <!-- DuckDB 数据库内容 -->
                        <div v-else class="duckdb-content">
                          <!-- 加载状态 -->
                          <div v-if="duckdbData.loading" class="loading-state">
                            <el-loading-spinner />
                            <p>Loading database contents...</p>
                          </div>

                          <!-- 错误状态 -->
                          <div v-else-if="duckdbData.error" class="error-state">
                            <el-alert type="error" :closable="false">
                              <template #title>Load Failed</template>
                              {{ duckdbData.error }}
                            </el-alert>
                          </div>

                          <!-- 数据库统计信息 -->
                          <div v-else-if="duckdbData.stats" class="db-stats">
                            <el-card class="stats-card">
                              <template #header>
                                <div class="card-header">
                                  <el-icon><DataBoard /></el-icon>
                                  <span>Database Stats</span>
                                </div>
                              </template>
                              <el-row :gutter="20">
                                <el-col :span="8">
                                  <div class="stat-item">
                                    <div class="stat-value">{{ duckdbData.stats.total_records || 0 }}</div>
                                    <div class="stat-label">Total Records</div>
                                  </div>
                                </el-col>
                                <el-col :span="8">
                                  <div class="stat-item">
                                    <div class="stat-value">{{ duckdbData.stats.total_nodes || 0 }}</div>
                                    <div class="stat-label">Node Count</div>
                                  </div>
                                </el-col>
                                <el-col :span="8">
                                  <div class="stat-item">
                                    <div class="stat-value">{{ duckdbData.tables.length }}</div>
                                    <div class="stat-label">Tables</div>
                                  </div>
                                </el-col>
                              </el-row>
                            </el-card>

                            <!-- 数据表列表 -->
                            <el-card v-if="duckdbData.tables.length > 0" class="tables-card">
                              <template #header>
                                <div class="card-header">
                                  <el-icon><Grid /></el-icon>
                                  <span>Data Nodes</span>
                                </div>
                              </template>
                              <div class="tables-list">
                                <el-collapse v-model="activeTablePanels" accordion>
                                  <el-collapse-item 
                                    v-for="table in duckdbData.tables" 
                                    :key="table.node_name"
                                    :name="table.node_name"
                                  >
                                    <template #title>
                                      <div class="table-title">
                                        <el-icon><Box /></el-icon>
                                        <span class="table-name">{{ table.node_name }}</span>
                                        <el-tag size="small" type="info">{{ table.record_count }} records</el-tag>
                                      </div>
                                    </template>
                                    
                                    <!-- 表数据预览 -->
                                    <div v-if="duckdbData.previewData[table.node_name]" class="table-preview">
                                      <div class="preview-variables">
                                        <div 
                                          v-for="(variable, varName) in duckdbData.previewData[table.node_name]"
                                          :key="varName"
                                          class="variable-item"
                                        >
                                          <div class="variable-header">
                                            <span class="variable-name">{{ varName }}</span>
                                            <el-tag :type="variable.type === 'input' ? 'success' : 'warning'" size="small">
                                              {{ variable.type }}
                                            </el-tag>
                                          </div>
                                          <div class="variable-value">
                                            <pre>{{ variable.display_value || JSON.stringify(variable.value, null, 2) }}</pre>
                                          </div>
                                          <div class="variable-meta">
                                            <span class="variable-time">{{ new Date(variable.time).toLocaleString() }}</span>
                                          </div>
                                        </div>
                                      </div>

                                      <!-- 历史记录 -->
                                      <div v-if="duckdbData.historyData[table.node_name]" class="history-section">
                                        <h4 class="history-title">📋 History</h4>
                                        <div class="history-table">
                                          <el-table 
                                            :data="duckdbData.historyData[table.node_name]" 
                                            size="small" 
                                            stripe
                                            :max-height="300"
                                          >
                                            <el-table-column prop="time" label="Time" width="160" show-overflow-tooltip />
                                            <el-table-column label="Input Variable" width="120">
                                              <template #default="scope">
                                                {{ scope.row.input_name || '-' }}
                                              </template>
                                            </el-table-column>
                                            <el-table-column label="Input Value" min-width="150">
                                              <template #default="scope">
                                                <div v-if="scope.row.input_value !== null && scope.row.input_value !== undefined" class="table-value">
                                                  <pre>{{ JSON.stringify(scope.row.input_value, null, 2) }}</pre>
                                                </div>
                                                <span v-else class="null-value">-</span>
                                              </template>
                                            </el-table-column>
                                            <el-table-column label="Output Variable" width="120">
                                              <template #default="scope">
                                                {{ scope.row.output_name || '-' }}
                                              </template>
                                            </el-table-column>
                                            <el-table-column label="Output Value" min-width="150">
                                              <template #default="scope">
                                                <div v-if="scope.row.output_value !== null && scope.row.output_value !== undefined" class="table-value">
                                                  <pre>{{ JSON.stringify(scope.row.output_value, null, 2) }}</pre>
                                                </div>
                                                <span v-else class="null-value">-</span>
                                              </template>
                                            </el-table-column>
                                          </el-table>
                                        </div>
                                      </div>
                                    </div>
                                  </el-collapse-item>
                                </el-collapse>
                              </div>
                            </el-card>
                          </div>

                          <!-- 空状态 -->
                          <div v-else class="empty-database">
                            <el-empty description="Database is empty or unreachable">
                              <el-button type="primary" @click="loadDuckDBData">Reload</el-button>
                            </el-empty>
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
                      <el-empty description="Select a file or switch to the new editor" />
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
                <span class="toggle-label-expanded">Close</span>
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
             <h4>Dataflow Diagram</h4>
             <div class="mermaid-toolbar">
               <el-tooltip content="Zoom In" placement="top">
                 <el-button size="small" text @click="zoomIn"><el-icon><Plus /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="Zoom Out" placement="top">
                 <el-button size="small" text @click="zoomOut"><el-icon><Minus /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="Reset" placement="top">
                 <el-button size="small" text @click="resetZoom"><el-icon><Refresh /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="Open in New Tab" placement="top">
                 <el-button size="small" text @click="openMermaidInNewTab"><el-icon><Document /></el-icon></el-button>
               </el-tooltip>
               <el-tooltip content="Close" placement="top">
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
              Loading...
            </div>
            <div v-else-if="mermaidHtmlContent"
                 class="mermaid-zoom-wrapper"
                 :style="{ transform: `scale(${zoomLevel})`, transformOrigin: 'top left' }">
              <iframe class="mermaid-content-iframe" :srcdoc="mermaidHtmlContent" />
            </div>
                         <div v-else class="mermaid-empty">
               <el-empty description="No HTML file found" size="small" />
             </div>
          </div>
        </div>
        </transition>
        
        <!-- 变量监控悬浮窗口 -->
        <VariableMonitor 
          ref="variableMonitorRef"
          :visible="showVariableMonitor"
          :default-width="variableMonitorWidth"
          :default-height="variableMonitorHeight"
          :default-x="variableMonitorX"
          :default-y="variableMonitorY"
          :agent-name="agentName"
          :agent-type="agentType"
          @close="handleVariableMonitorClose"
          @minimize="handleVariableMonitorMinimize"
          @position-change="handleVariableMonitorPositionChange"
          @size-change="handleVariableMonitorSizeChange"
        />

        <!-- 节点变量监控窗口群 -->
        <NodeVariableMonitor
          v-for="[nodeId, windowConfig] in nodeMonitorWindows"
          :key="nodeId"
          v-if="windowConfig && windowConfig.visible"
          :node-info="windowConfig.nodeInfo"
          :window-config="windowConfig"
          :visible="windowConfig.visible"
          @close="handleNodeMonitorClose"
          @minimize="handleNodeMonitorMinimize"
          @position-change="handleNodeMonitorPositionChange"
          @size-change="handleNodeMonitorSizeChange"
        />

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

    <el-drawer
      v-model="codeSearchDrawer"
      direction="rtl"
      size="380px"
      :with-header="false"
      class="code-search-drawer"
    >
      <div class="code-search-header">
        <h3>Repository Code Search</h3>
        <p class="code-search-subtitle">Glide through MoFA & Dora code with pastel-powered focus.</p>
      </div>
      <div class="code-search-controls">
        <el-input
          v-model="codeSearchQuery"
          placeholder="Keyword (e.g. run_agent)"
          clearable
          @keyup.enter="performCodeSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-input
          v-model="codeSearchGlob"
          placeholder="Optional glob (e.g. *.py,*.yml)"
          clearable
        />
        <div class="code-search-actions">
          <el-button type="primary" plain @click="performCodeSearch" :loading="searchLoading">Search</el-button>
          <el-button plain @click="clearCodeSearch">Clear</el-button>
        </div>
      </div>
      <el-divider content-position="left">Matches</el-divider>
      <el-scrollbar class="code-search-results" v-loading="searchLoading">
        <template v-if="!searchLoading && searchResults.length">
          <div
            v-for="item in searchResults"
            :key="item.file + ':' + item.line"
            class="code-search-item"
            @click="openSearchResult(item)"
          >
            <div class="result-path">{{ deriveAgentRelativePath(item) || item.relative_file }}</div>
            <div class="result-line">Line {{ item.line }}</div>
            <pre class="result-snippet">{{ item.preview }}</pre>
            <el-tag
              v-if="!deriveAgentRelativePath(item)"
              size="small"
              type="warning"
              effect="light"
            >Outside current agent</el-tag>
          </div>
        </template>
        <el-empty
          v-else-if="!searchLoading"
          description="No results yet. Try another query."
        />
      </el-scrollbar>
    </el-drawer>

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
        <span>Rename</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && contextMenuData.isDirectory" @click="handleDeleteItem">
        <el-icon><Delete /></el-icon>
        <span>Delete Folder</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleRenameItem">
        <el-icon><Edit /></el-icon>
        <span>Rename</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleCopyItem">
        <el-icon><CopyDocument /></el-icon>
        <span>Copy File</span>
      </div>
      <div class="context-menu-item" v-if="contextMenuData && !contextMenuData.isDirectory" @click="handleDeleteItem">
        <el-icon><Delete /></el-icon>
        <span>Delete File</span>
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

    <!-- Dataflow运行输出弹窗 -->
    <el-dialog 
      v-model="dataflowOutputDialogVisible" 
      :title="`Dataflow Output - ${agentName}`"
      width="80%"
      top="5vh"
      @close="closeDataflowOutputDialog"
    >
      <div class="dataflow-output-content">
        <!-- 控制按钮 -->
        <div class="dataflow-controls">
          <el-button-group>
            <el-button 
              type="primary" 
              size="small" 
              @click="fetchDataflowOutput" 
              :loading="dataflowOutputLoading"
            >
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
            <el-button 
              size="small" 
              @click="toggleDataflowAutoRefresh"
              :type="autoRefreshDataflowOutput ? 'success' : 'info'"
            >
              <el-icon><VideoPlay v-if="!autoRefreshDataflowOutput" /><VideoPause v-else /></el-icon>
              {{ autoRefreshDataflowOutput ? 'Stop Auto Refresh' : 'Auto Refresh' }}
            </el-button>
            <el-button 
              size="small" 
              @click="clearDataflowOutput"
            >
              <el-icon><Delete /></el-icon>
              Clear
            </el-button>
            <el-button 
              type="danger" 
              size="small" 
              @click="stopAgent"
              v-if="isAgentRunning"
            >
              <el-icon><VideoPause /></el-icon>
              Stop Run
            </el-button>
          </el-button-group>
        </div>
        
        <!-- 输出内容 -->
        <div class="dataflow-output-container">
          <el-card class="output-card" body-style="padding: 0;">
            <div class="output-header">
              <span class="output-title">Live Output</span>
              <el-tag 
                :type="isAgentRunning ? 'success' : 'info'" 
                size="small"
              >
                {{ isAgentRunning ? 'Running' : 'Stopped' }}
              </el-tag>
            </div>
            <div class="output-body">
              <pre class="output-content" v-loading="dataflowOutputLoading">{{ dataflowOutput || 'No output yet...' }}</pre>
            </div>
          </el-card>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="closeDataflowOutputDialog">Close</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '../store/agent'
import { useSettingsStore } from '../store/settings'
import CodeEditor from '../components/editor/CodeEditor.vue'
import { Document, ArrowLeft, VideoPlay, VideoPause, Search, Plus, Minus, Refresh, Download, Setting, ArrowUp, ArrowRight, Close, View, Hide, Delete, CopyDocument, Edit, Folder, FolderAdd, DataAnalysis, DataBoard, Grid, Box } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MarkdownIt from 'markdown-it'
import MermaidViewer from '../components/MermaidViewer.vue'
import VSCodeEmbed from '../components/editor/VSCodeEmbed.vue'
import VariableMonitor from '../components/editor/VariableMonitor.vue'
import NodeVariableMonitor from '../components/editor/NodeVariableMonitor.vue'
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
    DataAnalysis,
    DataBoard,
    Grid,
    Box,
    MermaidViewer,
    VSCodeEmbed,
    VariableMonitor,
    NodeVariableMonitor,
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
    const agentType = computed(() => route.query.type || 'examples')
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
    
    // 判断是否为dataflow类型（examples目录下的agent）
    const isDataflowAgent = computed(() => agentStore.exampleAgents.includes(props.agentName))
    
    // 判断是否在编辑node（agent-hub中的原子agent）
    const isNodeAgent = computed(() => agentStore.hubAgents.includes(props.agentName))
    
    // dataflow运行结果弹窗相关
    const dataflowOutputDialogVisible = ref(false)
    const dataflowOutput = ref('')
    const dataflowOutputLoading = ref(false)
    const autoRefreshDataflowOutput = ref(false)
    const dataflowAutoRefreshInterval = ref(null)
    
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

    // 变量监控窗口相关状态
    const showVariableMonitor = ref(false)
    const variableMonitorWidth = ref(320)
    const variableMonitorHeight = ref(400)
    const variableMonitorX = ref(100)
    const variableMonitorY = ref(100)

    // 节点变量监控窗口管理
    const nodeMonitorWindows = reactive(new Map()) // 存储每个节点的监控窗口状态
    const nextZIndex = ref(1001) // 管理窗口层级

    // 仓库代码搜索
    const codeSearchDrawer = ref(false)
    const codeSearchQuery = ref('')
    const codeSearchGlob = ref('')
    const searchResults = computed(() => agentStore.searchResults)
    const searchLoading = computed(() => agentStore.searchLoading)

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

    // 新增：检测DuckDB文件
    const isDuckDBFile = computed(() => {
      if (!currentFile.value) return false
      const lowerPath = currentFile.value.path.toLowerCase()
      return lowerPath.endsWith('.duckdb') || lowerPath.endsWith('.db')
    })

    // 新增：检测DuckDB WAL文件
    const isDuckDBWALFile = computed(() => {
      if (!currentFile.value) return false
      const lowerPath = currentFile.value.path.toLowerCase()
      return lowerPath.endsWith('.duckdb.wal') || lowerPath.endsWith('.db.wal')
    })

    // 获取图片文件的数据 URL
    const imageDataUrl = ref('')
    
    // 图片信息
    const imageInfo = ref({
      width: null,
      height: null,
      size: null
    })

    // DuckDB数据相关
    const duckdbData = ref({
      loading: false,
      error: null,
      tables: [],
      stats: null,
      previewData: {},
      historyData: {}
    })

    // DuckDB表格展开面板
    const activeTablePanels = ref([])

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
          ElMessage.success('VS Code Web started successfully')
        } else {
          vscodeStatus.value.error = result.error
          ElMessage.error(`Failed to launch: ${result.error}`)
        }
      } catch (error) {
        vscodeStatus.value.error = error.message
        ElMessage.error(`Failed to launch: ${error.message}`)
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
      ElMessage.info('Installing VS Code extensions...')
      try {
        const result = await vscodeApi.installExtensions(props.agentName)
        if (result.success) {
          ElMessage.success(`Extension install finished: ${result.installed.length} succeeded, ${result.failed.length} failed`)
        } else {
          ElMessage.error(`Extension install failed: ${result.error}`)
        }
      } catch (error) {
        ElMessage.error(`Extension install failed: ${error.message}`)
      }
    }

    // 更新 VS Code 配置
    const updateVSCodeConfig = async () => {
      try {
        const result = await vscodeApi.updateConfig(props.agentName)
        if (result.success) {
          ElMessage.success('VS Code configuration updated')
        } else {
          ElMessage.error(`Configuration update failed: ${result.error}`)
        }
      } catch (error) {
        ElMessage.error(`Configuration update failed: ${error.message}`)
      }
    }

    watch(editorContent, async (newVal) => {
      if (isDataflowYaml.value) {
        // call backend to generate mermaid
        try {
          const resp = await fetch('http://localhost:5002/api/mermaid/preview', {
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
          'Unsaved changes detected. Save before leaving?',
          'Unsaved Changes',
          {
            confirmButtonText: 'Save and Leave',
            cancelButtonText: 'Discard Changes',
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

    const openCodeSearch = () => {
      codeSearchDrawer.value = true
      nextTick(() => {
        if (!codeSearchQuery.value) {
          codeSearchQuery.value = currentFile.value ? currentFile.value.path.split('/').pop()?.split('.')[0] || '' : ''
        }
      })
    }

    const performCodeSearch = async () => {
      if (!codeSearchQuery.value.trim()) {
        ElMessage.warning('Enter a keyword to search')
        return
      }
      await agentStore.searchRepository(codeSearchQuery.value.trim(), codeSearchGlob.value.trim())
    }

    const clearCodeSearch = () => {
      codeSearchQuery.value = ''
      codeSearchGlob.value = ''
      agentStore.searchResults = []
    }

    const deriveAgentRelativePath = (result) => {
      if (!result || !result.file) {
        return null
      }
      const marker = `/${props.agentName}/`
      const idx = result.file.lastIndexOf(marker)
      if (idx === -1) {
        return null
      }
      return result.file.substring(idx + marker.length)
    }

    const openSearchResult = async (result) => {
      const relativePath = deriveAgentRelativePath(result)
      if (!relativePath) {
        ElMessage.info('Result belongs to another workspace. Open it from the repository directly.')
        return
      }
      fileTreeCollapsed.value = false
      await loadFileContent(relativePath)
      codeSearchDrawer.value = false
    }

    const handleFileClick = async (data) => {
      console.log('handleFileClick called with:', data)
      if (data.isDirectory) return
      
      // 如果当前有未保存的更改，提示保存
      if (currentFile.value && hasChanges.value) {
        try {
          await ElMessageBox.confirm(
            'Unsaved changes detected. Save now?',
            'Unsaved Changes',
            {
              confirmButtonText: 'Save',
              cancelButtonText: 'Discard Changes',
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
              console.log('Image loaded successfully:', filePath, 'size:', blob.size)
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
              console.log('Video loaded successfully:', filePath, 'size:', blob.size)
            } else {
              console.error('Failed to load video:', response.status, response.statusText)
              ElMessage.error('Failed to load video file')
            }
          } catch (e) {
            console.error('Failed to load video:', e)
            ElMessage.error('Failed to load video file')
          }
        } else if (lowerPath.endsWith('.duckdb') || lowerPath.endsWith('.db')) {
          // 对于DuckDB文件，显示数据库内容而不是二进制文件内容
          currentFile.value = {
            path: filePath,
            type: 'database'
          }
          originalContent.value = '# DuckDB Database File\n# Use the preview mode to explore the database content.'
          editorContent.value = '# DuckDB Database File\n# Use the preview mode to explore the database content.'
          
          // 加载DuckDB数据
          await loadDuckDBData()
          
          // 自动进入预览模式
          previewMode.value = true
        } else if (lowerPath.endsWith('.duckdb.wal') || lowerPath.endsWith('.db.wal')) {
          // 对于WAL文件，显示说明信息
          currentFile.value = {
            path: filePath,
            type: 'wal'
          }
          originalContent.value = '# DuckDB Write-Ahead Log (WAL) File\n# This is a transaction log file used by DuckDB for durability.\n# It contains uncommitted transactions and should not be modified manually.\n# WAL files are automatically managed by DuckDB.'
          editorContent.value = '# DuckDB Write-Ahead Log (WAL) File\n# This is a transaction log file used by DuckDB for durability.\n# It contains uncommitted transactions and should not be modified manually.\n# WAL files are automatically managed by DuckDB.'
        } else {
          // 对于非图片/视频/数据库文件，使用原有逻辑获取文本内容
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
              const resp = await fetch('http://localhost:5002/api/mermaid/export', {
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
          ElMessage.info('Image file created. Please edit with an external tool before uploading')
          const result = await agentStore.saveFileContent(props.agentName, filePath, '')
          if (result) {
            ElMessage.success('Image file placeholder created')
            newFileDialogVisible.value = false
            await loadAgentFiles()
          } else {
            ElMessage.error(`Failed to create file: ${error.value}`)
          }
          isCreatingFile.value = false
          return
        } else if (videoExtensions.includes(ext)) {
          ElMessage.info('Video file created. Please edit with an external tool before uploading')
          const result = await agentStore.saveFileContent(props.agentName, filePath, '')
          if (result) {
            ElMessage.success('Video file placeholder created')
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
      
      const itemType = contextMenuData.value.isDirectory ? 'Folder' : 'File'
      const itemName = contextMenuData.value.label
      
      try {
        await ElMessageBox.confirm(
          `Delete this ${itemType.toLowerCase()}? ${itemName}`,
          `Delete ${itemType}`,
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        // 调用后端删除接口
        const success = await agentStore.deleteFileOrFolder(props.agentName, contextMenuData.value.path)
        if (success) {
          ElMessage.success(`${itemType} deleted`)
          await loadAgentFiles()
          // 如果删除的是当前打开文件，清空编辑器
          if (currentFile.value && currentFile.value.path === contextMenuData.value.path) {
            currentFile.value = null
            editorContent.value = ''
          }
        } else {
          ElMessage.error(`Failed to delete the ${itemType.toLowerCase()}`)
        }
        
      } catch (e) {
        // 用户取消删除
      }
    }

    const confirmRename = async () => {
      if (!contextMenuData.value || !renameForm.value.newName.trim()) {
        ElMessage.warning('Please enter a new name')
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
      // 如果是dataflow类型，生成dora命令并复制到剪贴板
      if (isDataflowAgent.value) {
        try {
          // 获取dataflow文件信息
          const response = await fetch(`/api/agents/${props.agentName}/dataflow-file`)
          
          if (response.ok) {
            const data = await response.json()
            if (data.success) {
              const dataflowFile = data.dataflow_file
              const agentPath = data.agent_path
              
              // 构建完整的dora 4步命令
              const doraCommand = `cd ${agentPath} && dora up && dora build ${dataflowFile} && dora start ${dataflowFile}`
              
              // 复制到剪贴板
              try {
                await navigator.clipboard.writeText(doraCommand)
                
                // 自动展开终端
                showTerminal.value = true
                
                ElMessage.success({
                  message: `Dora command copied to clipboard! Paste it in the terminal below.`,
                  duration: 5000,
                  showClose: true
                })
              } catch (err) {
                // 如果剪贴板API失败，显示命令让用户手动复制
                ElMessage({
                  message: `Please copy this command to terminal: ${doraCommand}`,
                  type: 'info',
                  duration: 10000,
                  showClose: true
                })
                
                // 还是展开终端
                showTerminal.value = true
              }
              
              return
            }
          }
          
          // 如果获取dataflow文件失败，显示错误
          ElMessage.error('Failed to get dataflow file information')
          return
          
        } catch (error) {
          ElMessage.error(`Failed to prepare dataflow execution: ${error.message}`)
          return
        }
      }
      
      // 原有的agent运行逻辑（非dataflow类型）
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
        
        // 如果是dataflow类型，停止自动刷新并关闭弹窗
        if (isDataflowAgent.value) {
          stopDataflowOutputRefresh()
        }
      } else {
        ElMessage.error(`Failed to stop Agent: ${result.error}`)
      }
    }

    // dataflow输出相关方法
    const fetchDataflowOutput = async () => {
      if (!isDataflowAgent.value) return
      
      dataflowOutputLoading.value = true
      try {
        const response = await fetch(`/api/agents/${props.agentName}/process-output`)
        const data = await response.json()
        
        if (data.success && data.output) {
          dataflowOutput.value = data.output
        } else if (data.error) {
          dataflowOutput.value = `Error: ${data.error}`
        }
      } catch (error) {
        dataflowOutput.value = `Network Error: ${error.message}`
      } finally {
        dataflowOutputLoading.value = false
      }
    }

    const startDataflowOutputRefresh = () => {
      if (dataflowAutoRefreshInterval.value) return
      
      // 立即获取一次输出
      fetchDataflowOutput()
      
      // 启动自动刷新
      autoRefreshDataflowOutput.value = true
      dataflowAutoRefreshInterval.value = setInterval(() => {
        fetchDataflowOutput()
      }, 2000) // 每2秒刷新一次
    }

    const stopDataflowOutputRefresh = () => {
      autoRefreshDataflowOutput.value = false
      if (dataflowAutoRefreshInterval.value) {
        clearInterval(dataflowAutoRefreshInterval.value)
        dataflowAutoRefreshInterval.value = null
      }
    }

    const toggleDataflowAutoRefresh = () => {
      if (autoRefreshDataflowOutput.value) {
        stopDataflowOutputRefresh()
      } else {
        startDataflowOutputRefresh()
      }
    }

    const clearDataflowOutput = () => {
      dataflowOutput.value = ''
    }

    const closeDataflowOutputDialog = () => {
      dataflowOutputDialogVisible.value = false
      stopDataflowOutputRefresh()
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
          // 注入节点点击处理脚本到HTML内容中
          const scriptStart = '<script>';
          const scriptEnd = '</' + 'script>';
          
          const scriptContent = `
              // 等待DOM加载完成后添加节点点击监听
              document.addEventListener('DOMContentLoaded', function() {
                console.log('MermaidViewer iframe script loaded');
                // 查找所有mermaid节点 - 使用更广泛的选择器
                // 尝试更广泛的选择器来找到Mermaid节点
                const nodes = document.querySelectorAll('g, rect, [class*="node"], .node, .flowchart-node, [id*="flowchart"], [data-id]');
                console.log('Found mermaid nodes:', nodes.length);
                console.log('All elements in page:', document.querySelectorAll('*').length);
                console.log('All g elements:', document.querySelectorAll('g').length);
                console.log('All rect elements:', document.querySelectorAll('rect').length);
                nodes.forEach(nodeEl => {
                  nodeEl.style.cursor = 'pointer';
                  nodeEl.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const textEl = nodeEl.querySelector('text, span, .nodeLabel');
                    let nodeId = null;
                    
                    if (textEl) {
                      nodeId = textEl.textContent.trim();
                    } else {
                      // 尝试从节点ID获取
                      const id = nodeEl.id || nodeEl.getAttribute('id');
                      if (id) {
                        nodeId = id.replace(/^flowchart-/, '').replace(/-\\\\d+$/, '');
                      }
                    }
                    
                    if (nodeId) {
                      console.log('Clicking node:', nodeId);
                      // 向父窗口发送消息
                      window.parent.postMessage({
                        type: 'mermaid-node-click',
                        nodeId: nodeId
                      }, '*');
                    } else {
                      console.log('No nodeId found for clicked element:', nodeEl);
                    }
                  });
                });
              });
          `;
          
          const injectedScript = scriptStart + scriptContent + scriptEnd;
          
          // 将脚本注入到HTML内容的body结束标签前
          let content = fileData.content;
          const bodyEndTag = '</' + 'body>';
          if (content.includes(bodyEndTag)) {
            content = content.replace(bodyEndTag, injectedScript + bodyEndTag);
          } else {
            // 如果没有body结束标签，直接添加到末尾
            content += injectedScript;
          }
          
          mermaidHtmlContent.value = content;
        }
             } catch (err) {
        ElMessage.error(`Failed to load HTML: ${err.message}`)
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

    // 变量监控窗口相关方法
    const toggleVariableMonitor = () => {
      showVariableMonitor.value = !showVariableMonitor.value
    }

    const handleVariableMonitorClose = () => {
      showVariableMonitor.value = false
    }

    const handleVariableMonitorMinimize = (minimized) => {
      // 可以在这里处理最小化状态，比如记录到本地存储
      console.log('Variable monitor window minimized state:', minimized)
    }

    const handleVariableMonitorPositionChange = (position) => {
      variableMonitorX.value = position.x
      variableMonitorY.value = position.y
    }

    const handleVariableMonitorSizeChange = (size) => {
      variableMonitorWidth.value = size.width
      variableMonitorHeight.value = size.height
    }

    // 解析节点信息
    const parseNodeInfo = (lines, start, end, nodeId) => {
      const nodeInfo = {
        id: nodeId,
        type: '',
        inputs: [],
        outputs: [],
        config: {}
      }

      for (let i = start; i <= end; i++) {
        const line = lines[i]
        const trimmed = line.trim()

        // 解析节点类型
        if (trimmed.startsWith('type:')) {
          nodeInfo.type = trimmed.substring(5).trim()
        }
        // 解析输入变量
        else if (trimmed.startsWith('inputs:')) {
          // 查找inputs列表
          for (let j = i + 1; j <= end; j++) {
            const inputLine = lines[j]
            const inputTrimmed = inputLine.trim()
            if (inputTrimmed.startsWith('- ') && !inputTrimmed.includes(':')) {
              nodeInfo.inputs.push(inputTrimmed.substring(2).trim())
            } else if (!inputTrimmed.startsWith(' ') && inputTrimmed !== '') {
              break
            }
          }
        }
        // 解析输出变量
        else if (trimmed.startsWith('outputs:')) {
          // 查找outputs列表
          for (let j = i + 1; j <= end; j++) {
            const outputLine = lines[j]
            const outputTrimmed = outputLine.trim()
            if (outputTrimmed.startsWith('- ') && !outputTrimmed.includes(':')) {
              nodeInfo.outputs.push(outputTrimmed.substring(2).trim())
            } else if (!outputTrimmed.startsWith(' ') && outputTrimmed !== '') {
              break
            }
          }
        }
      }

      return nodeInfo
    }

    // 显示节点变量监控窗口
    const showNodeVariableMonitor = (nodeId, nodeInfo) => {
      console.log('showNodeVariableMonitor called with:', nodeId, nodeInfo)
      console.log('Current nodeMonitorWindows size:', nodeMonitorWindows.size)
      
      // 检查是否已经存在该节点的监控窗口
      if (nodeMonitorWindows.has(nodeId)) {
        // 如果存在，提升其层级并显示
        const existing = nodeMonitorWindows.get(nodeId)
        existing.zIndex = nextZIndex.value++
        existing.visible = true
        console.log('Updated existing window for node:', nodeId)
        return
      }

      // 创建新的监控窗口配置
      const windowConfig = {
        id: nodeId,
        nodeInfo: nodeInfo,
        visible: true,
        minimized: false,
        x: 150 + (nodeMonitorWindows.size * 30), // 错开位置
        y: 150 + (nodeMonitorWindows.size * 30),
        width: 350,
        height: 450,
        zIndex: nextZIndex.value++
      }

      // 添加到窗口管理器
      nodeMonitorWindows.set(nodeId, windowConfig)
      console.log('Created new window for node:', nodeId, 'Total windows:', nodeMonitorWindows.size)
      console.log('Window config:', windowConfig)
    }

    // 处理节点监控窗口关闭
    const handleNodeMonitorClose = (nodeId) => {
      if (nodeMonitorWindows.has(nodeId)) {
        const window = nodeMonitorWindows.get(nodeId)
        window.visible = false
      }
    }

    // 处理节点监控窗口最小化
    const handleNodeMonitorMinimize = (nodeId, minimized) => {
      if (nodeMonitorWindows.has(nodeId)) {
        const window = nodeMonitorWindows.get(nodeId)
        window.minimized = minimized
      }
    }

    // 处理节点监控窗口位置变化
    const handleNodeMonitorPositionChange = (nodeId, position) => {
      if (nodeMonitorWindows.has(nodeId)) {
        const window = nodeMonitorWindows.get(nodeId)
        window.x = position.x
        window.y = position.y
      }
    }

    // 处理节点监控窗口大小变化
    const handleNodeMonitorSizeChange = (nodeId, size) => {
      if (nodeMonitorWindows.has(nodeId)) {
        const window = nodeMonitorWindows.get(nodeId)
        window.width = size.width
        window.height = size.height
      }
    }

    // 关闭所有节点监控窗口
    const closeAllNodeMonitors = () => {
      nodeMonitorWindows.forEach(window => {
        window.visible = false
      })
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
    const variableMonitorRef = ref(null)

    const handleMermaidNodeClick = (nodeId) => {
      if (!codeEditorRef.value) return
      
      const lines = editorContent.value.split('\n')
      let start = -1
      let nodeInfo = null
      
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
      
      // 解析节点信息
      nodeInfo = parseNodeInfo(lines, start, end, nodeId)
      nodeInfo.agentName = props.agentName // 添加agent名称
      
      // monaco uses 1-based line numbers
      codeEditorRef.value.selectLines(start + 1, end + 2)
      
      // Switch to YAML tab if graph tab is active
      if (showYamlTabs.value) activeYamlTab.value = 'yaml'
      
      // 直接弹出变量监控窗口并自动发现变量
      showVariableMonitor.value = true
      
      // 延迟一下让窗口打开，然后自动发现变量
      setTimeout(() => {
        // 触发自动发现变量（需要在VariableMonitor组件中添加方法引用）
        if (variableMonitorRef.value && variableMonitorRef.value.autoDiscoverVariables) {
          variableMonitorRef.value.autoDiscoverVariables()
        }
      }, 300)
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

    // 加载DuckDB数据
    const loadDuckDBData = async () => {
      if (!isDuckDBFile.value || !currentFile.value) return
      
      duckdbData.value.loading = true
      duckdbData.value.error = null
      
      try {
        // 获取当前文件的完整路径
        const agentType = route.query.type || null
        let fullFilePath = currentFile.value.path
        
        // 如果是相对路径，需要构建完整路径
        // 对于hello_world agent，路径可能是相对的
        if (!fullFilePath.startsWith('/')) {
          // 构建基于agent的完整路径
          if (agentType === 'examples') {
            fullFilePath = `/Users/liyao/Code/mofa/mofa_old/mofa/python/examples/${props.agentName}/${fullFilePath}`
          } else {
            // 其他类型的agent，可能需要不同的路径构建逻辑
            fullFilePath = `/path/to/agents/${props.agentName}/${fullFilePath}`
          }
        }
        
        console.log('Loading DuckDB data for file:', fullFilePath)
        
        // 使用新的API接口，传递文件路径参数
        const queryParam = encodeURIComponent(fullFilePath)
        
        // 获取数据库统计信息
        const statsResponse = await fetch(`/api/agents/duckdb/file/stats?path=${queryParam}`)
        const statsData = await statsResponse.json()
        
        if (statsData.success) {
          duckdbData.value.stats = statsData.stats
        }

        // 获取所有表和节点
        const tablesResponse = await fetch(`/api/agents/duckdb/file/nodes?path=${queryParam}`)
        const tablesData = await tablesResponse.json()
        
        if (tablesData.success) {
          duckdbData.value.tables = tablesData.nodes || []
          
          // 为每个表获取预览数据和历史记录
          for (const table of duckdbData.value.tables) {
            try {
              // 获取变量数据
              const previewResponse = await fetch(`/api/agents/duckdb/file/node/${table.node_name}/variables?path=${queryParam}`)
              const previewData = await previewResponse.json()
              
              if (previewData.success) {
                duckdbData.value.previewData[table.node_name] = previewData.variables
              }

              // 获取历史记录
              const historyResponse = await fetch(`/api/agents/duckdb/file/node/${table.node_name}/history?path=${queryParam}&limit=20`)
              const historyData = await historyResponse.json()
              
              if (historyData.success) {
                duckdbData.value.historyData[table.node_name] = historyData.history
              }
            } catch (err) {
              console.warn(`Failed to load data for ${table.node_name}:`, err)
            }
          }
        } else {
          duckdbData.value.error = tablesData.message || 'Failed to load database nodes'
        }
      } catch (error) {
        console.error('Failed to load DuckDB data:', error)
        duckdbData.value.error = error.message || 'Failed to load database data'
      } finally {
        duckdbData.value.loading = false
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
          console.log('Editor is not initialized or unavailable')
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
      // 清理dataflow输出定时器
      stopDataflowOutputRefresh()
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
      agentType,
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
      // 代码搜索
      codeSearchDrawer,
      codeSearchQuery,
      codeSearchGlob,
      searchResults,
      searchLoading,
      openCodeSearch,
      performCodeSearch,
      clearCodeSearch,
      openSearchResult,
      fileTreeWrapper,
      deriveAgentRelativePath,
      rememberFileTreeScroll,
      restoreFileTreeScroll,
      terminalHeight,
      mermaidSidebarWidth,
      fileSidebarWidth,
      startResizeTerminal,
      startResizeMermaid,
      startResizeFileSidebar,
      codeEditorRef,
      variableMonitorRef,
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
      formatDuration,
      // DuckDB预览相关
      isDuckDBFile,
      isDuckDBWALFile,
      duckdbData,
      activeTablePanels,
      loadDuckDBData,
      // dataflow输出相关
      isDataflowAgent,
      isNodeAgent,
      dataflowOutputDialogVisible,
      dataflowOutput,
      dataflowOutputLoading,
      autoRefreshDataflowOutput,
      fetchDataflowOutput,
      startDataflowOutputRefresh,
      stopDataflowOutputRefresh,
      toggleDataflowAutoRefresh,
      clearDataflowOutput,
      closeDataflowOutputDialog,
      // 变量监控窗口相关
      showVariableMonitor,
      variableMonitorWidth,
      variableMonitorHeight,
      variableMonitorX,
      variableMonitorY,
      toggleVariableMonitor,
      handleVariableMonitorClose,
      handleVariableMonitorMinimize,
      handleVariableMonitorPositionChange,
      handleVariableMonitorSizeChange,
      // 节点变量监控窗口相关
      nodeMonitorWindows,
      handleNodeMonitorClose,
      handleNodeMonitorMinimize,
      handleNodeMonitorPositionChange,
      handleNodeMonitorSizeChange,
      closeAllNodeMonitors
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

.code-search-drawer {
  background: linear-gradient(180deg, #f8f4ff 0%, #f6fffb 100%);
}

.code-search-header {
  padding: 16px 20px 8px;
}

.code-search-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #5c2d91;
}

.code-search-subtitle {
  margin: 4px 0 0;
  color: #8a73c0;
  font-size: 13px;
}

.code-search-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 20px 12px;
}

.code-search-actions {
  display: flex;
  gap: 10px;
}

.code-search-results {
  padding: 0 16px 20px;
  max-height: calc(100vh - 220px);
}

.code-search-item {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(171, 135, 255, 0.26);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.code-search-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(149, 128, 255, 0.18);
}

.result-path {
  font-weight: 600;
  color: #5a3f8c;
  margin-bottom: 4px;
  font-size: 13px;
}

.result-line {
  font-size: 11px;
  color: #9c8fb5;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 6px;
}

.result-snippet {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  font-family: 'Fira Code', 'Monaco', 'Courier New', monospace;
  color: #40335e;
  background: rgba(244, 240, 255, 0.85);
  padding: 8px;
  border-radius: 6px;
  white-space: pre-wrap;
}

/* Dataflow输出弹窗样式 */
.dataflow-output-content {
  height: 70vh;
  display: flex;
  flex-direction: column;
}

.dataflow-controls {
  margin-bottom: 16px;
  flex-shrink: 0;
}

.dataflow-output-container {
  flex: 1;
  overflow: hidden;
}

.output-card {
  height: 100%;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.output-header {
  padding: 12px 16px;
  background: var(--fill-color-light);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.output-title {
  font-weight: 600;
  color: var(--text-color);
  font-size: 14px;
}

.output-body {
  height: calc(100% - 48px);
  overflow: hidden;
}

.output-content {
  height: 100%;
  margin: 0;
  padding: 16px;
  background: #1a1a1a;
  color: #f0f0f0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* 深色主题下的输出样式调整 */
[data-theme="dark"] .output-content {
  background: #0d1117;
  color: #c9d1d9;
}

/* 输出滚动条样式 */
.output-content::-webkit-scrollbar {
  width: 8px;
}

.output-content::-webkit-scrollbar-track {
  background: #2d2d2d;
}

.output-content::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.output-content::-webkit-scrollbar-thumb:hover {
  background: #777;
}

/* DuckDB 预览样式 */
.duckdb-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f9f9f9;
  overflow: hidden;
}

.duckdb-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: auto;
}

.duckdb-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e0e0e0;
}

.duckdb-header h3 {
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  color: #333;
}

.duckdb-icon {
  font-size: 24px;
  color: #409eff;
}

.duckdb-path {
  font-size: 12px;
  color: #999;
  font-family: monospace;
  background-color: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.wal-info {
  margin-bottom: 20px;
}

.wal-info ul {
  margin: 10px 0 0 0;
  padding-left: 20px;
}

.wal-info li {
  margin-bottom: 5px;
}

.duckdb-content {
  flex: 1;
  overflow: auto;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #666;
}

.loading-state p {
  margin-top: 15px;
  font-size: 14px;
}

.error-state {
  margin-bottom: 20px;
}

.db-stats {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-card, .tables-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.tables-list {
  margin-top: 15px;
}

.table-title {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.table-name {
  flex: 1;
  font-weight: 600;
  font-family: monospace;
}

.table-preview {
  padding: 15px;
  background: #fafafa;
  border-radius: 6px;
}

.preview-variables {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.variable-item {
  background: white;
  padding: 15px;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.variable-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.variable-name {
  font-weight: 600;
  font-family: monospace;
  font-size: 14px;
}

.variable-value {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
  font-family: monospace;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
}

.variable-value pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.variable-meta {
  font-size: 12px;
  color: #999;
  text-align: right;
}

.variable-time {
  font-family: monospace;
}

.empty-database {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #666;
}

/* 历史记录样式 */
.history-section {
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
}

.history-title {
  margin: 0 0 15px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.history-table {
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.table-value {
  max-width: 200px;
  overflow: hidden;
}

.table-value pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 100px;
  overflow-y: auto;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.null-value {
  color: #909399;
  font-style: italic;
}
</style>
