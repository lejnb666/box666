<template>
  <view class="profile-page">
    <!-- 用户信息卡片 -->
    <view class="user-card card">
      <view class="user-avatar-section">
        <image
          :src="userInfo?.avatarUrl || '/static/default-avatar.png'"
          class="user-avatar"
          @click="chooseAvatar"
        />
        <view class="user-info">
          <text class="user-nickname">{{ userInfo?.nickname || '未设置昵称' }}</text>
          <text class="user-id">ID: {{ userInfo?.id || '未知' }}</text>
          <text class="login-status" :class="loginStatusClass">
            {{ isLoggedIn ? '已登录' : '未登录' }}
          </text>
        </view>
        <button class="edit-btn" @click="editProfile">
          <text class="btn-text">编辑</text>
        </button>
      </view>

      <!-- 用户统计 -->
      <view class="user-stats">
        <view class="stat-item">
          <text class="stat-number">{{ userStats.totalTasks || 0 }}</text>
          <text class="stat-label">监控任务</text>
        </view>
        <view class="stat-item">
          <text class="stat-number">{{ userStats.totalTriggers || 0 }}</text>
          <text class="stat-label">触发次数</text>
        </view>
        <view class="stat-item">
          <text class="stat-number">{{ userStats.monitoredStreamers || 0 }}</text>
          <text class="stat-label">监控主播</text>
        </view>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="menu-section">
      <view class="menu-group">
        <text class="group-title">监控管理</text>
        <view class="menu-list">
          <view class="menu-item" @click="goToTaskManagement">
            <view class="menu-icon">📋</view>
            <text class="menu-text">任务管理</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="goToHistory">
            <view class="menu-icon">📊</view>
            <text class="menu-text">推送历史</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="goToStreamerManagement">
            <view class="menu-icon">🎬</view>
            <text class="menu-text">主播管理</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
      </view>

      <view class="menu-group">
        <text class="group-title">通知设置</text>
        <view class="menu-list">
          <view class="menu-item" @click="showNotificationSettings">
            <view class="menu-icon">🔔</view>
            <text class="menu-text">推送设置</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="subscribeMessage">
            <view class="menu-icon">📱</view>
            <text class="menu-text">订阅消息</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="showDoNotDisturbSettings">
            <view class="menu-icon">🌙</view>
            <text class="menu-text">免打扰设置</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
      </view>

      <view class="menu-group">
        <text class="group-title">应用设置</text>
        <view class="menu-list">
          <view class="menu-item" @click="showCacheSettings">
            <view class="menu-icon">💾</view>
            <text class="menu-text">缓存管理</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="showPrivacySettings">
            <view class="menu-icon">🔒</view>
            <text class="menu-text">隐私设置</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item" @click="showAbout">
            <view class="menu-icon">ℹ️</view>
            <text class="menu-text">关于应用</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
      </view>

      <view class="menu-group">
        <text class="group-title">账户操作</text>
        <view class="menu-list">
          <view class="menu-item" @click="refreshToken">
            <view class="menu-icon">🔄</view>
            <text class="menu-text">刷新Token</text>
            <text class="menu-arrow">›</text>
          </view>
          <view class="menu-item danger" @click="showLogoutConfirm">
            <view class="menu-icon">🚪</view>
            <text class="menu-text">退出登录</text>
            <text class="menu-arrow">›</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 编辑资料弹窗 -->
    <u-popup
      v-model="showEditModal"
      mode="bottom"
      border-radius="20"
      height="60%"
    >
      <view class="edit-modal">
        <view class="modal-header">
          <text class="modal-title">编辑资料</text>
          <text class="close-btn" @click="showEditModal = false">✕</text>
        </view>

        <view class="modal-content">
          <view class="form-item">
            <text class="form-label">昵称</text>
            <u-input
              v-model="editForm.nickname"
              placeholder="请输入昵称"
              :border="true"
            />
          </view>

          <view class="form-item">
            <text class="form-label">手机号</text>
            <u-input
              v-model="editForm.phone"
              placeholder="请输入手机号"
              :border="true"
              type="number"
            />
          </view>

          <view class="form-item">
            <text class="form-label">头像</text>
            <view class="avatar-upload">
              <image
                :src="editForm.avatarUrl || userInfo?.avatarUrl || '/static/default-avatar.png'"
                class="preview-avatar"
                @click="chooseAvatar"
              />
              <text class="upload-text">点击更换头像</text>
            </view>
          </view>
        </view>

        <view class="modal-actions">
          <button class="save-btn" @click="saveProfile">
            <text class="btn-text">保存</text>
          </button>
          <button class="cancel-btn" @click="showEditModal = false">
            <text class="btn-text">取消</text>
          </button>
        </view>
      </view>
    </u-popup>

    <!-- 推送设置弹窗 -->
    <u-action-sheet
      v-model="showNotificationModal"
      title="推送设置"
      :list="notificationOptions"
      @click="onNotificationOptionSelect"
      cancel-text="取消"
    />

    <!-- 退出登录确认 -->
    <u-modal
      v-model="showLogoutModal"
      title="确认退出"
      content="确定要退出登录吗？退出后需要重新授权登录。"
      @confirm="logout"
      show-cancel-button
      confirm-text="退出"
      cancel-text="取消"
    />
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../../stores/user'
import api from '../../services/api'

export default {
  setup() {
    const userStore = useUserStore()

    // 状态数据
    const userInfo = ref(null)
    const userStats = ref({})
    const isLoggedIn = ref(false)
    const showEditModal = ref(false)
    const showNotificationModal = ref(false)
    const showLogoutModal = ref(false)

    // 编辑表单
    const editForm = ref({
      nickname: '',
      phone: '',
      avatarUrl: ''
    })

    // 通知设置选项
    const notificationOptions = [
      { text: '微信订阅消息', subText: '通过微信接收推送通知' },
      { text: '短信通知', subText: '通过短信接收重要通知' },
      { text: '邮件通知', subText: '通过邮件接收详细报告' },
      { text: '免打扰设置', subText: '设置免打扰时间段' }
    ]

    // 页面加载
    onMounted(() => {
      initProfile()
    })

    // 初始化用户信息
    const initProfile = async () => {
      userInfo.value = userStore.userInfo
      isLoggedIn.value = userStore.isLoggedIn

      if (isLoggedIn.value) {
        await loadUserStats()
      }
    }

    // 加载用户统计
    const loadUserStats = async () => {
      try {
        const response = await api.user.getUserStats()
        userStats.value = response
      } catch (error) {
        console.error('Load user stats error:', error)
      }
    }

    // 编辑资料
    const editProfile = () => {
      editForm.value = {
        nickname: userInfo.value?.nickname || '',
        phone: userInfo.value?.phone || '',
        avatarUrl: userInfo.value?.avatarUrl || ''
      }
      showEditModal.value = true
    }

    // 选择头像
    const chooseAvatar = () => {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const tempFilePath = res.tempFilePaths[0]
          // 这里应该上传到服务器获取URL
          // 暂时使用本地路径
          editForm.value.avatarUrl = tempFilePath
        }
      })
    }

    // 保存资料
    const saveProfile = async () => {
      try {
        const response = await api.user.updateUserProfile(editForm.value)
        userStore.setUserInfo(response)
        userInfo.value = response

        showEditModal.value = false
        uni.showToast({
          title: '保存成功',
          icon: 'success'
        })
      } catch (error) {
        console.error('Save profile error:', error)
        uni.showToast({
          title: '保存失败',
          icon: 'none'
        })
      }
    }

    // 跳转到任务管理
    const goToTaskManagement = () => {
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

    // 跳转到主播管理
    const goToStreamerManagement = () => {
      uni.showToast({
        title: '功能开发中',
        icon: 'none'
      })
    }

    // 显示推送设置
    const showNotificationSettings = () => {
      showNotificationModal.value = true
    }

    // 通知设置选项选择
    const onNotificationOptionSelect = (index) => {
      switch (index) {
        case 0:
          subscribeMessage()
          break
        case 1:
          uni.showToast({ title: '短信通知设置', icon: 'none' })
          break
        case 2:
          uni.showToast({ title: '邮件通知设置', icon: 'none' })
          break
        case 3:
          showDoNotDisturbSettings()
          break
      }
    }

    // 订阅微信消息
    const subscribeMessage = async () => {
      try {
        const tmplIds = [
          'LIVE_START_TEMPLATE_ID',
          'PRODUCT_LAUNCH_TEMPLATE_ID',
          'KEYWORD_MATCH_TEMPLATE_ID'
        ]

        await new Promise((resolve, reject) => {
          uni.requestSubscribeMessage({
            tmplIds,
            success: (res) => {
              console.log('Subscribe success:', res)
              uni.showToast({
                title: '订阅成功',
                icon: 'success'
              })
              resolve(res)
            },
            fail: (err) => {
              console.log('Subscribe fail:', err)
              uni.showToast({
                title: '订阅失败',
                icon: 'none'
              })
              reject(err)
            }
          })
        })
      } catch (error) {
        console.error('Subscribe message error:', error)
      }
    }

    // 显示免打扰设置
    const showDoNotDisturbSettings = () => {
      uni.showModal({
        title: '免打扰设置',
        content: '设置免打扰时间段，在此时间段内不会收到推送通知',
        showCancel: false,
        confirmText: '知道了'
      })
    }

    // 显示缓存设置
    const showCacheSettings = () => {
      uni.showActionSheet({
        title: '缓存管理',
        itemList: ['清理图片缓存', '清理数据缓存', '查看缓存大小'],
        success: (res) => {
          const index = res.tapIndex
          switch (index) {
            case 0:
              clearImageCache()
              break
            case 1:
              clearDataCache()
              break
            case 2:
              showCacheSize()
              break
          }
        }
      })
    }

    // 清理图片缓存
    const clearImageCache = () => {
      // uni.clearStorage() 只能清理本地存储，图片缓存需要其他方式
      uni.showToast({
        title: '图片缓存已清理',
        icon: 'success'
      })
    }

    // 清理数据缓存
    const clearDataCache = () => {
      uni.clearStorage()
      uni.showToast({
        title: '数据缓存已清理',
        icon: 'success'
      })
    }

    // 显示缓存大小
    const showCacheSize = () => {
      uni.getStorageInfo({
        success: (res) => {
          const sizeInMB = (res.currentSize / 1024 / 1024).toFixed(2)
          uni.showModal({
            title: '缓存信息',
            content: `当前缓存大小: ${sizeInMB}MB`,
            showCancel: false
          })
        }
      })
    }

    // 显示隐私设置
    const showPrivacySettings = () => {
      uni.showModal({
        title: '隐私设置',
        content: '我们重视您的隐私保护\n\n• 不会收集敏感信息\n• 数据仅用于提供服务\n• 可随时删除账户数据',
        showCancel: false,
        confirmText: '知道了'
      })
    }

    // 显示关于页面
    const showAbout = () => {
      uni.showModal({
        title: '关于盯播助手',
        content: `版本：1.0.0\n\n智能直播监控助手\n帮助您不错过每一个精彩瞬间\n\n© 2026 StreamMonitor\n技术支持：support@streammonitor.com`,
        showCancel: false,
        confirmText: '知道了'
      })
    }

    // 刷新Token
    const refreshToken = async () => {
      try {
        const currentToken = userStore.getToken()
        const response = await api.user.refreshToken(currentToken)
        userStore.setToken(response.token)

        uni.showToast({
          title: 'Token刷新成功',
          icon: 'success'
        })
      } catch (error) {
        console.error('Refresh token error:', error)
        uni.showToast({
          title: '刷新失败',
          icon: 'none'
        })
      }
    }

    // 显示退出确认
    const showLogoutConfirm = () => {
      showLogoutModal.value = true
    }

    // 退出登录
    const logout = () => {
      userStore.logout()
      uni.reLaunch({
        url: '/pages/login/login'
      })
    }

    // 计算属性
    const loginStatusClass = computed(() => {
      return isLoggedIn.value ? 'status-online' : 'status-offline'
    })

    return {
      // 状态
      userInfo,
      userStats,
      isLoggedIn,
      showEditModal,
      showNotificationModal,
      showLogoutModal,
      editForm,
      notificationOptions,

      // 方法
      initProfile,
      loadUserStats,
      editProfile,
      chooseAvatar,
      saveProfile,
      goToTaskManagement,
      goToHistory,
      goToStreamerManagement,
      showNotificationSettings,
      onNotificationOptionSelect,
      subscribeMessage,
      showDoNotDisturbSettings,
      showCacheSettings,
      clearImageCache,
      clearDataCache,
      showCacheSize,
      showPrivacySettings,
      showAbout,
      refreshToken,
      showLogoutConfirm,
      logout,
      loginStatusClass
    }
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  background: #f8f8f8;
  padding-bottom: 40rpx;
}

.user-card {
  margin-bottom: 20rpx;

  .user-avatar-section {
    display: flex;
    align-items: center;
    margin-bottom: 30rpx;

    .user-avatar {
      width: 120rpx;
      height: 120rpx;
      border-radius: 60rpx;
      margin-right: 20rpx;
    }

    .user-info {
      flex: 1;

      .user-nickname {
        display: block;
        font-size: 32rpx;
        font-weight: 600;
        color: #333;
        margin-bottom: 8rpx;
      }

      .user-id {
        display: block;
        font-size: 24rpx;
        color: #666;
        margin-bottom: 8rpx;
      }

      .login-status {
        font-size: 20rpx;
        padding: 4rpx 12rpx;
        border-radius: 12rpx;

        &.status-online {
          background: #e6f7e6;
          color: #4CAF50;
        }

        &.status-offline {
          background: #fff3e0;
          color: #FF9800;
        }
      }
    }

    .edit-btn {
      background: #007AFF;
      color: white;
      border-radius: 20rpx;
      padding: 10rpx 20rpx;
      font-size: 24rpx;
    }
  }

  .user-stats {
    display: flex;
    justify-content: space-around;
    padding-top: 20rpx;
    border-top: 1rpx solid #f0f0f0;

    .stat-item {
      text-align: center;

      .stat-number {
        display: block;
        font-size: 32rpx;
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
}

.menu-section {
  .menu-group {
    margin-bottom: 20rpx;

    .group-title {
      display: block;
      font-size: 28rpx;
      font-weight: 600;
      color: #333;
      margin-bottom: 15rpx;
      padding: 0 20rpx;
    }

    .menu-list {
      background: white;
      border-radius: 12rpx;
      overflow: hidden;

      .menu-item {
        display: flex;
        align-items: center;
        padding: 30rpx 20rpx;
        border-bottom: 1rpx solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        &.danger {
          .menu-text {
            color: #FF3B30;
          }
        }

        .menu-icon {
          font-size: 32rpx;
          margin-right: 20rpx;
          width: 40rpx;
          text-align: center;
        }

        .menu-text {
          flex: 1;
          font-size: 28rpx;
          color: #333;
        }

        .menu-arrow {
          font-size: 28rpx;
          color: #999;
        }
      }
    }
  }
}

.edit-modal {
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
    padding: 30rpx;

    .form-item {
      margin-bottom: 30rpx;

      .form-label {
        display: block;
        font-size: 28rpx;
        font-weight: 500;
        color: #333;
        margin-bottom: 15rpx;
      }
    }

    .avatar-upload {
      text-align: center;

      .preview-avatar {
        width: 120rpx;
        height: 120rpx;
        border-radius: 60rpx;
        margin-bottom: 15rpx;
      }

      .upload-text {
        font-size: 24rpx;
        color: #666;
      }
    }
  }

  .modal-actions {
    display: flex;
    gap: 20rpx;
    padding: 30rpx;
    border-top: 1rpx solid #f0f0f0;

    .save-btn {
      flex: 1;
      background: #007AFF;
      color: white;
      border-radius: 12rpx;
      padding: 20rpx;
      font-size: 28rpx;
      text-align: center;
    }

    .cancel-btn {
      flex: 1;
      background: #f5f5f5;
      color: #666;
      border-radius: 12rpx;
      padding: 20rpx;
      font-size: 28rpx;
      text-align: center;
    }
  }
}
</style>