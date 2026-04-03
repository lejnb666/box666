import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { researchService } from '@/services/researchService'
import { useNotificationStore } from './notification'

export const useResearchStore = defineStore('research', () => {
  // State
  const currentTask = ref(null)
  const taskHistory = ref([])
  const isLoading = ref(false)
  const error = ref(null)
  const sseConnection = ref(null)
  const isStreaming = ref(false)

  // Getters
  const activeTasks = computed(() =>
    taskHistory.value.filter(task =>
      ['PENDING', 'PLANNING', 'RESEARCHING', 'ANALYZING', 'WRITING'].includes(task.status)
    )
  )

  const completedTasks = computed(() =>
    taskHistory.value.filter(task => task.status === 'COMPLETED')
  )

  const failedTasks = computed(() =>
    taskHistory.value.filter(task => task.status === 'FAILED')
  )

  const taskStats = computed(() => {
    const total = taskHistory.value.length
    const completed = completedTasks.value.length
    const active = activeTasks.value.length
    const failed = failedTasks.value.length

    return {
      total,
      completed,
      active,
      failed,
      successRate: total > 0 ? Math.round((completed / total) * 100) : 0
    }
  })

  // Actions
  async function createResearchTask(researchRequest) {
    const notificationStore = useNotificationStore()

    try {
      isLoading.value = true
      error.value = null

      const response = await researchService.createTask(researchRequest)
      const newTask = response.data

      // Add to task history
      taskHistory.value.unshift(newTask)
      currentTask.value = newTask

      // Start streaming updates
      startStreaming(newTask.id)

      notificationStore.success('Research task created successfully')
      return newTask

    } catch (err) {
      error.value = err.message
      notificationStore.error('Failed to create research task')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTaskHistory() {
    try {
      isLoading.value = true
      error.value = null

      const response = await researchService.getTaskHistory()
      taskHistory.value = response.data

    } catch (err) {
      error.value = err.message
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTaskById(taskId) {
    try {
      isLoading.value = true
      error.value = null

      const response = await researchService.getTask(taskId)
      const task = response.data

      // Update or add task in history
      const existingIndex = taskHistory.value.findIndex(t => t.id === taskId)
      if (existingIndex >= 0) {
        taskHistory.value[existingIndex] = task
      } else {
        taskHistory.value.unshift(task)
      }

      currentTask.value = task
      return task

    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function cancelTask(taskId) {
    const notificationStore = useNotificationStore()

    try {
      isLoading.value = true
      error.value = null

      await researchService.cancelTask(taskId)

      // Update task status locally
      const task = taskHistory.value.find(t => t.id === taskId)
      if (task) {
        task.status = 'CANCELLED'
      }

      // Stop streaming if this is the current task
      if (currentTask.value?.id === taskId) {
        stopStreaming()
      }

      notificationStore.success('Task cancelled successfully')

    } catch (err) {
      error.value = err.message
      notificationStore.error('Failed to cancel task')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function startStreaming(taskId) {
    if (sseConnection.value) {
      stopStreaming()
    }

    isStreaming.value = true
    sseConnection.value = researchService.createEventStream(taskId, {
      onMessage: handleSSEMessage,
      onError: handleSSEError,
      onClose: handleSSEClose
    })
  }

  function stopStreaming() {
    if (sseConnection.value) {
      sseConnection.value.close()
      sseConnection.value = null
    }
    isStreaming.value = false
  }

  function handleSSEMessage(event) {
    try {
      const data = JSON.parse(event.data)

      // Update current task with streaming data
      if (currentTask.value && currentTask.value.id === data.taskId) {
        updateTaskFromStream(currentTask.value, data)
      }

      // Update task in history
      const taskIndex = taskHistory.value.findIndex(t => t.id === data.taskId)
      if (taskIndex >= 0) {
        updateTaskFromStream(taskHistory.value[taskIndex], data)
      }

    } catch (err) {
      console.error('Failed to parse SSE message:', err)
    }
  }

  function updateTaskFromStream(task, streamData) {
    // Update task properties based on stream data
    if (streamData.status) {
      task.status = streamData.status
    }

    if (streamData.progressPercentage !== undefined) {
      task.progressPercentage = streamData.progressPercentage
    }

    if (streamData.agentStatuses) {
      task.agentStatuses = { ...task.agentStatuses, ...streamData.agentStatuses }
    }

    if (streamData.intermediateResults) {
      task.intermediateResults = [
        ...(task.intermediateResults || []),
        ...streamData.intermediateResults
      ]
    }

    if (streamData.finalReport) {
      task.finalReport = streamData.finalReport
    }

    if (streamData.errorMessage) {
      task.errorMessage = streamData.errorMessage
    }

    // Update timestamps
    task.updatedAt = new Date().toISOString()
  }

  function handleSSEError(error) {
    console.error('SSE connection error:', error)
    const notificationStore = useNotificationStore()
    notificationStore.warning('Real-time updates connection lost. Trying to reconnect...')

    // Attempt to reconnect after a delay
    setTimeout(() => {
      if (currentTask.value) {
        startStreaming(currentTask.value.id)
      }
    }, 5000)
  }

  function handleSSEClose() {
    isStreaming.value = false
    sseConnection.value = null
  }

  async function clearTaskHistory() {
    const notificationStore = useNotificationStore()

    try {
      // This would call an API endpoint to clear history on the server
      // await researchService.clearHistory()

      taskHistory.value = []
      currentTask.value = null
      stopStreaming()

      notificationStore.success('Task history cleared')

    } catch (err) {
      error.value = err.message
      notificationStore.error('Failed to clear task history')
    }
  }

  function getTaskProgress(taskId) {
    const task = taskHistory.value.find(t => t.id === taskId)
    return task ? calculateTaskProgress(task) : 0
  }

  function calculateTaskProgress(task) {
    if (!task) return 0

    // Calculate progress based on agent statuses and overall status
    const statusProgress = {
      'PENDING': 0,
      'PLANNING': 25,
      'RESEARCHING': 50,
      'ANALYZING': 75,
      'WRITING': 90,
      'COMPLETED': 100,
      'FAILED': 0,
      'CANCELLED': 0
    }

    const baseProgress = statusProgress[task.status] || 0

    // If we have detailed agent progress, use that for more accuracy
    if (task.agentStatuses) {
      const agentProgresses = Object.values(task.agentStatuses)
        .map(agent => agent.progress || 0)
        .filter(progress => typeof progress === 'number')

      if (agentProgresses.length > 0) {
        const avgAgentProgress = agentProgresses.reduce((sum, p) => sum + p, 0) / agentProgresses.length
        return Math.round(avgAgentProgress * 100)
      }
    }

    return baseProgress
  }

  function formatTaskDuration(task) {
    if (!task.createdAt) return 'Unknown'

    const startTime = new Date(task.createdAt)
    const endTime = task.completedAt ? new Date(task.completedAt) : new Date()
    const durationMs = endTime - startTime
    const durationMinutes = Math.round(durationMs / 60000)

    if (durationMinutes < 1) return 'Less than 1 minute'
    if (durationMinutes < 60) return `${durationMinutes} minute${durationMinutes !== 1 ? 's' : ''}`

    const hours = Math.floor(durationMinutes / 60)
    const remainingMinutes = durationMinutes % 60

    if (remainingMinutes === 0) return `${hours} hour${hours !== 1 ? 's' : ''}`
    return `${hours}h ${remainingMinutes}m`
  }

  // Cleanup on store disposal
  function $reset() {
    currentTask.value = null
    taskHistory.value = []
    isLoading.value = false
    error.value = null
    stopStreaming()
  }

  return {
    // State
    currentTask,
    taskHistory,
    isLoading,
    error,
    isStreaming,
    // Getters
    activeTasks,
    completedTasks,
    failedTasks,
    taskStats,
    // Actions
    createResearchTask,
    fetchTaskHistory,
    fetchTaskById,
    cancelTask,
    startStreaming,
    stopStreaming,
    clearTaskHistory,
    getTaskProgress,
    calculateTaskProgress,
    formatTaskDuration,
    $reset
  }
})