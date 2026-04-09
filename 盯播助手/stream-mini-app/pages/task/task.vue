<template>
  <view class="task-page">
    <!-- 顶部统计 -->
    <view class="stats-header card">
      <view class="stat-item">
        <text class="stat-number">{{ totalTasks }}</text>
        <text class="stat-label">总任务</text>
      </view>
      <view class="stat-item">
        <text class="stat-number">{{ activeTasks }}</text>
        <text class="stat-label">运行中</text>
      </view>
      <view class="stat-item">
        <text class="stat-number">{{ pausedTasks }}</text>
        <text class="stat-label">已暂停</text>
      </view>
    </view>

    <!-- 搜索和筛选 -->
    <view class="filter-section card">
      <view class="search-box">
        <u-search
          v-model="searchKeyword"
          placeholder="搜索主播或平台"
          :show-action="false"
          @search="loadTasks"
          @clear="loadTasks"
        />
      </view>
      <view class="filter-options">
        <u-tabs
          :list="filterTabs"
          :current="currentFilter"
          @change="onFilterChange"
          :active-color="'#007AFF'"
        />
      </view>
    </view>

    <!-- 任务列表 -->
    <view class="tasks-section">
      <view v-if="tasks.length > 0" class="tasks-list">
        <view
          v-for="task in tasks"
          :key="task.id"
          class="task-card card"
          @click="showTaskDetail(task)"
        >
          <!-- 任务头部 -->
          <view class="task-header">
            <view class="task-info">
              <text class="streamer-name">{{ task.streamerName }}</text>
              <text class="platform-tag">{{ getPlatformLabel(task.platform) }}</text>
            </view>
            <view class="task-status">
              <text
                class="status-badge"
                :class="getStatusClass(task.status)"
              >
                {{ getStatusText(task.status) }}
              </text>
            </view>
          </view>

          <!-- 任务类型 -->
          <view class="task-type">
            <text class="type-icon">{{ getTaskTypeIcon(task.taskType) }}</text>
            <text class="type-text">{{ getTaskTypeLabel(task.taskType) }}</text>
            <text v-if="task.aiAnalysis" class="ai-badge">AI分析</text>
          </view>

          <!-- 任务详情 -->
          <view class="task-details">
            <view class="detail-item">
              <text class="detail-label">房间号:</text>
              <text class="detail-value">{{ task.roomId }}</text>
            </view>
            <view class="detail-item">
              <text class="detail-label">触发次数:</text>
              <text class="detail-value">{{ task.triggerCount || 0 }}</text>
            </view>
            <view v-if="task.lastTriggeredAt" class="detail-item">
              <text class="detail-label">最后触发:</text>
              <text class="detail-value">{{ formatTime(task.lastTriggeredAt) }}</text>
            </view>
          </view>

          <!-- 任务操作 -->
          <view class="task-actions">
            <button
              class="action-btn toggle-btn"
              :class="task.status === 1 ? 'pause-btn' : 'start-btn'"
              @click.stop="toggleTaskStatus(task)"
            >
              <text class="btn-text">
                {{ task.status === 1 ? '暂停' : '启动' }}
              </text>
            </button>
            <button
              class="action-btn edit-btn"
              @click.stop="editTask(task)"
            >
              <text class="btn-text">编辑</text>
            </button>
            <button
              class="action-btn delete-btn"
              @click.stop="deleteTask(task)"
            >
              <text class="btn-text">删除</text>
            </button>
          </view>
        </view>
      </view>

      <!-- 空状态 -->
      <view v-else class="empty-state">
        <text class="empty-icon">📋</text>
        <text class="empty-title">暂无监控任务</text>
        <text class="empty-desc">点击下方按钮创建您的第一个监控任务</text>
        <button class="create-btn" @click="goToAddTask">
          <text class="btn-text">创建任务</text>
        </button>
      </view>
    </view>

    <!-- 添加任务按钮 -->
    <view class="add-task-btn" @click="goToAddTask">
      <text class="btn-icon">+</text>
    </view>

    <!-- 任务详情弹窗 -->
    <u-popup
      v-model="showDetailModal"
      mode="bottom"
      border-radius="20"
      height="60%"
    >
      <view class="detail-modal" v-if="selectedTask">
        <view class="modal-header">
          <text class="modal-title">任务详情</text>
          <text class="close-btn" @click="showDetailModal = false">✕</text>
        </view>

        <scroll-view class="modal-content" scroll-y>
          <view class="detail-section">
            <text class="section-title">基本信息</text>
            <view class="info-list">
              <view class="info-item">
                <text class="info-label">主播名称:</text>
                <text class="info-value">{{ selectedTask.streamerName }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">平台:</text>
                <text class="info-value">{{ getPlatformLabel(selectedTask.platform) }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">房间号:</text>
                <text class="info-value">{{ selectedTask.roomId }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">任务类型:</text>
                <text class="info-value">{{ getTaskTypeLabel(selectedTask.taskType) }}</text>
              </view>
            </view>
          </view>

          <view class="detail-section" v-if="selectedTask.keywords">
            <text class="section-title">关键词设置</text>
            <view class="keywords-list">
              <text
                v-for="keyword in JSON.parse(selectedTask.keywords || '[]')"
                :key="keyword"
                class="keyword-tag"
              >
                {{ keyword }}
              </text>
            </view>
          </view>

          <view class="detail-section">
            <text class="section-title">通知设置</text>
            <view class="info-list">
              <view class="info-item">
                <text class="info-label">通知方式:</text>
                <text class="info-value">{{ selectedTask.notificationMethods || 'wechat' }}</text>
              </view>
              <view class="info-item" v-if="selectedTask.doNotDisturbStart">
                <text class="info-label">免打扰:</text>
                <text class="info-value">
                  {{ selectedTask.doNotDisturbStart }} - {{ selectedTask.doNotDisturbEnd }}
                </text>
              </view>
              <view class="info-item">
                <text class="info-label">AI分析:</text>
                <text class="info-value">{{ selectedTask.aiAnalysis ? '启用' : '关闭' }}</text>
              </view>
            </view>
          </view>

          <view class="detail-section">
            <text class="section-title">统计信息</text>
            <view class="info-list">
              <view class="info-item">
                <text class="info-label">创建时间:</text>
                <text class="info-value">{{ formatDateTime(selectedTask.createdAt) }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">触发次数:</text>
                <text class="info-value">{{ selectedTask.triggerCount || 0 }}</text>
              </view>
              <view class="info-item" v-if="selectedTask.lastTriggeredAt">
                <text class="info-label">最后触发:</text>
                <text class="info-value">{{ formatDateTime(selectedTask.lastTriggeredAt) }}</text>
              </view>
            </view>
          </view>
        </scroll-view>

        <view class="modal-actions">
          <button class="modal-btn edit-btn" @click="editTask(selectedTask)">
            <text class="btn-text">编辑任务</text>
          </button>
          <button class="modal-btn delete-btn" @click="deleteTask(selectedTask)">
            <text class="btn-text">删除任务</text>
          </button>
        </view>
      </view>
    </u-popup>
  </view>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useTaskStore } from '../../stores/task'
import api from '../../services/api'

export default {
  setup() {
    const taskStore = useTaskStore()

    // 状态数据
    const searchKeyword = ref('')
    const currentFilter = ref(0)
    const showDetailModal = ref(false)
    const selectedTask = ref(null)

    // 筛选选项
    const filterTabs = [
      { name: '全部' },
      { name: '运行中' },
      { name: '已暂停' },
      { name: '今日触发' }
    ]

    // 计算属性
    const tasks = computed(() => taskStore.tasks)
    const totalTasks = computed(() => taskStore.totalTasks)
    const activeTasks = computed(() => taskStore.activeTasks)
    const pausedTasks = computed(() => totalTasks.value - activeTasks.value)

    // 页面加载
    onMounted(() => {
      loadTasks()
    })

    // 加载任务列表
    const loadTasks = async () => {
      try {
        const params = {
          keyword: searchKeyword.value,
          status: currentFilter.value === 1 ? 1 : currentFilter.value === 2 ? 0 : undefined,
          todayTrigger: currentFilter.value === 3
        }

        const response = await api.task.getTaskList(params)
        taskStore.setTasks(response.records || [])
      } catch (error) {
        console.error('Load tasks error:', error)
      }
    }

    // 筛选切换
    const onFilterChange = (index) => {
      currentFilter.value = index
      loadTasks()
    }

    // 切换任务状态
    const toggleTaskStatus = async (task) => {
      try {
        const newStatus = task.status === 1 ? 0 : 1

        if (newStatus === 1) {
          await api.task.startTask(task.id)
        } else {
          await api.task.stopTask(task.id)
        }

        taskStore.updateTask(task.id, { status: newStatus })

        uni.showToast({
          title: newStatus === 1 ? '任务已启动' : '任务已暂停',
          icon: 'success'
        })
      } catch (error) {
        console.error('Toggle task status error:', error)
        uni.showToast({
          title: '操作失败',
          icon: 'none'
        })
      }
    }

    // 编辑任务
    const editTask = (task) => {
      uni.navigateTo({
        url: `/pages/task/task-add?id=${task.id}&mode=edit`
      })
    }

    // 删除任务
    const deleteTask = (task) => {
      uni.showModal({
        title: '确认删除',
        content: `确定要删除监控任务「${task.streamerName}」吗？`,
        success: async (res) => {
          if (res.confirm) {
            try {
              await api.task.deleteTask(task.id)
              taskStore.deleteTask(task.id)

              uni.showToast({
                title: '删除成功',
                icon: 'success'
              })

              if (showDetailModal.value) {
                showDetailModal.value = false
              }
            } catch (error) {
              console.error('Delete task error:', error)
              uni.showToast({
                title: '删除失败',
                icon: 'none'
              })
            }
          }
        }
      })
    }

    // 显示任务详情
    const showTaskDetail = (task) => {
      selectedTask.value = task
      showDetailModal.value = true
    }

    // 跳转到添加任务页面
    const goToAddTask = () => {
      uni.navigateTo({
        url: '/pages/task/task-add'
      })
    }

    // 工具方法
    const getPlatformLabel = (platform) => {
      return taskStore.getPlatformLabel(platform)
    }

    const getTaskTypeLabel = (type) => {
      return taskStore.getTaskTypeLabel(type)
    }

    const getTaskTypeIcon = (type) => {
      const iconMap = {
        live_start: '🔴',
        product_launch: '🛍️',
        keyword_match: '🔍'
      }
      return iconMap[type] || '📋'
    }

    const getStatusClass = (status) => {
      return status === 1 ? 'status-running' : 'status-paused'
    }

    const getStatusText = (status) => {
      return status === 1 ? '运行中' : '已暂停'
    }

    const formatTime = (timeStr) => {
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date

      if (diff < 60000) {
        return '刚刚'
      } else if (diff < 3600000) {
        return Math.floor(diff / 60000) + '分钟前'
      } else if (diff < 86400000) {
        return Math.floor(diff / 3600000) + '小时前'
      } else {
        return Math.floor(diff / 86400000) + '天前'
      }
    }

    const formatDateTime = (timeStr) => {
      return new Date(timeStr).toLocaleString('zh-CN')
    }

    return {
      // 状态
      searchKeyword,
      currentFilter,
      showDetailModal,
      selectedTask,
      filterTabs,

      // 计算属性
      tasks,
      totalTasks,
      activeTasks,
      pausedTasks,

      // 方法
      loadTasks,
      onFilterChange,
      toggleTaskStatus,
      editTask,
      deleteTask,
      showTaskDetail,
      goToAddTask,
      getPlatformLabel,
      getTaskTypeLabel,
      getTaskTypeIcon,
      getStatusClass,
      getStatusText,
      formatTime,
      formatDateTime
    }
  }
}
</script>

<style lang="scss" scoped>
.task-page {
  min-height: 100vh;
  background: #f8f8f8;
  padding-bottom: 100rpx;
}

.stats-header {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20rpx;

  .stat-item {
    text-align: center;

    .stat-number {
      display: block;
      font-size: 36rpx;
      font-weight: bold;
      color: #007AFF;
      margin-bottom: 8rpx;
    }

    .stat-label {
      font-size: 24rpx;
      color: #666;
    }
  }
}

.filter-section {
  margin-bottom: 20rpx;

  .search-box {
    margin-bottom: 20rpx;
  }

  .filter-options {
    margin-top: 10rpx;
  }
}

.tasks-section {
  .tasks-list {
    .task-card {
      margin-bottom: 20rpx;
    }
  }

  .empty-state {
    text-align: center;
    padding: 80rpx 40rpx;

    .empty-icon {
      font-size: 80rpx;
      margin-bottom: 20rpx;
    }

    .empty-title {
      display: block;
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
      margin-bottom: 10rpx;
    }

    .empty-desc {
      display: block;
      font-size: 24rpx;
      color: #666;
      margin-bottom: 40rpx;
    }

    .create-btn {
      background: #007AFF;
      color: white;
      border-radius: 25rpx;
      padding: 20rpx 40rpx;
      font-size: 28rpx;
    }
  }
}

.task-card {
  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15rpx;

    .task-info {
      .streamer-name {
        font-size: 32rpx;
        font-weight: 600;
        color: #333;
        margin-right: 10rpx;
      }

      .platform-tag {
        background: #f0f0f0;
        color: #666;
        font-size: 20rpx;
        padding: 4rpx 12rpx;
        border-radius: 12rpx;
      }
    }

    .task-status {
      .status-badge {
        font-size: 20rpx;
        padding: 6rpx 16rpx;
        border-radius: 16rpx;

        &.status-running {
          background: #e6f7e6;
          color: #4CAF50;
        }

        &.status-paused {
          background: #fff3e0;
          color: #FF9800;
        }
      }
    }
  }

  .task-type {
    display: flex;
    align-items: center;
    margin-bottom: 15rpx;

    .type-icon {
      font-size: 24rpx;
      margin-right: 8rpx;
    }

    .type-text {
      font-size: 24rpx;
      color: #666;
      margin-right: 10rpx;
    }

    .ai-badge {
      background: #e6f3ff;
      color: #007AFF;
      font-size: 18rpx;
      padding: 2rpx 8rpx;
      border-radius: 8rpx;
    }
  }

  .task-details {
    margin-bottom: 20rpx;

    .detail-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8rpx;

      .detail-label {
        font-size: 24rpx;
        color: #999;
      }

      .detail-value {
        font-size: 24rpx;
        color: #333;
      }
    }
  }

  .task-actions {
    display: flex;
    gap: 10rpx;

    .action-btn {
      flex: 1;
      padding: 12rpx;
      border-radius: 8rpx;
      font-size: 24rpx;

      &.toggle-btn {
        &.start-btn {
          background: #4CAF50;
          color: white;
        }

        &.pause-btn {
          background: #FF9800;
          color: white;
        }
      }

      &.edit-btn {
        background: #007AFF;
        color: white;
      }

      &.delete-btn {
        background: #FF3B30;
        color: white;
      }
    }
  }
}

.add-task-btn {
  position: fixed;
  bottom: 40rpx;
  right: 40rpx;
  width: 100rpx;
  height: 100rpx;
  background: #007AFF;
  border-radius: 50rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba(0, 122, 255, 0.3);

  .btn-icon {
    font-size: 48rpx;
    color: white;
  }
}

.detail-modal {
  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 30rpx;
    border-bottom: 1rpx solid #f0f0f0;

    .modal-title {
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
    }

    .close-btn {
      font-size: 32rpx;
      color: #999;
    }
  }

  .modal-content {
    height: 80%;
    padding: 30rpx;

    .detail-section {
      margin-bottom: 30rpx;

      .section-title {
        font-size: 28rpx;
        font-weight: 600;
        color: #333;
        margin-bottom: 15rpx;
      }

      .info-list {
        .info-item {
          display: flex;
          justify-content: space-between;
          margin-bottom: 10rpx;

          .info-label {
            font-size: 24rpx;
            color: #666;
          }

          .info-value {
            font-size: 24rpx;
            color: #333;
          }
        }
      }

      .keywords-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10rpx;

        .keyword-tag {
          background: #f0f0f0;
          color: #666;
          font-size: 20rpx;
          padding: 6rpx 12rpx;
          border-radius: 12rpx;
        }
      }
    }
  }

  .modal-actions {
    display: flex;
    gap: 20rpx;
    padding: 30rpx;
    border-top: 1rpx solid #f0f0f0;

    .modal-btn {
      flex: 1;
      padding: 20rpx;
      border-radius: 12rpx;
      font-size: 28rpx;

      &.edit-btn {
        background: #007AFF;
        color: white;
      }

      &.delete-btn {
        background: #FF3B30;
        color: white;
      }
    }
  }
}
</style>