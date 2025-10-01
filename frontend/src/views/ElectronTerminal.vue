<template>
  <div class="electron-terminal-view">
    <div class="page-header">
      <h1 class="page-title">{{ t('sidebar.desktopTerminal') || 'Desktop Terminal' }}</h1>
      <div class="page-actions" v-if="isElectronAvailable">
        <el-button-group>
          <el-button type="primary" size="small" :loading="isCreatingSession" @click="spawnSession()">
            <el-icon><Plus /></el-icon>
            {{ t('electronTerminal.newTab') || 'New Tab' }}
          </el-button>
          <el-button size="small" @click="openSessionDialog">
            <el-icon><Setting /></el-icon>
          </el-button>
        </el-button-group>
        <el-divider direction="vertical" />
        <div class="toolbar-control">
          <span>{{ t('electronTerminal.fontSize') || 'Font' }}</span>
          <el-input-number
            v-model="preferences.fontSize"
            :min="10"
            :max="24"
            size="small"
            controls-position="right"
          />
        </div>
        <div class="toolbar-control">
          <span>{{ t('electronTerminal.theme') || 'Theme' }}</span>
          <el-select v-model="preferences.theme" size="small" style="width: 120px">
            <el-option :label="t('electronTerminal.themeDark') || 'Dark'" value="dark" />
            <el-option :label="t('electronTerminal.themeLight') || 'Light'" value="light" />
          </el-select>
        </div>
      </div>
    </div>

    <el-card v-if="!isElectronAvailable" class="info-card">
      <div class="info-empty">
        <el-empty :description="t('electronTerminal.unavailable') || 'Desktop terminal is only available inside the Electron app.'" />
      </div>
    </el-card>

    <div v-else class="terminal-layout">
      <aside class="quickbar" :class="{ collapsed: isQuickBarCollapsed }">
        <div class="quickbar-header" @click="toggleQuickBar">
          <span v-if="!isQuickBarCollapsed" class="quickbar-title">Quick Commands</span>
          <span v-else class="quickbar-title-collapsed">Q</span>
          <el-icon v-if="!isQuickBarCollapsed" class="collapse-icon" :class="{ rotated: isQuickBarCollapsed }"><ArrowRight /></el-icon>
        </div>
        <div v-if="!isQuickBarCollapsed" class="quickbar-content">
          <div class="quickbar-search">
            <el-input
              v-model="commandSearch"
              size="small"
              clearable
              placeholder="Search examples..."
              @input="filterQuickCommands"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <div class="quickbar-list">
            <template v-if="filteredQuickCommands.length">
              <div
                v-for="command in filteredQuickCommands"
                :key="command.name"
                class="quickbar-item"
                :class="{ active: selectedQuickCommand === command.name }"
              >
                <div class="item-main" @click="copyCommand(command)">
                  <el-icon><Document /></el-icon>
                  <span class="item-label">{{ command.name }}</span>
                </div>
                <el-tooltip content="Copy command" placement="top">
                  <el-button text size="small" @click.stop="copyCommand(command)">
                    <el-icon><DocumentCopy /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
            <el-empty
              v-else
              :image-size="60"
              :description="commandSearch ? (t('common.noResults') || 'No results') : (t('electronTerminal.noCommands') || 'No examples found')"
            />
          </div>
        </div>
      </aside>

      <el-card :class="['terminal-card', cardThemeClass]" :body-style="{ padding: '0', height: '100%' }">
        <el-tabs
          v-model="activeSessionId"
          type="card"
          editable
          @edit="handleTabEdit"
          @tab-click="handleTabClick"
          class="terminal-tabs"
        >
          <el-tab-pane
            v-for="session in sessions"
            :key="session.id"
            :label="session.title"
            :name="session.id"
          >
            <div class="terminal-meta">
              <span class="meta-item">
                <el-icon><Cpu /></el-icon>
                {{ session.shell }}
              </span>
              <span class="meta-item truncate" :title="session.cwd">
                <el-icon><FolderOpened /></el-icon>
                {{ session.cwd }}
              </span>
              <el-tag v-if="session.status === 'exited'" type="warning" size="small">
                {{ t('electronTerminal.sessionExited') || 'Exited' }}
              </el-tag>
            </div>
            <div
              class="terminal-surface"
              :class="{
                'is-active': activeSessionId === session.id,
                'is-exited': session.status === 'exited'
              }"
              :ref="el => registerContainer(session.id, el)"
            >
              <div v-if="session.status === 'starting'" class="terminal-loading">
                <el-icon class="spinner"><Loading /></el-icon>
                {{ t('electronTerminal.connecting') || 'Connecting to shell…' }}
              </div>
              <div v-else-if="session.status === 'exited'" class="terminal-overlay">
                {{ t('electronTerminal.sessionExitedHelp') || 'Session ended. Launch a new tab or restart from the menu.' }}
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <div v-if="sessions.length === 0" class="empty-placeholder">
          <el-empty :description="t('electronTerminal.noSessions') || 'Create a tab to start a local shell session.'">
            <el-button type="primary" :loading="isCreatingSession" @click="spawnSession()">
              {{ t('electronTerminal.startFirst') || 'Open Terminal' }}
            </el-button>
          </el-empty>
        </div>
      </el-card>
    </div>

    <el-dialog
      v-model="showNewSessionDialog"
      :title="t('electronTerminal.customLaunch') || 'Custom Session'"
      width="520px"
    >
      <el-form :model="sessionForm" label-width="160px">
        <el-form-item :label="t('electronTerminal.tabTitle') || 'Tab Title'">
          <el-input v-model="sessionForm.title" :placeholder="`${t('electronTerminal.tabTitlePrefix') || 'Shell'} ${sessions.length + 1}`" />
        </el-form-item>
        <el-form-item :label="t('electronTerminal.shellCommand') || 'Shell Command'">
          <el-input v-model="sessionForm.shell" :placeholder="resolvedShellPlaceholder">
            <template #append>
              <el-button size="small" @click="applyShellDefault">
                {{ t('electronTerminal.useDefault') || 'Default' }}
              </el-button>
            </template>
          </el-input>
          <div class="form-help">
            {{ t('electronTerminal.shellHelp') || 'Leave empty to use the default shell from settings or system profile.' }}
          </div>
        </el-form-item>
        <el-form-item :label="t('electronTerminal.workingDirectory') || 'Working Directory'">
          <el-input v-model="sessionForm.cwd" :placeholder="resolvedCwdPlaceholder">
            <template #append>
              <el-button size="small" @click="applyCwdDefault">
                {{ t('electronTerminal.useMofaDir') || 'Use MoFA Dir' }}
              </el-button>
            </template>
          </el-input>
          <div class="form-help">
            {{ t('electronTerminal.cwdHelp') || 'Absolute paths are recommended. ~ resolves to your home directory.' }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNewSessionDialog = false">
          {{ t('common.cancel') || 'Cancel' }}
        </el-button>
        <el-button type="primary" :loading="isCreatingSession" @click="handleCreateFromDialog">
          {{ t('electronTerminal.launch') || 'Launch' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { Plus, Setting, Loading, Cpu, FolderOpened, Search, ArrowRight, Document, DocumentCopy } from '@element-plus/icons-vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { useSettingsStore } from '../store/settings'
import { useAgentStore } from '../store/agent'

const DARK_THEME = {
  background: 'transparent',
  foreground: '#e2e8f0',
  cursor: '#7fffd4',
  selectionBackground: '#5b718d7d',
  cursorBlink: true,
  fontWeight: 'normal',
  black: '#2e3440',
  red: '#bf616a',
  green: '#a3be8c',
  yellow: '#ebcb8b',
  blue: '#81a1c1',
  magenta: '#b48ead',
  cyan: '#88c0d0',
  white: '#e5e9f0',
  brightBlack: '#4c566a',
  brightRed: '#bf616a',
  brightGreen: '#a3be8c',
  brightYellow: '#ebcb8b',
  brightBlue: '#81a1c1',
  brightMagenta: '#b48ead',
  brightCyan: '#8fbcbb',
  brightWhite: '#eceff4'
}

const LIGHT_THEME = {
  background: 'transparent',
  foreground: '#e2e8f0',
  cursor: '#7fffd4',
  selectionBackground: '#5b718d7d',
  cursorBlink: true,
  fontWeight: 'normal',
  black: '#2e3440',
  red: '#bf616a',
  green: '#a3be8c',
  yellow: '#ebcb8b',
  blue: '#81a1c1',
  magenta: '#b48ead',
  cyan: '#88c0d0',
  white: '#e5e9f0',
  brightBlack: '#4c566a',
  brightRed: '#bf616a',
  brightGreen: '#a3be8c',
  brightYellow: '#ebcb8b',
  brightBlue: '#81a1c1',
  brightMagenta: '#b48ead',
  brightCyan: '#8fbcbb',
  brightWhite: '#eceff4'
}

export default {
  name: 'ElectronTerminal',
  components: {
    Plus,
    Setting,
    Loading,
    Cpu,
    FolderOpened,
    Search,
    ArrowRight,
    Document,
    DocumentCopy
  },
  setup() {
    const settingsStore = useSettingsStore()
    const agentStore = useAgentStore()
    const { t } = useI18n()
    const route = useRoute()
    const terminalApi = computed(() => (typeof window !== 'undefined' ? window.electronAPI?.terminal : null))
    const hostPlatform = computed(() => window.electronAPI?.platform || 'linux')
    const API_BASE_URL = 'http://localhost:5002/api'

    const isElectronAvailable = ref(false)
    const defaultProfile = ref({ shell: '', cwd: '', platform: '' })
    const sessions = ref([])
    const activeSessionId = ref('')
    const containerRefs = reactive({})
    const disposers = []
    const isCreatingSession = ref(false)
    const showNewSessionDialog = ref(false)
    const sessionForm = reactive({
      title: '',
      shell: '',
      cwd: ''
    })

    const preferences = reactive({
      fontSize: Math.min(Math.max(settingsStore.settings?.editor_font_size || 14, 10), 24),
      theme: settingsStore.settings?.theme === 'dark' ? 'dark' : 'light'
    })

    const cardThemeClass = computed(() => (preferences.theme === 'dark' ? 'terminal-card-dark' : 'terminal-card-light'))

    const isQuickBarCollapsed = ref(false)
    const commandSearch = ref('')
    const quickCommands = ref([])
    const filteredQuickCommands = ref([])
    const selectedQuickCommand = ref('')

    const buildExamplesBasePath = () => {
      const settings = settingsStore.settings || {}
      if (settings.custom_examples_path) {
        return settings.custom_examples_path
      }
      if (settings.examples_path) {
        return settings.examples_path
      }
      if (settings.mofa_dir) {
        return `${settings.mofa_dir}/python/examples`
      }
      return ''
    }

    const filterQuickCommands = () => {
      if (!commandSearch.value) {
        filteredQuickCommands.value = quickCommands.value
        return
      }
      const query = commandSearch.value.toLowerCase()
      filteredQuickCommands.value = quickCommands.value.filter((item) => item.name.toLowerCase().includes(query))
    }

    const copyToClipboard = async (text) => {
      if (navigator.clipboard && window.isSecureContext) {
        try {
          await navigator.clipboard.writeText(text)
          return
        } catch (error) {
          console.warn('Clipboard API failed, falling back:', error)
        }
      }

      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      try {
        const successful = document.execCommand('copy')
        if (!successful) {
          throw new Error('execCommand copy failed')
        }
      } finally {
        document.body.removeChild(textArea)
      }
    }

    const copyCommand = async (command) => {
      selectedQuickCommand.value = command.name

      const settings = settingsStore.settings || {}
      let examplesPath = command.path || ''
      if (!examplesPath) {
        const basePath = buildExamplesBasePath()
        if (basePath) {
          examplesPath = `${basePath}/${command.name}`
        }
      }

      let dataflowFile = `${command.name}_dataflow.yml`

      try {
        const response = await fetch(`${API_BASE_URL}/agents/${command.name}/dataflow-file`)
        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            dataflowFile = data.dataflow_file
            examplesPath = data.agent_path || examplesPath
          }
        }

        if (!examplesPath) {
          const basePath = buildExamplesBasePath()
          if (basePath) {
            examplesPath = `${basePath}/${command.name}`
          }
        }

        const fullCommand = `cd ${examplesPath} && dora up && dora build ${dataflowFile} && dora start ${dataflowFile}`
        await copyToClipboard(fullCommand)
        ElMessage.success(t('electronTerminal.commandCopied', { name: command.name }) || `Command copied (${dataflowFile})`)
      } catch (error) {
        console.error('Failed to copy command:', error)

        const basePath = buildExamplesBasePath()
        const fallbackPath = basePath ? `${basePath}/${command.name}` : command.path
        const fallbackCommand = `cd ${fallbackPath || '.'} && dora up && dora build ${command.name}_dataflow.yml && dora start ${command.name}_dataflow.yml`
        try {
          await copyToClipboard(fallbackCommand)
          ElMessage.warning(t('electronTerminal.commandCopiedFallback', { name: command.name }) || 'Copied fallback command')
        } catch (fallbackError) {
          console.error('Fallback copy failed:', fallbackError)
          ElMessage.error(t('electronTerminal.commandCopyFailed') || 'Failed to copy command. See console for details.')
        }
      }
    }

    const toggleQuickBar = () => {
      isQuickBarCollapsed.value = !isQuickBarCollapsed.value
    }

    const loadQuickCommands = async () => {
      try {
        if (!settingsStore.settings?.mofa_dir) {
          await settingsStore.fetchSettings().catch(() => {})
        }

        await agentStore.fetchAgents()
        const exampleAgents = agentStore.exampleAgents || []
        const basePath = buildExamplesBasePath()

        if (exampleAgents.length) {
          quickCommands.value = exampleAgents.map((name) => ({
            name,
            path: basePath ? `${basePath}/${name}` : ''
          }))
        } else {
          quickCommands.value = [
            { name: 'hello_world', path: basePath ? `${basePath}/hello_world` : '' },
            { name: 'add_numbers', path: basePath ? `${basePath}/add_numbers` : '' }
          ]
        }
      } catch (error) {
        console.error('Failed to load quick commands:', error)
        const basePath = buildExamplesBasePath()
        quickCommands.value = [
          { name: 'hello_world', path: basePath ? `${basePath}/hello_world` : '' },
          { name: 'add_numbers', path: basePath ? `${basePath}/add_numbers` : '' }
        ]
      } finally {
        filteredQuickCommands.value = quickCommands.value
      }
    }

    const isVisible = computed(() => route.path === '/local-terminal')

    const getTheme = () => (preferences.theme === 'light' ? LIGHT_THEME : DARK_THEME)

    const defaultShell = computed(() => {
      const configured = settingsStore.settings?.local_terminal_shell?.trim()
      if (configured) {
        return configured
      }
      if (defaultProfile.value.shell) {
        return defaultProfile.value.shell
      }
      if (hostPlatform.value === 'win32') {
        return 'powershell.exe'
      }
      if (hostPlatform.value === 'darwin') {
        return '/bin/zsh'
      }
      return '/bin/bash'
    })

    const defaultCwd = computed(() => {
      const configured = settingsStore.settings?.local_terminal_cwd?.trim()
      if (configured) {
        return configured
      }
      if (settingsStore.settings?.mofa_dir) {
        return settingsStore.settings.mofa_dir
      }
      if (defaultProfile.value.cwd) {
        return defaultProfile.value.cwd
      }
      return ''
    })

    const resolvedShellPlaceholder = computed(() => defaultShell.value || '')
    const resolvedCwdPlaceholder = computed(() => defaultCwd.value || '')

    const flushPending = (session) => {
      if (!session.pendingChunks?.length || !session.term) {
        return
      }
      session.pendingChunks.forEach(chunk => session.term.write(chunk))
      session.pendingChunks = []
    }

    const syncTerminalGeometry = async (session) => {
      if (!session?.term || !terminalApi.value) {
        return
      }
      const cols = session.term.cols
      const rows = session.term.rows
      if (!Number.isFinite(cols) || cols <= 0 || !Number.isFinite(rows) || rows <= 0) {
        return
      }
      try {
        await terminalApi.value.resize(session.id, cols, rows)
        session.cols = cols
        session.rows = rows
      } catch (error) {
        console.warn('Failed to sync terminal size:', error)
      }
    }

    const tryFitSession = (session) => {
      if (!session?.term || !session.fitAddon) {
        return false
      }
      const mountPoint = containerRefs[session.id]
      if (!mountPoint) {
        return false
      }
      const bounds = typeof mountPoint.getBoundingClientRect === 'function'
        ? mountPoint.getBoundingClientRect()
        : null
      if (!bounds || bounds.width < 20 || bounds.height < 20) {
        session.pendingFit = true
        return false
      }
      try {
        session.fitAddon.fit()
        session.pendingFit = false
        syncTerminalGeometry(session)
        return true
      } catch (error) {
        console.warn('Failed to fit terminal', error)
        return false
      }
    }

    const focusActiveTerminal = () => {
      const current = sessions.value.find(item => item.id === activeSessionId.value)
      if (!current?.term) {
        return
      }
      if (tryFitSession(current)) {
        try {
          current.term.focus()
        } catch (error) {
          console.warn('Unable to focus terminal:', error)
        }
      }
    }

    const registerContainer = (sessionId, el) => {
      if (!el) {
        delete containerRefs[sessionId]
        return
      }
      containerRefs[sessionId] = el
      const session = sessions.value.find(item => item.id === sessionId)
      if (session && !session.term) {
        createTerminalInstance(session)
      } else if (session?.pendingFit) {
        if (tryFitSession(session) && session.status === 'starting') {
          session.status = 'running'
          flushPending(session)
        }
      }
    }

    const resolveShell = (shellOverride) => shellOverride?.trim() || defaultShell.value
    const resolveCwd = (cwdOverride) => cwdOverride?.trim() || defaultCwd.value

    const ensureDefaultProfile = async () => {
      if (!terminalApi.value || defaultProfile.value.initialized) {
        return
      }
      try {
        const profile = await terminalApi.value.getDefaultProfile()
        if (profile) {
          defaultProfile.value = { ...profile, initialized: true }
        } else {
          defaultProfile.value.initialized = true
        }
      } catch (error) {
        console.warn('Failed to load default terminal profile:', error)
        defaultProfile.value.initialized = true
      }
    }

    const createTerminalInstance = (session) => {
      const mountPoint = containerRefs[session.id]
      if (!mountPoint || session.term) {
        return
      }

      const term = new Terminal({
        fontFamily: '"JetBrains Mono", "Fira Code", "Menlo", monospace',
        fontSize: preferences.fontSize,
        convertEol: true,
        cursorBlink: true,
        scrollback: 5000,
        theme: getTheme(),
        allowTransparency: true,
        rendererType: 'canvas'
      })

      const fitAddon = new FitAddon()
      term.loadAddon(fitAddon)
      term.open(mountPoint)

      session.term = term
      session.fitAddon = fitAddon

      window.requestAnimationFrame(() => {
        const fitted = tryFitSession(session)
        if (fitted) {
          session.status = 'running'
          flushPending(session)
          try {
            term.focus()
          } catch (error) {
            console.warn('Failed to focus terminal after mount:', error)
          }
        }
      })

      term.onData((chunk) => {
        if (!terminalApi.value || session.status !== 'running') {
          return
        }
        terminalApi.value.write(session.id, chunk)
      })
    }

    const spawnSession = async (options = {}) => {
      if (!terminalApi.value) {
        ElMessage.warning(t('electronTerminal.unavailable') || 'Desktop terminal is only available inside the Electron app.')
        return
      }
      if (isCreatingSession.value) {
        return
      }

      isCreatingSession.value = true
      try {
        await ensureDefaultProfile()
        const resolvedShell = resolveShell(options.shell)
        if (!resolvedShell) {
          throw new Error(t('electronTerminal.shellMissing') || 'Shell command is required.')
        }
        const resolvedCwd = resolveCwd(options.cwd)
        const result = await terminalApi.value.createSession({
          shellCommand: resolvedShell,
          cwd: resolvedCwd,
          cols: options.cols,
          rows: options.rows
        })

        const baseTitle = t('electronTerminal.tabTitlePrefix') || 'Shell'
        const title = options.title?.trim() || `${baseTitle} ${sessions.value.length + 1}`

        const session = {
          id: result.id,
          shell: result.shell || resolvedShell,
          cwd: result.cwd || resolvedCwd,
          title,
          status: 'starting',
          term: null,
          fitAddon: null,
          pendingChunks: [],
          pendingFit: false,
          config: {
            shell: resolvedShell,
            cwd: resolvedCwd
          }
        }

        sessions.value = [...sessions.value, session]
        activeSessionId.value = session.id

        await nextTick()
        createTerminalInstance(session)
      } catch (error) {
        console.error('Failed to create electron terminal session:', error)
        ElMessage.error(error?.message || 'Failed to start local terminal')
      } finally {
        isCreatingSession.value = false
      }
    }

    const closeSession = async (sessionId) => {
      const sessionIndex = sessions.value.findIndex(item => item.id === sessionId)
      if (sessionIndex === -1) {
        return
      }
      const session = sessions.value[sessionIndex]
      try {
        await terminalApi.value?.close(session.id)
      } catch (error) {
        console.warn('Failed to close terminal session:', error)
      }
      try {
        session.term?.dispose()
      } catch (error) {
        console.warn('Failed to dispose terminal instance:', error)
      }
      delete containerRefs[session.id]
      const nextSessions = [...sessions.value]
      nextSessions.splice(sessionIndex, 1)
      sessions.value = nextSessions

      if (nextSessions.length === 0) {
        activeSessionId.value = ''
        return
      }

      if (activeSessionId.value === sessionId) {
        const next = nextSessions[Math.max(0, sessionIndex - 1)] || nextSessions[0]
        activeSessionId.value = next.id
        focusActiveTerminal()
      }
    }

    const handleTabEdit = async (targetName, action) => {
      if (action === 'remove') {
        await closeSession(targetName)
      }
      if (action === 'add') {
        await spawnSession()
      }
    }

    const handleTabClick = () => {
      window.requestAnimationFrame(() => {
        focusActiveTerminal()
      })
    }

    const handleData = (payload) => {
      if (!payload || !payload.id) {
        return
      }
      const session = sessions.value.find(item => item.id === payload.id)
      if (!session) {
        return
      }
      if (session.term) {
        session.term.write(payload.data)
      } else {
        session.pendingChunks = session.pendingChunks || []
        session.pendingChunks.push(payload.data)
      }
    }

    const handleExit = (payload) => {
      if (!payload || !payload.id) {
        return
      }
      const session = sessions.value.find(item => item.id === payload.id)
      if (!session) {
        return
      }
      session.status = 'exited'
      session.pendingFit = false
      if (session.term) {
        session.term.write(`\r\n[process exited with code ${payload.exitCode ?? '0'}]\r\n`)
      } else {
        session.pendingChunks = session.pendingChunks || []
        session.pendingChunks.push(`\r\n[process exited with code ${payload.exitCode ?? '0'}]\r\n`)
      }
    }

    const refreshActive = () => {
      const current = sessions.value.find(item => item.id === activeSessionId.value)
      if (!current) {
        return
      }
      if (current.term && current.fitAddon) {
        if (tryFitSession(current) && current.status === 'starting') {
          current.status = 'running'
          flushPending(current)
        }
      }
    }

    const openSessionDialog = async () => {
      if (!terminalApi.value) {
        ElMessage.warning(t('electronTerminal.unavailable') || 'Desktop terminal is only available inside the Electron app.')
        return
      }
      await ensureDefaultProfile()
      sessionForm.title = ''
      sessionForm.shell = defaultShell.value
      sessionForm.cwd = defaultCwd.value
      showNewSessionDialog.value = true
    }

    const handleCreateFromDialog = async () => {
      const payload = {
        title: sessionForm.title,
        shell: sessionForm.shell,
        cwd: sessionForm.cwd
      }
      showNewSessionDialog.value = false
      await spawnSession(payload)
    }

    const applyShellDefault = () => {
      sessionForm.shell = defaultShell.value
    }

    const applyCwdDefault = () => {
      sessionForm.cwd = defaultCwd.value
    }

    onMounted(async () => {
      if (!terminalApi.value) {
        return
      }
      const available = await terminalApi.value.isAvailable()
      isElectronAvailable.value = !!available
      if (!available) {
        return
      }

      disposers.push(terminalApi.value.onData(handleData))
      disposers.push(terminalApi.value.onExit(handleExit))

      const handleResize = () => {
        refreshActive()
      }
      window.addEventListener('resize', handleResize)
      disposers.push(() => window.removeEventListener('resize', handleResize))

      await ensureDefaultProfile()
    })

    onBeforeUnmount(() => {
      disposers.forEach((dispose) => {
        try {
          dispose?.()
        } catch (error) {
          console.warn('Failed to run disposer:', error)
        }
      })
      disposers.length = 0

      sessions.value.forEach((session) => {
        try {
          terminalApi.value?.close(session.id)
        } catch (error) {
          console.warn('Failed to close terminal on unmount:', error)
        }
        try {
          session.term?.dispose()
        } catch (error) {
          console.warn('Failed to dispose terminal on unmount:', error)
        }
      })
      sessions.value = []
    })

    const stopFontWatch = watch(
      () => preferences.fontSize,
      (size) => {
        sessions.value.forEach(session => {
          if (session.term) {
            session.term.options.fontSize = size
            if (tryFitSession(session) && session.status === 'starting') {
              session.status = 'running'
              flushPending(session)
            }
          }
        })
      }
    )
    disposers.push(stopFontWatch)

    const stopThemeWatch = watch(
      () => preferences.theme,
      () => {
        const theme = getTheme()
        sessions.value.forEach(session => {
          session.term?.setOption('theme', theme)
        })
      }
    )
    disposers.push(stopThemeWatch)

    const stopThemeSync = watch(
      () => settingsStore.settings?.theme,
      (theme) => {
        preferences.theme = theme === 'dark' ? 'dark' : 'light'
      }
    )
    disposers.push(stopThemeSync)

    const stopFontSync = watch(
      () => settingsStore.settings?.editor_font_size,
      (size) => {
        if (size) {
          preferences.fontSize = Math.min(Math.max(size, 10), 24)
        }
      }
    )
    disposers.push(stopFontSync)

    const attemptedInitialSession = ref(false)
    const stopVisibilityWatch = watch(
      [isElectronAvailable, isVisible],
      async ([available, visible]) => {
        if (!available || !visible) {
          return
        }
        if (!attemptedInitialSession.value && sessions.value.length === 0) {
          attemptedInitialSession.value = true
          await spawnSession()
        } else {
          refreshActive()
        }
      },
      { immediate: true }
    )
    disposers.push(stopVisibilityWatch)

    onMounted(() => {
      loadQuickCommands()
    })

    return {
      t,
      sessions,
      activeSessionId,
      preferences,
      isElectronAvailable,
      isCreatingSession,
      showNewSessionDialog,
      sessionForm,
      resolvedShellPlaceholder,
      resolvedCwdPlaceholder,
      spawnSession,
      handleTabEdit,
      handleTabClick,
      registerContainer,
      openSessionDialog,
      handleCreateFromDialog,
      applyShellDefault,
      applyCwdDefault,
      cardThemeClass,
      isQuickBarCollapsed,
      toggleQuickBar,
      commandSearch,
      filteredQuickCommands,
      selectedQuickCommand,
      filterQuickCommands,
      copyCommand
    }
  }
}
</script>

<style scoped>
.electron-terminal-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.terminal-layout {
  display: flex;
  flex-grow: 1;
  gap: 16px;
  overflow: hidden;
  width: 100%;
  position: relative;
}

.quickbar {
  width: 280px;
  min-width: 250px;
  max-width: 320px;
  flex-shrink: 0;
  background: var(--card-background);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: var(--card-shadow);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.quickbar.collapsed {
  width: 60px;
  min-width: 60px;
  max-width: 60px;
}

.quickbar:hover {
  box-shadow: var(--card-shadow-hover);
}

.quickbar-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, var(--mofa-red) 0%, var(--mofa-orange) 100%);
  color: white;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}

.quickbar.collapsed .quickbar-header {
  padding: 16px 8px;
  justify-content: center;
}

.quickbar-header:hover {
  background: linear-gradient(135deg, var(--mofa-orange) 0%, var(--mofa-red) 100%);
}

.quickbar-title {
  font-weight: 600;
  letter-spacing: 0.5px;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.quickbar-title-collapsed {
  font-size: 18px;
  font-weight: 700;
  opacity: 1;
  transition: opacity 0.2s ease;
}

.collapse-icon {
  transition: transform 0.3s ease;
}

.collapse-icon.rotated {
  transform: rotate(180deg);
}

.quickbar.collapsed .quickbar-header {
  position: relative;
  flex-direction: column;
  gap: 8px;
}

.quickbar.collapsed .quickbar-header::after {
  content: '';
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 4px solid white;
  border-top: 3px solid transparent;
  border-bottom: 3px solid transparent;
}

.quickbar-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  padding: 16px;
  gap: 16px;
}

.quickbar-search {
  padding: 0;
}

.quickbar-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quickbar-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--item-background);
  border: 1px solid var(--item-border);
  cursor: pointer;
  transition: all 0.2s ease;
}

.quickbar-item:hover {
  background: var(--item-background-hover);
  border-color: var(--item-border-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.quickbar-item.active {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.item-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.item-label {
  font-weight: 500;
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-control {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary-color, #6b7280);
}

.terminal-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
}

.terminal-card :deep(.el-card__body) {
  background: transparent;
}

.terminal-card-dark {
  background: radial-gradient(circle at top, #161b29 0%, #0b0d15 65%);
  border: 1px solid rgba(148, 163, 184, 0.12);
  color: #e2e8f0;
}

.terminal-card-light {
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.24);
}

.terminal-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.terminal-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0 16px;
}

.terminal-tabs :deep(.el-tabs__content) {
  flex: 1;
  padding: 0;
  height: 100%;
  overflow: hidden;
}

.terminal-tabs :deep(.el-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.terminal-meta {
  display: flex;
  gap: 16px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border-color, #e5e7eb);
  color: var(--text-secondary-color, #6b7280);
  font-size: 12px;
  align-items: center;
  overflow: hidden;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-item .el-icon {
  font-size: 14px;
}

.truncate {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.terminal-surface {
  position: relative;
  flex: 1;
  border-radius: 8px;
  margin: 16px;
  padding: 12px;
  overflow: hidden;
}

.terminal-card-dark .terminal-surface {
  background: linear-gradient(180deg, rgba(20, 24, 36, 0.92) 0%, rgba(28, 32, 46, 0.98) 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 16px 40px rgba(17, 24, 39, 0.35);
}

.terminal-card-light .terminal-surface {
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.98) 100%) !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 8px 24px rgba(15, 23, 42, 0.25);
}

.terminal-card-dark .terminal-surface.is-active {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 16px 40px rgba(25, 94, 140, 0.45);
}

.terminal-card-light .terminal-surface.is-active {
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 8px 24px rgba(59, 130, 246, 0.35);
}

.terminal-surface.is-exited {
  opacity: 0.92;
  filter: grayscale(0.1);
}

.terminal-surface :deep(.xterm) {
  height: 100%;
  background: transparent !important;
}

.terminal-surface :deep(.xterm .xterm-viewport) {
  background: transparent !important;
}

.terminal-surface :deep(.xterm .xterm-screen) {
  background: transparent !important;
}

.terminal-loading,
.terminal-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #f8fafc;
  background: rgba(17, 24, 39, 0.4);
  backdrop-filter: blur(4px);
  font-size: 14px;
  padding: 12px;
  text-align: center;
}

.terminal-loading .spinner {
  animation: spin 1.2s linear infinite;
  font-size: 24px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-placeholder {
  padding: 48px 0;
}

.info-card {
  flex: none;
}

.info-empty {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-help {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-tertiary-color, #9ca3af);
}
</style>
