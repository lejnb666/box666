import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css/index.css'
import './assets/styles/main.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

// Use plugins
app.use(createPinia())
app.use(router)
app.use(ElementPlus)

// Register all Element Plus icons globally
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Global properties
app.config.globalProperties.$appName = 'InsightWeaver'
app.config.globalProperties.$version = '1.0.0'

app.mount('#app')