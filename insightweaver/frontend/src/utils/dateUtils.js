/**
 * Date utility functions for InsightWeaver frontend
 */

/**
 * Format a date string or timestamp into a readable format
 * @param {string|number} dateInput - Date string or timestamp
 * @param {string} format - Format style: 'short', 'medium', 'long'
 * @returns {string} Formatted date string
 */
export function formatDate(dateInput, format = 'medium') {
  if (!dateInput) return 'N/A'
  
  const date = new Date(dateInput)
  
  if (isNaN(date.getTime())) {
    return 'Invalid Date'
  }
  
  const options = {
    short: { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    },
    medium: { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    },
    long: {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }
  }
  
  try {
    return date.toLocaleDateString('en-US', options[format] || options.medium)
  } catch (error) {
    console.error('Error formatting date:', error)
    return date.toISOString().split('T')[0] // Fallback to YYYY-MM-DD
  }
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {string|number} dateInput - Date string or timestamp
 * @returns {string} Relative time string
 */
export function formatRelativeTime(dateInput) {
  if (!dateInput) return 'N/A'
  
  const date = new Date(dateInput)
  const now = new Date()
  const diffInSeconds = Math.floor((now - date) / 1000)
  
  if (isNaN(diffInSeconds)) {
    return 'Invalid Date'
  }
  
  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60
  }
  
  for (const [unit, seconds] of Object.entries(intervals)) {
    const interval = Math.floor(diffInSeconds / seconds)
    
    if (interval >= 1) {
      return interval === 1 ? `1 ${unit} ago` : `${interval} ${unit}s ago`
    }
  }
  
  return 'Just now'
}

/**
 * Format time duration
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration string
 */
export function formatDuration(minutes) {
  if (!minutes || minutes <= 0) return 'N/A'
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  
  if (hours > 0) {
    return remainingMinutes > 0 
      ? `${hours}h ${remainingMinutes}m`
      : `${hours}h`
  }
  
  return `${remainingMinutes}m`
}

/**
 * Get time remaining until deadline
 * @param {string|number} deadline - Deadline date string or timestamp
 * @returns {string} Time remaining string
 */
export function getTimeRemaining(deadline) {
  if (!deadline) return 'No deadline'
  
  const deadlineDate = new Date(deadline)
  const now = new Date()
  const diffInMs = deadlineDate - now
  
  if (isNaN(diffInMs)) {
    return 'Invalid deadline'
  }
  
  if (diffInMs <= 0) {
    return 'Deadline passed'
  }
  
  const diffInMinutes = Math.floor(diffInMs / (1000 * 60))
  
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes !== 1 ? 's' : ''} remaining`
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours !== 1 ? 's' : ''} remaining`
  }
  
  const diffInDays = Math.floor(diffInHours / 24)
  return `${diffInDays} day${diffInDays !== 1 ? 's' : ''} remaining`
}

/**
 * Parse and validate date input
 * @param {string|number} dateInput - Date string or timestamp
 * @returns {Date|null} Parsed Date object or null if invalid
 */
export function parseDate(dateInput) {
  if (!dateInput) return null
  
  const date = new Date(dateInput)
  return isNaN(date.getTime()) ? null : date
}

/**
 * Check if a date is today
 * @param {string|number} dateInput - Date string or timestamp
 * @returns {boolean} True if the date is today
 */
export function isToday(dateInput) {
  if (!dateInput) return false
  
  const date = new Date(dateInput)
  const today = new Date()
  
  return date.getDate() === today.getDate() &&
         date.getMonth() === today.getMonth() &&
         date.getFullYear() === today.getFullYear()
}

/**
 * Get start and end of day for a given date
 * @param {string|number} dateInput - Date string or timestamp
 * @returns {Object} Object with start and end of day timestamps
 */
export function getDayBounds(dateInput) {
  const date = parseDate(dateInput) || new Date()
  
  const startOfDay = new Date(date)
  startOfDay.setHours(0, 0, 0, 0)
  
  const endOfDay = new Date(date)
  endOfDay.setHours(23, 59, 59, 999)
  
  return {
    start: startOfDay.getTime(),
    end: endOfDay.getTime()
  }
}

// Default export for convenience
export default {
  formatDate,
  formatRelativeTime,
  formatDuration,
  getTimeRemaining,
  parseDate,
  isToday,
  getDayBounds
}
