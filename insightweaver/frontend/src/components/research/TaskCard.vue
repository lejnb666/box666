<template>
  <el-card class="task-card" :class="{ 'is-active': isActive, 'is-streaming': isStreaming }">
    <div class="task-header">
      <div class="task-title">
        <h4>{{ task.title }}</h4>
        <el-tag :type="getStatusType(task.status)" size="small">
          {{ task.status }}
        </el-tag>
      </div>
      <div class="task-actions">
        <el-button-group>
          <el-button 
            size="small" 
            @click="$emit('view-details', task.id)"
            :disabled="isActive && isStreaming"
          >
            <el-icon><View /></el-icon>
            Details
          </el-button>
          <el-button 
            v-if="canCancel"
            size="small" 
            type="danger"
            @click="$emit('cancel', task.id)"
            :disabled="isStreaming"
          >
            <el-icon><Close /></el-icon>
            Cancel
          </el-button>
        </el-button-group>
      </div>
    </div>

    <div class="task-content">
      <p class="task-description">{{ task.description }}</p>
      
      <div class="task-meta">
        <div class="meta-item">
          <el-icon><Clock /></el-icon>
          <span>{{ formatDate(task.createdAt) }}</span>
        </div>
        <div class="meta-item">
          <el-icon><Document /></el-icon>
          <span>{{ task.outputFormat || 'markdown' }}</span>
        </div>
        <div v-if="task.estimatedDuration" class="meta-item">
          <el-icon><Timer /></el-icon>
          <span>{{ task.estimatedDuration }} min</span>
        </div>
      </div>

      <!-- Progress indicator for active tasks -->
      <div v-if="isActive" class="task-progress">
        <div class="progress-header">
          <span class="progress-label">Progress</span>
          <span class="progress-percentage">{{ Math.round(task.progress || 0) }}%</span>
        </div>
        <el-progress 
          :percentage="task.progress || 0" 
          :status="getProgressStatus(task.status)"
          :stroke-width="8"
        />
        <div v-if="task.currentAgent" class="current-agent">
          <el-icon><User /></el-icon>
          <span>Current: {{ task.currentAgent }} - {{ task.currentAction }}</span>
        </div>
      </div>

      <!-- Streaming indicator -->
      <div v-if="isStreaming" class="streaming-indicator">
        <el-icon class="blinking"><Loading /></el-icon>
        <span>Real-time updates active</span>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  },
  isActive: {
    type: Boolean,
    default: false
  },
  isStreaming: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['view-details', 'cancel'])

const canCancel = computed(() => {
  return props.isActive && 
         !props.isStreaming && 
         ['PENDING', 'PLANNING', 'RESEARCHING', 'ANALYZING', 'WRITING'].includes(props.task.status)
})

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'info',
    'PLANNING': 'primary',
    'RESEARCHING': 'primary',
    'ANALYZING': 'warning',
    'WRITING': 'success',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

const getProgressStatus = (status) => {
  const statusMap = {
    'COMPLETED': 'success',
    'FAILED': 'exception',
    'CANCELLED': 'info'
  }
  return statusMap[status] || 'active'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}
</script>

<style scoped>
.task-card {
  margin-bottom: 16px;
  transition: all 0.3s ease;
  border: 1px solid var(--el-border-color-lighter);
}

.task-card.is-active {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.task-card.is-streaming {
  border-color: var(--el-color-success);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.task-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.task-title h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.task-actions {
  margin-left: 16px;
}

.task-content {
  .task-description {
    margin: 0 0 12px 0;
    color: var(--el-text-color-regular);
    font-size: 14px;
    line-height: 1.4;
  }

  .task-meta {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }

  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .task-progress {
    margin-top: 16px;
    padding: 12px;
    background-color: var(--el-fill-color-light);
    border-radius: 6px;
  }

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .progress-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    font-weight: 500;
  }

  .progress-percentage {
    font-size: 12px;
    color: var(--el-text-color-primary);
    font-weight: 600;
  }

  .current-agent {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  .streaming-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding: 8px 12px;
    background-color: var(--el-color-success-light-9);
    border-radius: 4px;
    font-size: 12px;
    color: var(--el-color-success);
  }

  .blinking {
    animation: blink 1s infinite;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

/* Responsive design */
@media (max-width: 768px) {
  .task-header {
    flex-direction: column;
    gap: 12px;
  }

  .task-actions {
    margin-left: 0;
    align-self: flex-end;
  }

  .task-meta {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
