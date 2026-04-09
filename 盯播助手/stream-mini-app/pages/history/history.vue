<template>
  <view class="history-page">
    <!-- 统计卡片 -->
    <view class="stats-section card">
      <view class="stat-item">
        <text class="stat-number">{{ totalCount }}</text>
        <text class="stat-label">总推送</text>
      </view>
      <view class="stat-item">
        <text class="stat-number">{{ todayCount }}</text>
        <text class="stat-label">今日</text>
      </view>
      <view class="stat-item">
        <text class="stat-number">{{ unreadCount }}</text>
        <text class="stat-label">未读</text>
      </view>
    </view>

    <!-- 筛选和搜索 -->
    <view class="filter-section card">
      <view class="search-box">
        <u-search
          v-model="searchKeyword"
          placeholder="搜索推送内容"
          :show-action="false"
          @search="loadHistory"
          @clear="loadHistory"
        />
      </view>

      <view class="filter-tabs">
        <u-tabs
          :list="filterTabs"
          :current="currentFilter"
          @change="onFilterChange"
          :active-color="'#007AFF'"
        />
      </view>

      <view class="action-buttons">
        <button class="action-btn" @click="markAllAsRead">
          <text class="btn-text">全部已读</text>
        </button>
        <button class="action-btn" @click="showFilterOptions">
          <text class="btn-text">筛选</text>
        </button>
      </view>
    </view>

    <!-- 推送历史列表 -->
    <view class="history-section">
      <view v-if="historyList.length > 0" class="history-list">
        <view
          v-for="item in historyList"
          :key="item.id"
          class="history-item card"
          :class="{ unread: item.status === 2 }"
          @click="showHistoryDetail(item)"
        >
          <!-- 推送头部 -->
          <view class="history-header">
            <view class="trigger-info">
              <text class="trigger-icon">{{ getTriggerIcon(item.triggerType) }}</text>
              <text class="trigger-type">{{ getTriggerTypeLabel(item.triggerType) }}</text>
              <text class="streamer-name">{{ item.streamerName }}</text>
            </view>
            <view class="history-status">
              <text
                class="status-badge"
                :class="getStatusClass(item.status)"
              >
                {{ getStatusText(item.status) }}
              </text>
              <text v-if="item.status === 2" class="unread-dot"></text>
            </view>
          </view>

          <!-- 推送内容 -->
          <view class="history-content">
            <text class="message-title">{{ item.messageTitle }}</text>
            <text class="message-preview">{{ getMessagePreview(item.messageContent) }}</text>
          </view>

          <!-- AI分析信息 -->
          <view v-if="item.aiConfidence" class="ai-info">
            <text class="ai-label">AI置信度:</text>
            <text class="ai-confidence">{{ (item.aiConfidence * 100).toFixed(0) }}%</text>
            <view class="confidence-bar">
              <view
                class="confidence-fill"
                :style="{ width: (item.aiConfidence * 100) + '%' }"
                :class="getConfidenceClass(item.aiConfidence)"
              ></view>
            </view>
          </view>

          <!-- 触发内容 -->
          <view v-if="item.triggerContent" class="trigger-content">
            <text class="trigger-text">{{ item.triggerContent }}</text>
          </view>

          <!-- 推送底部 -->
          <view class="history-footer">
            <text class="sent-time">{{ formatTime(item.sentAt) }}</text>
            <text class="platform-tag">{{ getPlatformLabel(item.platform) }}</text>
          </view>
        </view>
      </view>

      <!-- 空状态 -->
      <view v-else class="empty-state">
        <text class="empty-icon">📭</text>
        <text class="empty-title">暂无推送记录</text>
        <text class="empty-desc">开始创建监控任务，获取第一手直播信息</text>
        <button class="create-task-btn" @click="goToCreateTask">
          <text class="btn-text">创建监控任务</text>
        </button>
      </view>
    </view>

    <!-- 加载更多 -->
    <view v-if="hasMore" class="load-more">
      <button class="load-btn" :loading="loading" @click="loadMore">
        <text class="btn-text">{{ loading ? '加载中...' : '加载更多' }}</text>
      </button>
    </view>

    <!-- 详情弹窗 -->
    <u-popup
      v-model="showDetailModal"
      mode="bottom"
      border-radius="20"
      height="70%"
    >
      <view class="detail-modal" v-if="selectedItem">
        <view class="modal-header">
          <text class="modal-title">推送详情</text>
          <text class="close-btn" @click="showDetailModal = false">✕</text>
        </view>

        <scroll-view class="modal-content" scroll-y>
          <view class="detail-section">
            <text class="section-title">基本信息</text>
            <view class="info-grid">
              <view class="info-item">
                <text class="info-label">触发类型:</text>
                <text class="info-value">{{ getTriggerTypeLabel(selectedItem.triggerType) }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">主播:</text>
                <text class="info-value">{{ selectedItem.streamerName }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">平台:</text>
                <text class="info-value">{{ getPlatformLabel(selectedItem.platform) }}</text>
              </view>
              <view class="info-item">
                <text class="info-label">推送时间:</text>
                <text class="info-value">{{ formatDateTime(selectedItem.sentAt) }}</text>
              </view>
            </view>
          </view>

          <view class="detail-section">
            <text class="section-title">推送内容</text>
            <view class="content-box">
              <text class="content-title">{{ selectedItem.messageTitle }}</text>
              <text class="content-text">{{ selectedItem.messageContent }}</text>
            </view>
          </view>

          <view v-if="selectedItem.triggerContent" class="detail-section">
            <text class="section-title">触发内容</text>
            <view class="trigger-box">
              <text class="trigger-text">{{ selectedItem.triggerContent }}</text>
            </view>
          </view>

          <view v-if="selectedItem.aiConfidence" class="detail-section">
            <text class="section-title">AI分析</text>
            <view class="ai-analysis">
              <view class="confidence-display">
                <text class="confidence-label">置信度:</text>
                <text class="confidence-value">{{ (selectedItem.aiConfidence * 100).toFixed(1) }}%</text>
              </view>
              <view class="confidence-bar large">
                <view
                  class="confidence-fill"
                  :style="{ width: (selectedItem.aiConfidence * 100) + '%' }"
                  :class="getConfidenceClass(selectedItem.aiConfidence)"
                ></view>
              </view>
            </view>
          </view>
        </scroll-view>

        <view class="modal-actions">
          <button
            v-if="selectedItem.status === 2"
            class="modal-btn mark-read-btn"
            @click="markAsRead(selectedItem)"
          >
            <text class="btn-text">标记已读</text>
          </button>
          <button class="modal-btn delete-btn" @click="deleteHistory(selectedItem)">
            <text class="btn-text">删除记录</text>
          </button>
        </view>
      </view>
    </u-popup>

    <!-- 筛选弹窗 -->
    <u-action-sheet
      v-model="showFilterModal"
      :list="filterOptions"
      @click="onFilterOptionSelect"
      cancel-text="取消"
    />
  </view>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import api from '../../services/api'

export default {
  setup() {
    // 状态数据
    const searchKeyword = ref('')
    const currentFilter = ref(0)
    const loading = ref(false)
    const showDetailModal = ref(false)
    const showFilterModal = ref(false)
    const selectedItem = ref(null)
    const page = ref(1)
    const pageSize = ref(20)
    const hasMore = ref(true)

    // 数据列表
    const historyList = ref([])
    const totalCount = ref(0)
    const todayCount = ref(0)
    const unreadCount = ref(0)

    // 筛选选项
    const filterTabs = [
      { name: '全部' },
      { name: '未读' },
      { name: '今日' },
      { name: 'AI分析' }
    ]

    const filterOptions = [
      { text: '按类型筛选' },
      { text: '按平台筛选' },
      { text: '按时间筛选' },
      { text: '清除筛选' }
    ]

    // 计算属性
    const filteredList = computed(() => {
      let filtered = historyList.value

      if (currentFilter.value === 1) { // 未读
        filtered = filtered.filter(item => item.status === 2)
      } else if (currentFilter.value === 2) { // 今日
        const today = new Date().toDateString()
        filtered = filtered.filter(item =>
          new Date(item.sentAt).toDateString() === today
        )
      } else if (currentFilter.value === 3) { // AI分析
        filtered = filtered.filter(item => item.aiConfidence)
      }

      if (searchKeyword.value) {
        const keyword = searchKeyword.value.toLowerCase()
        filtered = filtered.filter(item =>
          item.messageTitle.toLowerCase().includes(keyword) ||
          item.messageContent.toLowerCase().includes(keyword) ||
          item.streamerName.toLowerCase().includes(keyword)
        )
      }

      return filtered
    })

    // 页面加载
    onMounted(() => {
      loadHistory()
      loadStats()
    })

    // 加载统计数据
    const loadStats = async () => {
      try {
        // 这里应该调用获取统计数据的API
        // 暂时使用模拟数据
        totalCount.value = 156
        todayCount.value = 12
        unreadCount.value = 8
      } catch (error) {
        console.error('Load stats error:', error)
      }
    }

    // 加载历史记录
    const loadHistory = async (reset = true) => {
      if (loading.value) return

      loading.value = true

      try {
        if (reset) {
          page.value = 1
          historyList.value = []
        }

        const params = {
          page: page.value,
          pageSize: pageSize.value,
          keyword: searchKeyword.value,
          status: currentFilter.value === 1 ? 2 : undefined,
          today: currentFilter.value === 2,
          hasAi: currentFilter.value === 3
        }

        const response = await api.history.getPushHistory(params)
        const newRecords = response.records || []

        if (reset) {
          historyList.value = newRecords
        } else {
          historyList.value.push(...newRecords)
        }

        hasMore.value = newRecords.length === pageSize.value
        page.value++

      } catch (error) {
        console.error('Load history error:', error)
        uni.showToast({
          title: '加载失败',
          icon: 'none'
        })
      } finally {
        loading.value = false
      }
    }

    // 加载更多
    const loadMore = () => {
      if (hasMore.value && !loading.value) {
        loadHistory(false)
      }
    }

    // 筛选切换
    const onFilterChange = (index) => {
      currentFilter.value = index
      loadHistory()
    }

    // 显示筛选选项
    const showFilterOptions = () => {
      showFilterModal.value = true
    }

    // 筛选选项选择
    const onFilterOptionSelect = (index) => {
      switch (index) {
        case 0:
          // 按类型筛选
          uni.showActionSheet({
            itemList: ['开播提醒', '商品上架', '关键词匹配', '抽奖活动'],
            success: (res) => {
              // 处理类型筛选
            }
          })
          break
        case 1:
          // 按平台筛选
          uni.showActionSheet({
            itemList: ['哔哩哔哩', '斗鱼直播', '虎牙直播', '抖音直播'],
            success: (res) => {
              // 处理平台筛选
            }
          })
          break
        case 2:
          // 按时间筛选
          uni.showActionSheet({
            itemList: ['今天', '最近7天', '最近30天', '自定义'],
            success: (res) => {
              // 处理时间筛选
            }
          })
          break
        case 3:
          // 清除筛选
          currentFilter.value = 0
          searchKeyword.value = ''
          loadHistory()
          break
      }
    }

    // 全部标记为已读
    const markAllAsRead = async () => {
      try {
        // 这里应该调用批量标记已读的API
        historyList.value.forEach(item => {
          if (item.status === 2) {
            item.status = 1
          }
        })
        unreadCount.value = 0

        uni.showToast({
          title: '已全部标记为已读',
          icon: 'success'
        })
      } catch (error) {
        console.error('Mark all as read error:', error)
        uni.showToast({
          title: '操作失败',
          icon: 'none'
        })
      }
    }

    // 显示历史详情
    const showHistoryDetail = (item) => {
      selectedItem.value = item
      showDetailModal.value = true

      // 如果是未读状态，自动标记为已读
      if (item.status === 2) {
        markAsRead(item)
      }
    }

    // 标记为已读
    const markAsRead = async (item) => {
      try {
        await api.history.markAsRead(item.id)
        item.status = 1
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      } catch (error) {
        console.error('Mark as read error:', error)
      }
    }

    // 删除历史记录
    const deleteHistory = (item) => {
      uni.showModal({
        title: '确认删除',
        content: '确定要删除这条推送记录吗？',
        success: async (res) => {
          if (res.confirm) {
            try {
              await api.history.deleteHistory(item.id)
              const index = historyList.value.findIndex(h => h.id === item.id)
              if (index !== -1) {
                historyList.value.splice(index, 1)
              }

              if (showDetailModal.value) {
                showDetailModal.value = false
              }

              uni.showToast({
                title: '删除成功',
                icon: 'success'
              })
            } catch (error) {
              console.error('Delete history error:', error)
              uni.showToast({
                title: '删除失败',
                icon: 'none'
              })
            }
          }
        }
      })
    }

    // 跳转到创建任务页面
    const goToCreateTask = () => {
      uni.switchTab({
        url: '/pages/task/task'
      })
    }

    // 工具方法
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

    const getTriggerTypeLabel = (type) => {
      const labelMap = {
        live_start: '开播提醒',
        product_launch: '商品上架',
        keyword_match: '关键词匹配',
        lottery: '抽奖活动',
        discount: '降价促销'
      }
      return labelMap[type] || type
    }

    const getPlatformLabel = (platform) => {
      const platformMap = {
        bilibili: 'B站',
        douyu: '斗鱼',
        huya: '虎牙',
        douyin: '抖音'
      }
      return platformMap[platform] || platform
    }

    const getStatusClass = (status) => {
      return status === 2 ? 'status-unread' : 'status-read'
    }

    const getStatusText = (status) => {
      return status === 2 ? '未读' : '已读'
    }

    const getConfidenceClass = (confidence) => {
      if (confidence >= 0.8) return 'confidence-high'
      if (confidence >= 0.6) return 'confidence-medium'
      return 'confidence-low'
    }

    const getMessagePreview = (content) => {
      if (!content) return ''
      return content.length > 50 ? content.substring(0, 50) + '...' : content
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
      loading,
      showDetailModal,
      showFilterModal,
      selectedItem,
      hasMore,

      // 数据
      historyList,
      totalCount,
      todayCount,
      unreadCount,
      filterTabs,
      filterOptions,

      // 计算属性
      filteredList,

      // 方法
      loadHistory,
      loadMore,
      onFilterChange,
      showFilterOptions,
      onFilterOptionSelect,
      markAllAsRead,
      showHistoryDetail,
      markAsRead,
      deleteHistory,
      goToCreateTask,
      getTriggerIcon,
      getTriggerTypeLabel,
      getPlatformLabel,
      getStatusClass,
      getStatusText,
      getConfidenceClass,
      getMessagePreview,
      formatTime,
      formatDateTime
    }
  }
}
</script>

<style lang="scss" scoped>
.history-page {
  min-height: 100vh;
  background: #f8f8f8;
  padding-bottom: 40rpx;
}

.stats-section {
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

  .filter-tabs {
    margin-bottom: 20rpx;
  }

  .action-buttons {
    display: flex;
    gap: 20rpx;

    .action-btn {
      flex: 1;
      padding: 15rpx;
      background: #f0f0f0;
      border-radius: 8rpx;
      text-align: center;

      .btn-text {
        font-size: 24rpx;
        color: #666;
      }
    }
  }
}

.history-section {
  .history-list {
    .history-item {
      margin-bottom: 15rpx;
      border-left: 4rpx solid transparent;

      &.unread {
        border-left-color: #007AFF;
        background: #f8fcff;
      }
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

    .create-task-btn {
      background: #007AFF;
      color: white;
      border-radius: 25rpx;
      padding: 20rpx 40rpx;
      font-size: 28rpx;
    }
  }
}

.history-item {
  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15rpx;

    .trigger-info {
      display: flex;
      align-items: center;

      .trigger-icon {
        font-size: 24rpx;
        margin-right: 8rpx;
      }

      .trigger-type {
        font-size: 24rpx;
        font-weight: 500;
        color: #333;
        margin-right: 10rpx;
      }

      .streamer-name {
        font-size: 20rpx;
        color: #666;
        background: #f0f0f0;
        padding: 4rpx 12rpx;
        border-radius: 12rpx;
      }
    }

    .history-status {
      display: flex;
      align-items: center;

      .status-badge {
        font-size: 20rpx;
        padding: 4rpx 12rpx;
        border-radius: 12rpx;

        &.status-unread {
          background: #e6f3ff;
          color: #007AFF;
        }

        &.status-read {
          background: #f0f0f0;
          color: #666;
        }
      }

      .unread-dot {
        width: 8rpx;
        height: 8rpx;
        background: #FF3B30;
        border-radius: 4rpx;
        margin-left: 8rpx;
      }
    }
  }

  .history-content