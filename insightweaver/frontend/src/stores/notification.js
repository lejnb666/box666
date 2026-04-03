import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref([])
  const notificationId = ref(0)

  // Add a success notification
  const success = (message, duration = 3000) => {
    addNotification('success', message, duration)
  }

  // Add an error notification
  const error = (message, duration = 5000) => {
    addNotification('error', message, duration)
  }

  // Add a warning notification
  const warning = (message, duration = 4000) => {
    addNotification('warning', message, duration)
  }

  // Add an info notification
  const info = (message, duration = 3000) => {
    addNotification('info', message, duration)
  }

  // Add a notification with custom type
  const addNotification = (type, message, duration = 3000) => {
    const id = notificationId.value++
    const notification = {
      id,
      type,
      message,
      timestamp: new Date().toISOString()
    }

    notifications.value.push(notification)

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id)
      }, duration)
    }

    return id
  }

  // Remove a notification by ID
  const removeNotification = (id) => {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  // Clear all notifications
  const clearAll = () => {
    notifications.value = []
  }

  // Clear notifications by type
  const clearByType = (type) => {
    notifications.value = notifications.value.filter(n => n.type !== type)
  }

  return {
    notifications,
    success,
    error,
    warning,
    info,
    addNotification,
    removeNotification,
    clearAll,
    clearByType
  }
})
