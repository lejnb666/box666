import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // State
  const isDark = ref(false)
  const themeMode = ref('light') // 'light', 'dark', 'auto'

  // Getters
  const isDarkMode = computed(() => {
    if (themeMode.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return themeMode.value === 'dark'
  })

  const themeClass = computed(() => {
    return isDarkMode.value ? 'dark' : 'light'
  })

  // Actions
  function setTheme(mode) {
    themeMode.value = mode
    applyTheme()
    saveThemeToStorage()
  }

  function toggleTheme() {
    if (themeMode.value === 'light') {
      setTheme('dark')
    } else if (themeMode.value === 'dark') {
      setTheme('light')
    } else {
      setTheme(isDarkMode.value ? 'light' : 'dark')
    }
  }

  function applyTheme() {
    const html = document.documentElement

    if (isDarkMode.value) {
      html.classList.add('dark')
      html.setAttribute('data-theme', 'dark')
    } else {
      html.classList.remove('dark')
      html.setAttribute('data-theme', 'light')
    }

    // Update Element Plus theme
    isDark.value = isDarkMode.value
  }

  function initTheme() {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('insightweaver-theme')
    if (savedTheme) {
      themeMode.value = savedTheme
    }

    // Initialize theme
    applyTheme()

    // Listen for system theme changes if in auto mode
    if (themeMode.value === 'auto') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', handleSystemThemeChange)
    }
  }

  function handleSystemThemeChange(event) {
    if (themeMode.value === 'auto') {
      applyTheme()
    }
  }

  function saveThemeToStorage() {
    localStorage.setItem('insightweaver-theme', themeMode.value)
  }

  // Initialize theme on store creation
  initTheme()

  return {
    // State
    isDark,
    themeMode,
    // Getters
    isDarkMode,
    themeClass,
    // Actions
    setTheme,
    toggleTheme,
    applyTheme,
    initTheme
  }
})