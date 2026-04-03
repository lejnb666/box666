<template>
  <div class="research-dashboard">
    <!-- Header Section -->
    <div class="dashboard-header">
      <el-row :gutter="20" class="header-row">
        <el-col :span="16">
          <h1 class="page-title">
            <el-icon><Reading /></el-icon>
            Research Dashboard
          </h1>
          <p class="page-subtitle">
            Create and manage AI-powered research tasks with multi-agent collaboration
          </p>
        </el-col>
        <el-col :span="8" class="header-actions">
          <el-button-group>
            <el-button type="primary" @click="showCreateDialog = true">
              <el-icon><Plus /></el-icon>
              New Research
            </el-button>
            <el-button @click="refreshData">
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
          </el-button-group>
        </el-col>
      </el-row>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon total">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number">{{ taskStats.total }}</div>
                <div class="stat-label">Total Tasks</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon active">
                <el-icon><Loading /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number">{{ taskStats.active }}</div>
                <div class="stat-label">Active Tasks</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon completed">
                <el-icon><Check /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number">{{ taskStats.completed }}</div>
                <div class="stat-label">Completed</div>
              </div>
            </div>
          </el-card>
        </el-col>

        <el-col :span="6">
          <el-card class="stat-card" shadow="hover">
            <div class="stat-content">
              <div class="stat-icon success-rate">
                <el-icon><TrendCharts /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-number">{{ taskStats.successRate }}%</div>
                <div class="stat-label">Success Rate</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- Main Content Area -->
    <el-row :gutter="20" class="main-content">
      <!-- Task List -->
      <el-col :span="16">
        <el-card class="task-section" shadow="never">
          <template #header>
            <div class="section-header">
              <h3>Research Tasks</h3>
              <div class="section-actions">
                <el-input
                  v-model="searchQuery"
                  placeholder="Search tasks..."
                  prefix-icon="Search"
                  clearable
                  class="search-input"
                />
                <el-select v-model="statusFilter" placeholder="Filter by status" clearable>
                  <el-option label="All Status" value="" />
                  <el-option label="Active" value="active" />
                  <el-option label="Completed" value="completed" />
                  <el-option label="Failed" value="failed" />
                </el-select>
              </div>
            </div>
          </template>

          <div class="task-list">
            <!-- Active Task (if any) -->
            <div v-if="currentTask" class="current-task-section">
              <h4 class="subsection-title">
                <el-icon><Aim /></el-icon>
                Current Research
              </h4>
              <task-card
                :task="currentTask"
                :is-active="true"
                :is-streaming="isStreaming"
                @view-details="viewTaskDetails"
                @cancel="cancelTask"
              />

              <!-- Workflow Visualization -->
              <el-card v-if="currentTask.agentStatuses" class="workflow-visualization" shadow="never">
                <template #header>
                  <div class="workflow-header">
                    <h5>Multi-Agent Workflow Status</h5>
                    <el-tag :type="getWorkflowStatusType(currentTask.status)" size="small">
                      {{ currentTask.status }}
                    </el-tag>
                  </div>
                </template>

                <div class="workflow-topology">
                  <div
                    v-for="(agent, agentName) in getWorkflowAgents()"
                    :key="agentName"
                    class="agent-node"
                    :class="[agentName, getAgentStatus(agentName)]"
                  >
                    <div class="agent-icon">
                      <el-icon>
                        <component :is="getAgentIcon(agentName)" />
                      </el-icon>
                    </div>
                    <div class="agent-label">{{ formatAgentName(agentName) }}</div>
                    <div class="agent-status">
                      <el-tag :type="getStatusType(getAgentStatus(agentName))" size="small">
                        {{ getAgentStatus(agentName) }}
                      </el-tag>
                    </div>

                    <!-- Connection arrows -->
                    <div
                      v-if="!isLastAgent(agentName)"
                      class="connection-arrow"
                      :class="{ 'active': isConnectionActive(agentName) }"
                    >
                      <el-icon><ArrowRight /></el-icon>
                    </div>
                  </div>
                </div>

                <!-- Agent Details -->
                <div v-if="currentTask.intermediateResults" class="agent-details">
                  <el-collapse accordion>
                    <el-collapse-item
                      v-for="(results, agentName) in getRelevantResults()"
                      :key="agentName"
                      :title="formatAgentName(agentName)"
                      :name="agentName"
                    >
                      <div class="agent-results">
                        <div v-if="results.summary" class="result-summary">
                          <strong>Summary:</strong> {{ results.summary }}
                        </div>
                        <div v-if="results.keyFindings" class="key-findings">
                          <strong>Key Findings:</strong>
                          <ul>
                            <li v-for="(finding, idx) in results.keyFindings" :key="idx">
                              {{ finding }}
                            </li>
                          </ul>
                        </div>
                        <div v-if="results.sources" class="sources-info">
                          <strong>Sources:</strong> {{ results.sources.length }} items
                        </div>
                        <div v-if="results.accuracyScore" class="accuracy-score">
                          <strong>Accuracy Score:</strong>
                          <el-progress
                            :percentage="results.accuracyScore * 100"
                            :status="getAccuracyStatus(results.accuracyScore)"
                          />
                        </div>
                      </div>
                    </el-collapse-item>
                  </el-collapse>
                </div>
              </el-card>
            </div>

            <!-- Task History -->
            <div class="task-history-section">
              <h4 class="subsection-title">
                <el-icon><Clock /></el-icon>
                Task History
                <span class="task-count">({{ filteredTasks.length }})</span>
              </h4>

              <div v-if="filteredTasks.length === 0" class="empty-state">
                <el-empty
                  :image-size="200"
                  description="No research tasks found. Create your first task to get started."
                >
                  <template #image>
                    <el-icon :size="64" class="empty-icon"><Document /></el-icon>
                  </template>
                  <el-button type="primary" @click="showCreateDialog = true">
                    Create Research Task
                  </el-button>
                </el-empty>
              </div>

              <div v-else class="task-items">
                <task-card
                  v-for="task in filteredTasks"
                  :key="task.id"
                  :task="task"
                  :is-active="task.id === currentTask?.id"
                  @view-details="viewTaskDetails"
                  @cancel="cancelTask"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- Sidebar -->
      <el-col :span="8">
        <div class="sidebar">
          <!-- Quick Actions -->
          <el-card class="sidebar-section" shadow="never">
            <template #header>
              <h4>Quick Actions</h4>
            </template>
            <div class="quick-actions">
              <el-button type="primary" @click="showCreateDialog = true" class="action-button">
                <el-icon><Plus /></el-icon>
                New Research Task
              </el-button>
              <el-button @click="showTemplates = true" class="action-button">
                <el-icon><Document /></el-icon>
                Use Template
              </el-button>
              <el-button @click="clearHistory" class="action-button" :disabled="taskHistory.length === 0">
                <el-icon><Delete /></el-icon>
                Clear History
              </el-button>
            </div>
          </el-card>

          <!-- Recent Activity -->
          <el-card class="sidebar-section" shadow="never">
            <template #header>
              <h4>Recent Activity</h4>
            </template>
            <div class="activity-feed">
              <div v-if="recentActivity.length === 0" class="empty-activity">
                No recent activity
              </div>
              <div v-else class="activity-items">
                <div
                  v-for="activity in recentActivity"
                  :key="activity.id"
                  class="activity-item"
                >
                  <div class="activity-icon" :class="activity.type">
                    <el-icon>
                      <component :is="getActivityIcon(activity.type)" />
                    </el-icon>
                  </div>
                  <div class="activity-content">
                    <div class="activity-text">{{ activity.text }}</div>
                    <div class="activity-time">{{ formatTime(activity.timestamp) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- Tips -->
          <el-card class="sidebar-section" shadow="never">
            <template #header>
              <h4>Research Tips</h4>
            </template>
            <div class="tips-section">
              <div class="tip-item">
                <el-icon><Lightbulb /></el-icon>
                <span>Be specific in your research objectives for better results</span>
              </div>
              <div class="tip-item">
                <el-icon><Lightbulb /></el-icon>
                <span>Use multiple research topics to cover different aspects</span>
              </div>
              <div class="tip-item">
                <el-icon><Lightbulb /></el-icon>
                <span>Set appropriate deadlines based on research complexity</span>
              </div>
            </div>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- Create Research Dialog -->
    <create-research-dialog
      v-model="showCreateDialog"
      @created="onTaskCreated"
    />

    <!-- Task Details Dialog -->
    <task-details-dialog
      v-model="showDetailsDialog"
      :task-id="selectedTaskId"
      @close="selectedTaskId = null"
    />

    <!-- Templates Dialog -->
    <research-templates-dialog
      v-model="showTemplates"
      @select-template="onTemplateSelected"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useResearchStore } from '@/stores/research'
import { useNotificationStore } from '@/stores/notification'
import { formatTime } from '@/utils/dateUtils'
import TaskCard from '@/components/research/TaskCard.vue'
import CreateResearchDialog from '@/components/research/CreateResearchDialog.vue'
import TaskDetailsDialog from '@/components/research/TaskDetailsDialog.vue'
import ResearchTemplatesDialog from '@/components/research/ResearchTemplatesDialog.vue'

// Store
const researchStore = useResearchStore()
const notificationStore = useNotificationStore()

// Reactive state
const showCreateDialog = ref(false)
const showDetailsDialog = ref(false)
const showTemplates = ref(false)
const selectedTaskId = ref(null)
const searchQuery = ref('')
const statusFilter = ref('')

// Computed properties
const taskStats = computed(() => researchStore.taskStats)
const taskHistory = computed(() => researchStore.taskHistory)
const currentTask = computed(() => researchStore.currentTask)
const isStreaming = computed(() => researchStore.isStreaming)

const filteredTasks = computed(() => {
  let tasks = taskHistory.value.filter(task => task.id !== currentTask.value?.id)

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    tasks = tasks.filter(task =>
      task.title.toLowerCase().includes(query) ||
      (task.description && task.description.toLowerCase().includes(query))
    )
  }

  // Filter by status
  if (statusFilter.value) {
    switch (statusFilter.value) {
      case 'active':
        tasks = tasks.filter(task => ['PENDING', 'PLANNING', 'RESEARCHING', 'ANALYZING', 'WRITING'].includes(task.status))
        break
      case 'completed':
        tasks = tasks.filter(task => task.status === 'COMPLETED')
        break
      case 'failed':
        tasks = tasks.filter(task => task.status === 'FAILED')
        break
    }
  }

  // Sort by creation date (newest first)
  return tasks.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
})

const recentActivity = computed(() => {
  const activities = []

  // Add recent task activities
  taskHistory.value.slice(0, 5).forEach(task => {
    activities.push({
      id: `task-${task.id}`,
      type: getTaskActivityType(task.status),
      text: getTaskActivityText(task),
      timestamp: task.updatedAt || task.createdAt
    })
  })

  return activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 5)
})

// Methods
const refreshData = async () => {
  try {
    await researchStore.fetchTaskHistory()
    notificationStore.success('Data refreshed successfully')
  } catch (error) {
    console.error('Failed to refresh data:', error)
  }
}

const viewTaskDetails = (taskId) => {
  selectedTaskId.value = taskId
  showDetailsDialog.value = true
}

const cancelTask = async (taskId) => {
  try {
    await researchStore.cancelTask(taskId)
  } catch (error) {
    console.error('Failed to cancel task:', error)
  }
}

const clearHistory = async () => {
  try {
    await researchStore.clearTaskHistory()
  } catch (error) {
    console.error('Failed to clear history:', error)
  }
}

const onTaskCreated = (task) => {
  showCreateDialog.value = false
  // Task is automatically added to store via SSE
}

const onTemplateSelected = (template) => {
  showTemplates.value = false
  // Pre-fill create dialog with template data
  showCreateDialog.value = true
}

const getTaskActivityType = (status) => {
  const typeMap = {
    'COMPLETED': 'success',
    'FAILED': 'error',
    'CANCELLED': 'warning',
    'PLANNING': 'info',
    'RESEARCHING': 'info',
    'ANALYZING': 'info',
    'WRITING': 'info'
  }
  return typeMap[status] || 'info'
}

const getTaskActivityText = (task) => {
  const statusText = {
    'COMPLETED': 'completed successfully',
    'FAILED': 'failed',
    'CANCELLED': 'was cancelled',
    'PLANNING': 'started planning',
    'RESEARCHING': 'started researching',
    'ANALYZING': 'started analyzing',
    'WRITING': 'started writing'
  }
  return `${task.title} ${statusText[task.status] || task.status.toLowerCase()}`
}

const getActivityIcon = (type) => {
  const iconMap = {
    'success': 'Check',
    'error': 'Close',
    'warning': 'Warning',
    'info': 'InfoFilled'
  }
  return iconMap[type] || 'InfoFilled'
}

const getWorkflowStatusType = (status) => {
  const typeMap = {
    'RUNNING': 'primary',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'warning',
    'CREATED': 'info'
  }
  return typeMap[status] || 'info'
}

const getWorkflowAgents = () => {
  return {
    'planning': { name: 'Planning', order: 1 },
    'research': { name: 'Research', order: 2 },
    'analysis': { name: 'Analysis', order: 3 },
    'fact_check': { name: 'Fact Check', order: 4 },
    'writing': { name: 'Writing', order: 5 }
  }
}

const getAgentStatus = (agentName) => {
  return currentTask.value?.agentStatuses?.[agentName] || 'waiting'
}

const getAgentIcon = (agentName) => {
  const iconMap = {
    'planning': 'Document',
    'research': 'Search',
    'analysis': 'DataAnalysis',
    'fact_check': 'CircleCheck',
    'writing': 'Edit'
  }
  return iconMap[agentName] || 'InfoFilled'
}

const formatAgentName = (agentName) => {
  return agentName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const isLastAgent = (agentName) => {
  const agents = getWorkflowAgents()
  const maxOrder = Math.max(...Object.values(agents).map(a => a.order))
  return agents[agentName]?.order === maxOrder
}

const isConnectionActive = (agentName) => {
  const agents = getWorkflowAgents()
  const currentAgentOrder = agents[agentName]?.order || 0
  const currentAgent = currentTask.value?.currentAgent
  const currentOrder = agents[currentAgent]?.order || 0

  return currentAgentOrder < currentOrder
}

const getStatusType = (status) => {
  const typeMap = {
    'completed': 'success',
    'executing': 'primary',
    'failed': 'danger',
    'waiting': 'info',
    'idle': 'info'
  }
  return typeMap[status] || 'info'
}

const getRelevantResults = () => {
  const results = currentTask.value?.intermediateResults || {}
  const relevantKeys = ['planning', 'research', 'analysis', 'fact_check', 'writing']
  const filtered = {}

  relevantKeys.forEach(key => {
    if (results[key]) {
      filtered[key] = {
        summary: results[key].summary || results[key].executive_summary || '',
        keyFindings: results[key].key_findings || results[key].keyFindings || [],
        sources: results[key].sources || [],
        accuracyScore: results[key].accuracy_score || 0
      }
    }
  })

  return filtered
}

const getAccuracyStatus = (score) => {
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'exception'
}

// Lifecycle
onMounted(async () => {
  await refreshData()
})

onUnmounted(() => {
  // Cleanup any active streams
  researchStore.stopStreaming()
})
</script>

<style lang="scss" scoped>
.research-dashboard {
  padding: 20px;
  min-height: 100vh;
  background-color: var(--el-bg-color-page);

  .dashboard-header {
    margin-bottom: 24px;

    .header-row {
      align-items: center;
    }

    .page-title {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 8px 0;
      font-size: 28px;
      font-weight: 600;
      color: var(--el-text-color-primary);

      .el-icon {
        font-size: 32px;
        color: var(--el-color-primary);
      }
    }

    .page-subtitle {
      margin: 0;
      color: var(--el-text-color-secondary);
      font-size: 16px;
    }

    .header-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }

  .stats-section {
    margin-bottom: 24px;

    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: 16px;
      }

      .stat-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;

        &.total {
          background-color: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
        }

        &.active {
          background-color: var(--el-color-warning-light-9);
          color: var(--el-color-warning);
        }

        &.completed {
          background-color: var(--el-color-success-light-9);
          color: var(--el-color-success);
        }

        &.success-rate {
          background-color: var(--el-color-info-light-9);
          color: var(--el-color-info);
        }
      }

      .stat-info {
        flex: 1;

        .stat-number {
          font-size: 24px;
          font-weight: 600;
          color: var(--el-text-color-primary);
          line-height: 1.2;
        }

        .stat-label {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          margin-top: 4px;
        }
      }
    }
  }

  .main-content {
    .task-section {
      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
          margin: 0;
          font-size: 20px;
          font-weight: 600;
        }

        .section-actions {
          display: flex;
          gap: 12px;
          align-items: center;

          .search-input {
            width: 240px;
          }
        }
      }

      .task-list {
        .current-task-section {
          margin-bottom: 32px;

          .subsection-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 16px 0;
            font-size: 18px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }
        }

        .task-history-section {
          .subsection-title {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 0 0 16px 0;
            font-size: 18px;
            font-weight: 600;
            color: var(--el-text-color-primary);

            .task-count {
              font-size: 14px;
              color: var(--el-text-color-secondary);
              font-weight: 400;
            }
          }

          .empty-state {
            padding: 40px 0;
            text-align: center;

            .empty-icon {
              color: var(--el-text-color-disabled);
            }
          }

          .task-items {
            display: flex;
            flex-direction: column;
            gap: 16px;
          }
        }
      }
    }

    .sidebar {
      display: flex;
      flex-direction: column;
      gap: 20px;

      .sidebar-section {
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }

        .quick-actions {
          display: flex;
          flex-direction: column;
          gap: 12px;

          .action-button {
            justify-content: flex-start;
            width: 100%;
          }
        }

        .activity-feed {
          .empty-activity {
            text-align: center;
            color: var(--el-text-color-disabled);
            padding: 20px 0;
          }

          .activity-items {
            .activity-item {
              display: flex;
              gap: 12px;
              padding: 12px 0;
              border-bottom: 1px solid var(--el-border-color-lighter);

              &:last-child {
                border-bottom: none;
              }

              .activity-icon {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;

                &.success {
                  background-color: var(--el-color-success-light-9);
                  color: var(--el-color-success);
                }

                &.error {
                  background-color: var(--el-color-danger-light-9);
                  color: var(--el-color-danger);
                }

                &.warning {
                  background-color: var(--el-color-warning-light-9);
                  color: var(--el-color-warning);
                }

                &.info {
                  background-color: var(--el-color-info-light-9);
                  color: var(--el-color-info);
                }
              }

              .activity-content {
                flex: 1;

                .activity-text {
                  font-size: 14px;
                  color: var(--el-text-color-primary);
                  margin-bottom: 4px;
                }

                .activity-time {
                  font-size: 12px;
                  color: var(--el-text-color-disabled);
                }
              }
            }
          }
        }

        .tips-section {
          .tip-item {
            display: flex;
            gap: 8px;
            align-items: flex-start;
            padding: 8px 0;
            font-size: 14px;
            color: var(--el-text-color-regular);
            line-height: 1.4;

            .el-icon {
              color: var(--el-color-primary);
              margin-top: 2px;
            }
          }
        }
      }
    }
  }
}

// Responsive design
@media (max-width: 1200px) {
  .research-dashboard {
    .stats-section {
      .el-col {
        margin-bottom: 16px;
      }
    }

    .main-content {
      .el-col {
        width: 100%;
      }
    }
  }
}

@media (max-width: 768px) {
  .research-dashboard {
    padding: 16px;

    .dashboard-header {
      .page-title {
        font-size: 24px;
      }

      .header-actions {
        justify-content: flex-start;
        margin-top: 16px;
      }
    }

    .stats-section {
      .el-col {
        width: 50%;
      }
    }
  }
}

.workflow-visualization {
  margin-top: 20px;
  border: 1px solid var(--el-border-color-lighter);

  .workflow-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    h5 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .workflow-topology {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 0;
    overflow-x: auto;

    .agent-node {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-width: 120px;
      position: relative;

      .agent-icon {
        width: 60px;
        height: 60px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        margin-bottom: 8px;
        transition: all 0.3s ease;

        .el-icon {
          font-size: 24px;
        }
      }

      .agent-label {
        font-size: 14px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        margin-bottom: 4px;
        text-align: center;
      }

      .agent-status {
        .el-tag {
          font-size: 12px;
        }
      }

      // Status-based styling
      &.completed {
        .agent-icon {
          background-color: var(--el-color-success-light-9);
          color: var(--el-color-success);
          border: 2px solid var(--el-color-success);
        }
      }

      &.executing {
        .agent-icon {
          background-color: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
          border: 2px solid var(--el-color-primary);
          animation: pulse 2s infinite;
        }
      }

      &.failed {
        .agent-icon {
          background-color: var(--el-color-danger-light-9);
          color: var(--el-color-danger);
          border: 2px solid var(--el-color-danger);
        }
      }

      &.waiting {
        .agent-icon {
          background-color: var(--el-color-info-light-9);
          color: var(--el-color-info);
          border: 2px solid var(--el-border-color);
        }
      }

      .connection-arrow {
        position: absolute;
        right: -40px;
        top: 30px;
        color: var(--el-border-color);
        font-size: 20px;

        &.active {
          color: var(--el-color-primary);
        }
      }
    }
  }

  .agent-details {
    margin-top: 20px;
    border-top: 1px solid var(--el-border-color-lighter);
    padding-top: 20px;

    .agent-results {
      .result-summary {
        margin-bottom: 12px;
        font-size: 14px;
        color: var(--el-text-color-regular);
      }

      .key-findings {
        margin-bottom: 12px;

        ul {
          margin: 8px 0 0 16px;
          padding: 0;

          li {
            font-size: 14px;
            color: var(--el-text-color-regular);
            margin-bottom: 4px;
          }
        }
      }

      .sources-info {
        margin-bottom: 12px;
        font-size: 14px;
        color: var(--el-text-color-regular);
      }

      .accuracy-score {
        .el-progress {
          margin-top: 4px;
        }
      }
    }
  }
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(var(--el-color-primary-rgb), 0.7);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(var(--el-color-primary-rgb), 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(var(--el-color-primary-rgb), 0);
  }
}
</style>