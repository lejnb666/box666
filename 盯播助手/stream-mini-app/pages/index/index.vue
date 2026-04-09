<template>
  <view class="index-page">
    <!-- 用户信息卡片 -->
    <view class="user-card card">
      <view class="user-info">
        <image :src="userInfo?.avatarUrl || '/static/default-avatar.png'" class="avatar" />
        <view class="user-details">
          <text class="nickname">{{ userInfo?.nickname || '用户' }}</text>
          <text class="welcome-text">欢迎使用盯播助手</text>
        </view>
      </view>
      <button class="profile-btn" @click="goToProfile">
        <text class="btn-text">个人中心</text>
        <text class="arrow">›</text>
      </button>
    </view>

    <!-- 数据统计卡片 -->
    <view class="stats-section">
      <view class="stat-card">
        <text class="stat-number">{{ stats.totalTasks }}</text>
        <text class="stat-label">总任务数</text>
      </view>
      <view class="stat-card">
        <text class="stat-number">{{ stats.activeTasks }}</text>
        <text class="stat-label">活跃任务</text>
      </view>
      <view class="stat-card">
        <text class="stat-number">{{ stats.totalTriggers }}</text>
        <text class="stat-label">触发次数</text>
      </view>
      <view class="stat-card">
        <text class="stat-number">{{ stats.monitoredStreamers }}</text>
        <text class="stat-label">监控主播</text>
      </view>
    </view>

    <!-- 快速操作 -->
    <view class="quick-actions card">
      <text class="section-title">快速操作</text>
      <view class="actions-grid">
        <view class="action-item" @click="goToAddTask">
          <text class="action-icon">➕</text>
          <text class="action-text">添加任务</text>
        </view>
        <view class="action-item" @click="goToTaskList">
          <text class="action-icon">📋</text>
          <text class="action-text">任务管理</text>
        </view>
        <view class="action-item" @click="goToHistory">
          <text class="action-icon">📊</text>
          <text class="action-text">推送历史</text>
        </view>
        <view class="action-item" @click="showSettings">
          <text class="action-icon">⚙️</text>
          <text class="action-text">系统设置</text>
        </view>
      </view>
    </view>

    <!-- 热门主播推荐 -->
    <view class="hot-streamers card">
      <view class="section-header">
        <text class="section-title">热门主播</text>
        <text class="refresh-btn" @click="refreshHotStreamers">🔄 刷新</text>
      </view>
      <scroll-view class="streamers-scroll" scroll-x>
        <view class="streamers-list">
          <view
            v-for="streamer in hotStreamers"
            :key="streamer.id"
            class="streamer-item"
            @click="addTaskForStreamer(streamer)"
          >
            <image :src="streamer.avatarUrl || '/static/default-streamer.png'" class="streamer-avatar" />
            <text class="streamer-name">{{ streamer.streamerName }}</text>
            <text class="streamer-platform">{{ getPlatformLabel(streamer.platform) }}</text>
            <text class="streamer-viewers">{{ formatViewerCount(streamer.avgViewerCount) }}人观看</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <!-- 最近触发记录 -->
    <view class="recent-triggers card">
      <view class="section-header">
        <text class="section-title">最近触发</text>
        <text class="view-all" @click="goToHistory">查看全部 ›</text>
      </view>
      <view v-if="recentTriggers.length > 0" class="triggers-list">
        <view
          v-for="trigger in recentTriggers"
          :key="trigger.id"
          class="trigger-item"
          @click="showTriggerDetail(trigger)"
        >
          <view class="trigger-icon">
            <text>{{ getTriggerIcon(trigger.triggerType) }}</text>
          </view>
          <view class="trigger-content">
            <text class="trigger-title">{{ trigger.messageTitle }}</text>
            <text class="trigger-time">{{ formatTime(trigger.sentAt) }}</text>
          </view>
          <view class="trigger-confidence" v-if="trigger.aiConfidence">
            <text class="confidence-text">{{ (trigger.aiConfidence * 100).toFixed(0) }}%</text>
          </view>
        </view>
      </view>
      <view v-else class="empty-state">
        <text class="empty-text">暂无触发记录</text>
      </view>
    </view>

    <!-- 系统状态 -->
    <view class="system-status card">
      <text class="section-title">系统状态</text>
      <view class="status-list">
        <view class="status-item">
          <text class="status-label">爬虫服务</text>
          <text class="status-value" :class="getStatusClass(systemStatus.crawler)">
            {{ getStatusText(systemStatus.crawler) }}
          </text>
        </view>
        <view class="status-item">
          <text class="status-label">AI服务</text>
          <text class="status-value" :class="getStatusClass(systemStatus.ai)">
            {{ getStatusText(systemStatus.ai) }}
          </text>
        </view>
        <view class="status-item">
          <text class="status-label">WebSocket</text>
          <text class="status-value" :class="getStatusClass(systemStatus.websocket)">
            {{ getStatusText(systemStatus.websocket) }}
          </text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../../stores/user'
import { useTaskStore } from '../../stores/task'
import api from '../../services/api'

export default {
  setup() {
    const userStore = useUserStore()
    const taskStore = useTaskStore()

    // 数据状态
    const userInfo = ref(null)
    const stats = ref({
      totalTasks: 0,
      activeTasks: 0,
      totalTriggers: 0,
      monitoredStreamers: 0
    })
    const hotStreamers = ref([])
    const recentTriggers = ref([])
    const systemStatus = ref({
      crawler: false,
      ai: false,
      websocket: false
    })

    // 页面加载
    onMounted(() => {
      initPage()
    })

    // 初始化页面数据
    const initPage = async () => {
      userInfo.value = userStore.userInfo
      await Promise.all([
        loadUserStats(),
        loadHotStreamers(),
        loadRecentTriggers(),
        checkSystemStatus()
      ])
    }

    // 加载用户统计
    const loadUserStats = async () => {
      try {
        const response = await api.user.getUserStats()
        stats.value = response
      } catch (error) {
        console.error('Load user stats error:', error)
      }
    }

    // 加载热门主播
    const loadHotStreamers = async () => {
      try {
        // 调用后端API获取热门主播列表
        const response = await api.streamer.getHotList({ limit: 10 })
        hotStreamers.value = response.records || response.data || []
      } catch (error) {
        console.error('Load hot streamers error:', error)
        // 如果API调用失败，显示错误提示
        uni.showToast({
          title: '获取热门主播失败',
          icon: 'none'
        })
      }
    }

    // 加载最近触发记录
    const loadRecentTriggers = async () => {
      try {
        const response = await api.history.getPushHistory({ limit: 5 })
        recentTriggers.value = response.records || []
      } catch (error) {
        console.error('Load recent triggers error:', error)
      }
    }

    // 检查系统状态
    const checkSystemStatus = async () => {
      try {
        const response = await api.crawler.getCrawlerStatus()
        systemStatus.value = {
          crawler: response.services?.crawler || false,
          ai: response.services?.ai || false,
          websocket: response.services?.websocket || false
        }
      } catch (error) {
        console.error('Check system status error:', error)
      }
    }

    // 刷新热门主播
    const refreshHotStreamers = () => {
      loadHotStreamers()
    }

    // 为指定主播添加任务
    const addTaskForStreamer = (streamer) => {
      uni.navigateTo({
        url: `/pages/task/task-add?streamerId=${streamer.id}&platform=${streamer.platform}&streamerName=${streamer.streamerName}`
      })
    }

    // 显示触发详情
    const showTriggerDetail = (trigger) => {
      uni.showModal({
        title: trigger.messageTitle,
        content: trigger.messageContent || trigger.triggerContent,
        showCancel: false,
        confirmText: '知道了'
      })
    }

    // 跳转到个人中心
    const goToProfile = () => {
      uni.switchTab({
        url: '/pages/profile/profile'
      })
    }

    // 跳转到添加任务页面
    const goToAddTask = () => {
      uni.navigateTo({
        url: '/pages/task/task-add'
      })
    }

    // 跳转到任务列表
    const goToTaskList = () => {
      uni.switchTab({
        url: '/pages/task/task'
      })
    }

    // 跳转到推送历史
    const goToHistory = () => {
      uni.switchTab({
        url: '/pages/history/history'
      })
    }

    // 显示设置
    const showSettings = () => {
      uni.showActionSheet({
        itemList: ['通知设置', '隐私设置', '关于应用'],
        success: (res) => {
          const index = res.tapIndex
          if (index === 0) {
            // 通知设置
            uni.showToast({ title: '通知设置', icon: 'none' })
          } else if (index === 1) {
            // 隐私设置
            uni.showToast({ title: '隐私设置', icon: 'none' })
          } else if (index === 2) {
            // 关于应用
            uni.showModal({
              title: '关于盯播助手',
              content: '版本：1.0.0\n智能直播监控助手\n© 2026 StreamMonitor',
              showCancel: false
            })
          }
        }
      })
    }

    // 工具方法
    const getPlatformLabel = (platform) => {
      const platformMap = {
        bilibili: 'B站',
        douyu: '斗鱼',
        huya: '虎牙',
        douyin: '抖音'
      }
      return platformMap[platform] || platform
    }

    const formatViewerCount = (count) => {
      if (count >= 10000) {
        return (count / 10000).toFixed(1) + 'w'
      }
      return count.toString()
    }

    const formatTime = (timeStr) => {
      const date = new Date(timeStr)
      const now = new Date()
      const diff = now - date

      if (diff < 60000) { // 1分钟内
        return '刚刚'
      } else if (diff < 3600000) { // 1小时内
        return Math.floor(diff / 60000) + '分钟前'
      } else if (diff < 86400000) { // 1天内
        return Math.floor(diff / 3600000) + '小时前'
      } else {
        return Math.floor(diff / 86400000) + '天前'
      }
    }

    const getTriggerIcon = (type) => {
      const iconMap = {
        live_start: '🔴',
        product_launch: '🛍️',
        keyword_match: '🔍',
        lottery: '🎁',
        discount: '💰'
      }
      return iconMap[type] || '📢'
    }

    const getStatusClass = (status) => {
      return status ? 'status-online' : 'status-offline'
    }

    const getStatusText = (status) => {
      return status ? '正常' : '离线'
    }

    return {
      userInfo,
      stats,
      hotStreamers,
      recentTriggers,
      systemStatus,
      initPage,
      loadUserStats,
      loadHotStreamers,
      loadRecentTriggers,
      checkSystemStatus,
      refreshHotStreamers,
      addTaskForStreamer,
      showTriggerDetail,
      goToProfile,
      goToAddTask,
      goToTaskList,
      goToHistory,
      showSettings,
      getPlatformLabel,
      formatViewerCount,
      formatTime,
      getTriggerIcon,
      getStatusClass,
      getStatusText
    }
  }
}
</script>

<style lang="scss" scoped>
.index-page {
  padding: 20rpx;
  background: #f8f8f8;
  min-height: 100vh;
}

.user-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;

  .user-info {
    display: flex;
    align-items: center;

    .avatar {
      width: 80rpx;
      height: 80rpx;
      border-radius: 40rpx;
      margin-right: 20rpx;
    }

    .user-details {
      .nickname {
        display: block;
        font-size: 32rpx;
        font-weight: 600;
        color: #333;
        margin-bottom: 4rpx;
      }

      .welcome-text {
        font-size: 24rpx;
        color: #666;
      }
    }
  }

  .profile-btn {
    display: flex;
    align-items: center;
    padding: 10rpx 20rpx;
    background: #f0f0f0;
    border-radius: 20rpx;

    .btn-text {
      font-size: 24rpx;
      color: #666;
      margin-right: 8rpx;
    }

    .arrow {
      font-size: 24rpx;
      color: #999;
    }
  }
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15rpx;
  margin-bottom: 20rpx;

  .stat-card {
    background: white;
    border-radius: 12rpx;
    padding: 20rpx;
    text-align: center;
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);

    .stat-number {
      display: block;
      font-size: 36rpx;
      font-weight: bold;
      color: #007AFF;
      margin-bottom: 8rpx;
    }

    .stat-label {
      font-size: 20rpx;
      color: #666;
    }
  }
}

.quick-actions {
  margin-bottom: 20rpx;

  .section-title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 30rpx;
  }

  .actions-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20rpx;

    .action-item {
      text-align: center;
      padding: 30rpx 0;

      .action-icon {
        display: block;
        font-size: 48rpx;
        margin-bottom: 10rpx;
      }

      .action-text {
        font-size: 24rpx;
        color: #666;
      }
    }
  }
}

.hot-streamers {
  margin-bottom: 20rpx;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20rpx;

    .section-title {
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
    }

    .refresh-btn {
      font-size: 24rpx;
      color: #007AFF;
    }
  }

  .streamers-scroll {
    white-space: nowrap;
  }

  .streamers-list {
    display: flex;
    padding: 0 10rpx;

    .streamer-item {
      width: 200rpx;
      margin-right: 20rpx;
      text-align: center;

      .streamer-avatar {
        width: 120rpx;
        height: 120rpx;
        border-radius: 60rpx;
        margin-bottom: 10rpx;
      }

      .streamer-name {
        display: block;
        font-size: 24rpx;
        font-weight: 500;
        color: #333;
        margin-bottom: 4rpx;
      }

      .streamer-platform {
        display: block;
        font-size: 20rpx;
        color: #666;
        margin-bottom: 4rpx;
      }

      .streamer-viewers {
        font-size: 18rpx;
        color: #999;
      }
    }
  }
}

.recent-triggers {
  margin-bottom: 20rpx;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20rpx;

    .section-title {
      font-size: 32rpx;
      font-weight: 600;
      color: #333;
    }

    .view-all {
      font-size: 24rpx;
      color: #007AFF;
    }
  }

  .triggers-list {
    .trigger-item {
      display: flex;
      align-items: center;
      padding: 20rpx 0;
      border-bottom: 1rpx solid #f0f0f0;

      .trigger-icon {
        width: 60rpx;
        height: 60rpx;
        border-radius: 30rpx;
        background: #f8f8f8;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 20rpx;

        text {
          font-size: 28rpx;
        }
      }

      .trigger-content {
        flex: 1;

        .trigger-title {
          display: block;
          font-size: 28rpx;
          color: #333;
          margin-bottom: 4rpx;
        }

        .trigger-time {
          font-size: 20rpx;
          color: #999;
        }
      }

      .trigger-confidence {
        .confidence-text {
          font-size: 20rpx;
          color: #007AFF;
          background: #e6f3ff;
          padding: 4rpx 12rpx;
          border-radius: 12rpx;
        }
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 40rpx 0;

    .empty-text {
      font-size: 24rpx;
      color: #999;
    }
  }
}

.system-status {
  .section-title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 20rpx;
  }

  .status-list {
    .status-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15rpx 0;

      .status-label {
        font-size: 28rpx;
        color: #333;
      }

      .status-value {
        font-size: 24rpx;
        padding: 4rpx 12rpx;
        border-radius: 12rpx;

        &.status-online {
          color: #4CD964;
          background: #f0f9f0;
        }

        &.status-offline {
          color: #FF3B30;
          background: #fff0f0;
        }
      }
    }
  }
}
</style>