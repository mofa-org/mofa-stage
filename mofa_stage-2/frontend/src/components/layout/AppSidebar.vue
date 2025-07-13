<template>
  <div class="sidebar" :class="{ 'collapsed': isCollapsed }">
    <!-- 浮动折叠按钮 -->
    <div class="collapse-toggle" @click="toggleCollapse">
      <el-icon>
        <Expand v-if="isCollapsed" />
        <Fold v-else />
      </el-icon>
    </div>
    
    <div class="sidebar-menu">
      <el-menu
        router
        :default-active="activeRoute"
        class="sidebar-nav"
        :background-color="computedTheme.bgColor"
        :text-color="computedTheme.textColor"
        :active-text-color="computedTheme.activeTextColor"
        :collapse="isCollapsed">
        <el-menu-item index="/agents" class="menu-item">
          <el-icon><Menu /></el-icon>
          <span v-if="!isCollapsed">{{ $t('sidebar.agentsList') }}</span>
        </el-menu-item>
        <el-menu-item index="/terminal" v-if="showTerminal" class="menu-item">
          <el-icon><Monitor /></el-icon>
          <span v-if="!isCollapsed">{{ $t('sidebar.commandLine') }}</span>
        </el-menu-item>
        <el-menu-item index="/webssh" v-if="showWebSSH" class="menu-item">
          <el-icon><Monitor /></el-icon>
          <span v-if="!isCollapsed">{{ $t('sidebar.webSSH') }}</span>
        </el-menu-item>
        <el-menu-item index="/ttyd" v-if="showTtyd" class="menu-item">
          <el-icon><Monitor /></el-icon>
          <span v-if="!isCollapsed">{{ $t('sidebar.ttyd') || 'ttyd Terminal' }}</span>
        </el-menu-item>
        <el-menu-item index="/settings" class="menu-item">
          <el-icon><Setting /></el-icon>
          <span v-if="!isCollapsed">{{ $t('sidebar.settings') }}</span>
        </el-menu-item>
      </el-menu>
    </div>
    <div class="sidebar-footer" v-if="!isCollapsed">
      <div class="version-info">
        <span class="version-label">MoFA Stage</span>
        <span class="version-number">v0.5.0</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, watch, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '../../store/settings'
import { useI18n } from 'vue-i18n'
import { Menu, Setting, Connection, Monitor, Fold, Expand } from '@element-plus/icons-vue'

export default {
  name: 'AppSidebar',
  components: {
    Menu,
    Setting,
    Connection,
    Monitor,
    Fold,
    Expand
  },
  setup() {
    const route = useRoute()
    const settingsStore = useSettingsStore()
    const { t } = useI18n()
    
    // 折叠状态
    const isCollapsed = ref(false)
    
    // 切换折叠状态
    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value
    }
    
    const activeRoute = computed(() => {
      // 对于 agents 相关的路由，都映射到 /agents
      if (route.path.startsWith('/agents')) {
        return '/agents'
      }
      return route.path
    })
    
    const computedTheme = computed(() => {
      const isDark = settingsStore.settings.theme === 'dark'
      return {
        bgColor: isDark ? 'var(--sidebar-background)' : 'var(--sidebar-background)',
        textColor: isDark ? 'var(--sidebar-text-color)' : 'var(--sidebar-text-color)',
        activeTextColor: isDark ? 'var(--sidebar-active-text-color)' : 'var(--sidebar-active-text-color)'
      }
    })
    
    const showTerminal = computed(() => {
      const mode = settingsStore.settings.terminal_display_mode || 'both'
      return mode === 'both' || mode === 'terminal'
    })
    
    const showWebSSH = computed(() => {
      const mode = settingsStore.settings.terminal_display_mode || 'both'
      return mode === 'both' || mode === 'webssh'
    })
    
    const showTtyd = computed(() => {
      const mode = settingsStore.settings.terminal_display_mode || 'both'
      return mode === 'both' || mode === 'ttyd'
    })
    
    // Watch for terminal display mode changes
    watch(
      () => settingsStore.settings.terminal_display_mode,
      (newMode) => {
        console.log('Terminal display mode changed:', newMode);
      }
    );
    
    return {
      activeRoute,
      computedTheme,
      showTerminal,
      showWebSSH,
      showTtyd,
      isCollapsed,
      toggleCollapse
    }
  }
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, var(--sidebar-background) 0%, rgba(248, 250, 254, 0.95) 100%);
  backdrop-filter: blur(10px);
  border-right: 1px solid var(--border-color);
  color: var(--sidebar-text-color);
  display: flex;
  flex-direction: column;
  height: calc(100vh - 70px);
  overflow: hidden;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
  transition: width 0.3s ease;
  position: relative;
}

.sidebar.collapsed {
  width: 64px;
}

/* 浮动折叠按钮 */
.collapse-toggle {
  position: absolute;
  top: 8px;
  right: 12px;
  width: 24px;
  height: 24px;
  background: var(--sidebar-background);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 100;
  font-size: 12px;
  color: var(--sidebar-text-color);
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.collapse-toggle:hover {
  background: var(--mofa-teal);
  color: white;
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(107, 206, 210, 0.3);
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0 16px 0;
}

.sidebar.collapsed .sidebar-menu {
  padding: 16px 0;
}

.sidebar-nav {
  border-right: none;
  background: transparent !important;
}

.sidebar-nav .el-menu-item {
  margin: 4px 16px;
  border-radius: 0;
  color: var(--sidebar-text-color);
  font-weight: 500;
  height: 48px;
  line-height: 48px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.sidebar.collapsed .sidebar-nav .el-menu-item {
  margin: 4px 8px;
  text-align: center;
  padding: 0 !important;
  justify-content: center;
}

.sidebar-nav .el-menu-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: linear-gradient(135deg, var(--mofa-red) 0%, var(--mofa-teal) 100%);
  border-radius: 0;
  transition: height 0.3s ease;
}

.sidebar-nav .el-menu-item:hover {
  background: rgba(107, 206, 210, 0.1);
  color: var(--mofa-teal);
  transform: translateX(4px);
}

.sidebar.collapsed .sidebar-nav .el-menu-item:hover {
  transform: none;
}

.sidebar-nav .el-menu-item:hover::before {
  height: 24px;
}

.sidebar-nav .el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(255, 92, 72, 0.1) 0%, rgba(107, 206, 210, 0.1) 100%);
  color: var(--primary-color);
  font-weight: 600;
}

.sidebar-nav .el-menu-item.is-active::before {
  height: 32px;
}

.sidebar-nav .el-menu-item .el-icon {
  margin-right: 12px;
  font-size: 18px;
}

.sidebar.collapsed .sidebar-nav .el-menu-item .el-icon {
  margin-right: 0;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(107, 206, 210, 0.1);
  background: rgba(255, 255, 255, 0.6);
}

.version-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.version-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
}

.version-number {
  font-size: 12px;
  color: var(--text-color-secondary);
  font-family: 'Monaco', 'Consolas', monospace;
  background: rgba(107, 206, 210, 0.1);
  padding: 2px 8px;
  border-radius: 0;
}

/* Dark theme adjustments */
[data-theme="dark"] .sidebar {
  background: linear-gradient(180deg, var(--sidebar-background) 0%, rgba(13, 17, 23, 0.95) 100%);
  border-right-color: var(--border-color);
}

[data-theme="dark"] .collapse-toggle {
  background: var(--sidebar-background);
  border-color: var(--border-color);
}

[data-theme="dark"] .collapse-toggle:hover {
  background: var(--mofa-teal);
  box-shadow: 0 4px 12px rgba(107, 206, 210, 0.4);
}

[data-theme="dark"] .sidebar-footer {
  background: rgba(22, 27, 34, 0.6);
  border-top-color: rgba(107, 206, 210, 0.2);
}

[data-theme="dark"] .sidebar-nav .el-menu-item:hover {
  background: rgba(107, 206, 210, 0.15);
}

[data-theme="dark"] .sidebar-nav .el-menu-item.is-active {
  background: linear-gradient(135deg, rgba(255, 92, 72, 0.15) 0%, rgba(107, 206, 210, 0.15) 100%);
}

[data-theme="dark"] .version-number {
  background: rgba(107, 206, 210, 0.2);
}
</style>
