<template>
  <el-dialog
    v-model="visible"
    title="Task Details"
    width="700px"
    @close="handleClose"
  >
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="task" class="task-details">
      <div class="task-header">
        <h3>{{ task.title }}</h3>
        <el-tag :type="getStatusType(task.status)">
          {{ task.status }}
        </el-tag>
      </div>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="Task ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="Created">{{ formatDate(task.createdAt) }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ task.status }}</el-descriptions-item>
        <el-descriptions-item label="Progress">
          <el-progress :percentage="task.progress || 0" />
        </el-descriptions-item>
      </el-descriptions>

      <div v-if="task.description" class="task-section">
        <h4>Description</h4>
        <p>{{ task.description }}</p>
      </div>

      <div v-if="finalResult" class="task-section">
        <h4>Final Result</h4>
        <div class="result-content">
          <div class="interactive-report" v-html="renderInteractiveReport(finalResult)"></div>
        </div>
      </div>

      <!-- Source Details Dialog -->
      <el-dialog
        v-model="showSourceDialog"
        title="Source Details"
        width="600px"
      >
        <div v-if="selectedSource" class="source-details">
          <h4>{{ selectedSource.title }}</h4>
          <el-tag type="info" size="small" class="source-type">
            {{ selectedSource.source_type || 'Source' }}
          </el-tag>

          <div class="source-url" v-if="selectedSource.url">
            <strong>URL:</strong>
            <a :href="selectedSource.url" target="_blank" rel="noopener">
              {{ selectedSource.url }}
            </a>
          </div>

          <div class="source-content">
            <strong>Content:</strong>
            <div class="source-snippet">
              {{ selectedSource.snippet || selectedSource.content || 'No content available' }}
            </div>
          </div>

          <div class="source-metadata" v-if="selectedSource.metadata">
            <strong>Metadata:</strong>
            <pre>{{ JSON.stringify(selectedSource.metadata, null, 2) }}</pre>
          </div>
        </div>
      </el-dialog>
    </div>

    <div v-else class="error-state">
      <el-empty description="Task not found" />
    </div>

    <template #footer>
      <el-button @click="handleClose">Close</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  taskId: String
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const loading = ref(false)
const task = ref(null)
const finalResult = ref(null)
const showSourceDialog = ref(false)
const selectedSource = ref(null)
const sourceMap = ref({})

const getStatusType = (status) => {
  const typeMap = {
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'primary'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleString()
}

const handleClose = () => {
  visible.value = false
  emit('close')
}

const renderInteractiveReport = (content) => {
  if (!content) return ''

  // Convert markdown-like content to HTML with clickable citations
  let html = content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')

  // Find and replace citation markers [1], [2], etc.
  const citationRegex = /\[(\d+)\]/g
  html = html.replace(citationRegex, (match, citationNum) => {
    const sourceId = `source-${citationNum}`
    return `<span class="citation-marker" data-source-id="${citationNum}" @click="showSourceDetails('${citationNum}')">[${citationNum}]</span>`
  })

  return html
}

const showSourceDetails = (sourceId) => {
  // Find source by ID in the task's research results
  if (task.value?.intermediateResults?.research?.sources) {
    const sources = task.value.intermediateResults.research.sources
    const source = sources.find(s => s.id === sourceId || s.id === `source-${sourceId}`)

    if (source) {
      selectedSource.value = source
      showSourceDialog.value = true
    }
  }
}

const getSourceTypeColor = (type) => {
  const colorMap = {
    'web': 'primary',
    'academic': 'success',
    'news': 'warning'
  }
  return colorMap[type] || 'info'
}
</script>

<style scoped>
.task-details {
  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .task-section {
    margin: 20px 0;
  }

  .result-content {
    max-height: 300px;
    overflow-y: auto;
  }

  .result-content pre {
    margin: 0;
    padding: 12px;
    background-color: var(--el-fill-color-light);
    border-radius: 4px;
    font-size: 12px;
    white-space: pre-wrap;
  }

  .interactive-report {
    margin: 0;
    padding: 12px;
    background-color: var(--el-fill-color-light);
    border-radius: 4px;
    font-size: 14px;
    line-height: 1.6;

    .citation-marker {
      color: var(--el-color-primary);
      cursor: pointer;
      text-decoration: underline;
      font-weight: 600;
      padding: 0 2px;
      border-radius: 2px;
      transition: background-color 0.2s;

      &:hover {
        background-color: var(--el-color-primary-light-9);
      }
    }
  }
}

.source-details {
  h4 {
    margin: 0 0 12px 0;
    color: var(--el-text-color-primary);
  }

  .source-type {
    margin-bottom: 16px;
  }

  .source-url {
    margin-bottom: 16px;

    a {
      color: var(--el-color-primary);
      text-decoration: none;
      word-break: break-all;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  .source-content {
    margin-bottom: 16px;

    .source-snippet {
      margin-top: 8px;
      padding: 12px;
      background-color: var(--el-fill-color-lighter);
      border-radius: 4px;
      font-size: 14px;
      line-height: 1.5;
      max-height: 200px;
      overflow-y: auto;
    }
  }

  .source-metadata {
    pre {
      margin-top: 8px;
      padding: 12px;
      background-color: var(--el-fill-color-lighter);
      border-radius: 4px;
      font-size: 12px;
      max-height: 150px;
      overflow-y: auto;
    }
  }
}
</style>
