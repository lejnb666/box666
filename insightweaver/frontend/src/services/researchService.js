import axios from 'axios'
import { useNotificationStore } from '@/stores/notification'

// Create axios instance
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add request timestamp
    config.metadata = { startTime: new Date() }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Calculate request duration
    response.config.metadata.endTime = new Date()
    response.duration = response.config.metadata.endTime - response.config.metadata.startTime

    return response
  },
  (error) => {
    const notificationStore = useNotificationStore()

    // Handle common error responses
    if (error.response) {
      switch (error.response.status) {
        case 401:
          notificationStore.error('Authentication required. Please login again.')
          // Redirect to login or refresh token
          break
        case 403:
          notificationStore.error('Access denied. Insufficient permissions.')
          break
        case 404:
          notificationStore.error('Resource not found.')
          break
        case 429:
          notificationStore.error('Too many requests. Please try again later.')
          break
        case 500:
          notificationStore.error('Server error. Please try again later.')
          break
        default:
          notificationStore.error(error.response.data?.message || 'An error occurred')
      }
    } else if (error.request) {
      notificationStore.error('Network error. Please check your connection.')
    } else {
      notificationStore.error('Request failed. Please try again.')
    }

    return Promise.reject(error)
  }
)

// Research Service
export const researchService = {
  // Create a new research task
  async createTask(researchRequest) {
    try {
      const response = await apiClient.post('/research', researchRequest)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Get all tasks for current user
  async getTaskHistory() {
    try {
      const response = await apiClient.get('/research')
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Get specific task by ID
  async getTask(taskId) {
    try {
      const response = await apiClient.get(`/research/${taskId}`)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Cancel a task
  async cancelTask(taskId) {
    try {
      const response = await apiClient.post(`/research/${taskId}/cancel`)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Get task history/audit trail
  async getTaskHistoryDetails(taskId) {
    try {
      const response = await apiClient.get(`/research/${taskId}/history`)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Update task priority
  async updateTaskPriority(taskId, priority) {
    try {
      const response = await apiClient.put(`/research/${taskId}/priority?priority=${priority}`)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Get user statistics
  async getUserStats() {
    try {
      const response = await apiClient.get('/research/stats')
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Create Server-Sent Events stream for real-time updates
  createEventStream(taskId, handlers = {}) {
    const eventSource = new EventSource(`/api/v1/research/${taskId}/stream`, {
      withCredentials: true
    })

    // Set up event handlers
    eventSource.onopen = (event) => {
      console.log('SSE connection opened for task:', taskId)
      if (handlers.onOpen) {
        handlers.onOpen(event)
      }
    }

    eventSource.onmessage = (event) => {
      if (handlers.onMessage) {
        handlers.onMessage(event)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      if (handlers.onError) {
        handlers.onError(error)
      }

      // Attempt reconnection
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('SSE connection closed, attempting to reconnect...')
        setTimeout(() => {
          this.createEventStream(taskId, handlers)
        }, 3000)
      }
    }

    eventSource.addEventListener('close', (event) => {
      console.log('SSE connection closed')
      if (handlers.onClose) {
        handlers.onClose(event)
      }
    })

    // Handle specific event types
    eventSource.addEventListener('status_update', (event) => {
      if (handlers.onStatusUpdate) {
        handlers.onStatusUpdate(JSON.parse(event.data))
      }
    })

    eventSource.addEventListener('agent_update', (event) => {
      if (handlers.onAgentUpdate) {
        handlers.onAgentUpdate(JSON.parse(event.data))
      }
    })

    eventSource.addEventListener('progress_update', (event) => {
      if (handlers.onProgressUpdate) {
        handlers.onProgressUpdate(JSON.parse(event.data))
      }
    })

    eventSource.addEventListener('error', (event) => {
      if (handlers.onTaskError) {
        handlers.onTaskError(JSON.parse(event.data))
      }
    })

    eventSource.addEventListener('completion', (event) => {
      if (handlers.onCompletion) {
        handlers.onCompletion(JSON.parse(event.data))
      }
    })

    return eventSource
  },

  // Download research report
  async downloadReport(taskId, format = 'markdown') {
    try {
      const response = await apiClient.get(`/research/${taskId}/download?format=${format}`, {
        responseType: 'blob'
      })

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `research-report-${taskId}.${format === 'markdown' ? 'md' : format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)

      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Share research report
  async shareReport(taskId, shareOptions) {
    try {
      const response = await apiClient.post(`/research/${taskId}/share`, shareOptions)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Get shared report by token
  async getSharedReport(shareToken) {
    try {
      const response = await apiClient.get(`/research/shared/${shareToken}`)
      return response
    } catch (error) {
      throw this.handleError(error)
    }
  },

  // Validate research request before submission
  validateResearchRequest(request) {
    const errors = []

    if (!request.title || request.title.trim().length === 0) {
      errors.push('Title is required')
    }

    if (request.title && request.title.length > 500) {
      errors.push('Title must not exceed 500 characters')
    }

    if (request.description && request.description.length > 2000) {
      errors.push('Description must not exceed 2000 characters')
    }

    if (request.deadlineMinutes && (request.deadlineMinutes < 5 || request.deadlineMinutes > 120)) {
      errors.push('Deadline must be between 5 and 120 minutes')
    }

    if (request.maxSources && (request.maxSources < 1 || request.maxSources > 100)) {
      errors.push('Maximum sources must be between 1 and 100')
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  },

  // Format research request for API
  formatResearchRequest(formData) {
    return {
      title: formData.title,
      description: formData.description,
      researchTopics: formData.researchTopics || [],
      preferredSources: formData.preferredSources || [],
      outputFormat: formData.outputFormat || 'MARKDOWN',
      toneStyle: formData.toneStyle || 'FORMAL',
      maxSources: formData.maxSources || 20,
      includeCitations: formData.includeCitations !== false,
      customInstructions: formData.customInstructions,
      deadlineMinutes: formData.deadlineMinutes || 30,
      additionalContext: formData.additionalContext || {}
    }
  },

  // Handle errors consistently
  handleError(error) {
    if (error.response) {
      // Server responded with error status
      return {
        message: error.response.data?.message || `Server error: ${error.response.status}`,
        status: error.response.status,
        data: error.response.data
      }
    } else if (error.request) {
      // Request was made but no response received
      return {
        message: 'Network error: No response from server',
        status: 'NETWORK_ERROR'
      }
    } else {
      // Something else happened
      return {
        message: error.message || 'Unknown error occurred',
        status: 'UNKNOWN_ERROR'
      }
    }
  },

  // Utility method to check if a task can be cancelled
  canCancelTask(task) {
    if (!task) return false
    const cancellableStatuses = ['PENDING', 'PLANNING', 'RESEARCHING', 'ANALYZING', 'WRITING']
    return cancellableStatuses.includes(task.status)
  },

  // Utility method to check if a task is completed
  isTaskCompleted(task) {
    return task && task.status === 'COMPLETED'
  },

  // Utility method to get task status display text
  getTaskStatusText(status) {
    const statusMap = {
      'PENDING': 'Pending',
      'PLANNING': 'Planning Research',
      'RESEARCHING': 'Gathering Information',
      'ANALYZING': 'Analyzing Data',
      'WRITING': 'Writing Report',
      'COMPLETED': 'Completed',
      'FAILED': 'Failed',
      'CANCELLED': 'Cancelled'
    }
    return statusMap[status] || status
  },

  // Utility method to get task status color
  getTaskStatusColor(status) {
    const colorMap = {
      'PENDING': 'info',
      'PLANNING': 'primary',
      'RESEARCHING': 'primary',
      'ANALYZING': 'warning',
      'WRITING': 'warning',
      'COMPLETED': 'success',
      'FAILED': 'danger',
      'CANCELLED': 'info'
    }
    return colorMap[status] || 'info'
  }
}

export default researchService