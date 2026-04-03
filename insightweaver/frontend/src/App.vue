<template>
  <el-config-provider :locale="locale" :size="size">
    <div id="app" :class="['app-container', { 'dark-mode': isDarkMode }]">
      <app-header @toggle-theme="toggleTheme" />

      <el-container class="main-container">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-container>

      <app-footer />

      <!-- Global Loading Overlay -->
      <el-loading
        v-model="globalLoading"
        :fullscreen="true"
        :text="loadingText"
        background="rgba(0, 0, 0, 0.7)"
      />

      <!-- Global Notifications -->
      <el-notification-container />
    </div>
  </el-config-provider>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { useNotificationStore } from '@/stores/notification'
import { ElConfigProvider, ElLoading, ElNotificationContainer } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppFooter from '@/components/layout/AppFooter.vue'

// Stores
const themeStore = useThemeStore()
const notificationStore = useNotificationStore()

// Reactive state
const size = ref('default')
const globalLoading = ref(false)
const loadingText = ref('Loading...')

// Computed properties
const isDarkMode = computed(() => themeStore.isDark)
const locale = computed(() => zhCn)

// Methods
const toggleTheme = () => {
  themeStore.toggleTheme()
}

// Lifecycle
onMounted(() => {
  // Initialize theme from localStorage or system preference
  themeStore.initTheme()

  // Set up global event listeners
  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)
})

// Event handlers
const handleOnline = () => {
  notificationStore.success('Network connection restored')
}

const handleOffline = () => {
  notificationStore.warning('Network connection lost')
}

// Expose global methods
window.$app = {
  showLoading: (text = 'Loading...') => {
    loadingText.value = text
    globalLoading.value = true
  },
  hideLoading: () => {
    globalLoading.value = false
    loadingText.value = 'Loading...'
  }
}
</script>

<style lang="scss">
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
  transition: all 0.3s ease;

  &.dark-mode {
    --el-bg-color: #141414;
    --el-bg-color-overlay: #1d1e1f;
    --el-text-color-primary: #ffffff;
    --el-text-color-regular: #cfd3dc;
    --el-border-color: #363637;
    --el-fill-color-blank: #1d1e1f;
  }

  .main-container {
    flex: 1;
    min-height: 0;
  }
}

// Global transitions
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

// Global scrollbar styling
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--el-scrollbar-bg-color, var(--el-fill-color-light));
}

::-webkit-scrollbar-thumb {
  background: var(--el-border-color-darker);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--el-text-color-secondary);
}

// Responsive design
@media (max-width: 768px) {
  .app-container {
    .main-container {
      flex-direction: column;
    }
  }
}
</style>