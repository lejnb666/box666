<template>
  <el-dialog
    v-model="visible"
    title="Research Templates"
    width="600px"
    @close="handleClose"
  >
    <div class="templates-grid">
      <div 
        v-for="template in templates" 
        :key="template.id"
        class="template-card"
        @click="selectTemplate(template)"
      >
        <div class="template-header">
          <el-icon :size="24" :color="template.iconColor">
            <component :is="template.icon" />
          </el-icon>
          <h4>{{ template.title }}</h4>
        </div>
        <p class="template-description">{{ template.description }}</p>
        <div class="template-meta">
          <el-tag size="small" :type="template.complexity === 'high' ? 'danger' : 'info'">
            {{ template.complexity }} complexity
          </el-tag>
          <span class="template-duration">{{ template.estimatedDuration }} min</span>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">Cancel</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'select-template'])

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const templates = [
  {
    id: 'market-analysis',
    title: 'Market Analysis',
    description: 'Comprehensive analysis of market trends, competitors, and opportunities',
    icon: 'TrendCharts',
    iconColor: '#409EFF',
    complexity: 'high',
    estimatedDuration: 45,
    defaultParams: {
      outputFormat: 'report',
      depth: 'comprehensive',
      sources: ['academic', 'reports', 'news']
    }
  },
  {
    id: 'technical-overview',
    title: 'Technical Overview',
    description: 'Technical explanation and implementation details for technology topics',
    icon: 'Cpu',
    iconColor: '#67C23A',
    complexity: 'medium',
    estimatedDuration: 30,
    defaultParams: {
      outputFormat: 'markdown',
      depth: 'standard',
      sources: ['academic', 'web']
    }
  },
  {
    id: 'literature-review',
    title: 'Literature Review',
    description: 'Academic literature review with citations and critical analysis',
    icon: 'Document',
    iconColor: '#E6A23C',
    complexity: 'high',
    estimatedDuration: 60,
    defaultParams: {
      outputFormat: 'markdown',
      depth: 'comprehensive',
      sources: ['academic']
    }
  },
  {
    id: 'quick-summary',
    title: 'Quick Summary',
    description: 'Brief overview and key points for general topics',
    icon: 'Memo',
    iconColor: '#909399',
    complexity: 'low',
    estimatedDuration: 15,
    defaultParams: {
      outputFormat: 'text',
      depth: 'quick',
      sources: ['web', 'news']
    }
  },
  {
    id: 'competitor-analysis',
    title: 'Competitor Analysis',
    description: 'Detailed analysis of competitors, products, and market positioning',
    icon: 'DataAnalysis',
    iconColor: '#F56C6C',
    complexity: 'high',
    estimatedDuration: 50,
    defaultParams: {
      outputFormat: 'report',
      depth: 'comprehensive',
      sources: ['web', 'news', 'reports']
    }
  },
  {
    id: 'industry-report',
    title: 'Industry Report',
    description: 'Comprehensive industry analysis with trends and forecasts',
    icon: 'PieChart',
    iconColor: '#67C23A',
    complexity: 'high',
    estimatedDuration: 55,
    defaultParams: {
      outputFormat: 'report',
      depth: 'comprehensive',
      sources: ['academic', 'reports', 'news']
    }
  }
]

const selectTemplate = (template) => {
  emit('select-template', template)
  handleClose()
}

const handleClose = () => {
  visible.value = false
}
</script>

<style scoped>
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.template-card {
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  background-color: var(--el-bg-color);
}

.template-card:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.template-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.template-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.template-description {
  margin: 0 0 16px 0;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 1.4;
  min-height: 40px;
}

.template-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-duration {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* Responsive design */
@media (max-width: 768px) {
  .templates-grid {
    grid-template-columns: 1fr;
  }
  
  :deep(.el-dialog) {
    width: 95% !important;
    margin: 5vh auto !important;
  }
}
</style>
