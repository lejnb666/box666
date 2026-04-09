<template>
  <view class="task-add-page">
    <view class="form-section">
      <!-- 主播信息 -->
      <view class="form-card card">
        <text class="section-title">主播信息</text>

        <view class="form-item">
          <text class="form-label">平台选择 *</text>
          <view class="platform-selector">
            <view
              v-for="platform in platforms"
              :key="platform.value"
              class="platform-option"
              :class="{ active: form.platform === platform.value }"
              @click="selectPlatform(platform.value)"
            >
              <text class="platform-icon">{{ platform.icon }}</text>
              <text class="platform-name">{{ platform.label }}</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">房间号 *</text>
          <u-input
            v-model="form.roomId"
            placeholder="请输入房间号"
            :border="true"
            @blur="validateRoomId"
          />
        </view>

        <view class="form-item">
          <text class="form-label">主播名称</text>
          <u-input
            v-model="form.streamerName"
            placeholder="请输入主播名称（可选）"
            :border="true"
          />
        </view>
      </view>

      <!-- 任务类型 -->
      <view class="form-card card">
        <text class="section-title">监控类型</text>

        <view class="form-item">
          <view class="task-type-selector">
            <view
              v-for="type in taskTypes"
              :key="type.value"
              class="task-type-option"
              :class="{ active: form.taskType === type.value }"
              @click="selectTaskType(type.value)"
            >
              <text class="type-icon">{{ type.icon }}</text>
              <text class="type-name">{{ type.label }}</text>
            </view>
          </view>
        </view>

        <!-- 关键词设置（仅关键词匹配类型显示） -->
        <view v-if="form.taskType === 'keyword_match'" class="form-item">
          <text class="form-label">关键词设置 *</text>
          <view class="keywords-section">
            <view class="keywords-input">
              <u-input
                v-model="keywordInput"
                placeholder="输入关键词后按回车添加"
                :border="true"
                @confirm="addKeyword"
              />
            </view>
            <view class="keywords-list">
              <text
                v-for="(keyword, index) in keywords"
                :key="index"
                class="keyword-tag"
                @click="removeKeyword(index)"
              >
                {{ keyword }} ✕
              </text>
            </view>
          </view>
        </view>
      </view>

      <!-- 通知设置 -->
      <view class="form-card card">
        <text class="section-title">通知设置</text>

        <view class="form-item">
          <view class="switch-item">
            <text class="switch-label">AI智能分析</text>
            <text class="switch-desc">启用后将使用AI进行深度语义分析</text>
            <u-switch v-model="form.aiAnalysis" />
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">通知方式</text>
          <view class="notification-methods">
            <view
              v-for="method in notificationMethods"
              :key="method.value"
              class="method-option"
              :class="{ active: form.notificationMethods.includes(method.value) }"
              @click="toggleNotificationMethod(method.value)"
            >
              <text class="method-name">{{ method.label }}</text>
            </view>
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">免打扰时间</text>
          <view class="disturb-time">
            <u-input
              v-model="form.doNotDisturbStart"
              placeholder="开始时间"
              :border="true"
              type="text"
              @focus="showTimePicker('start')"
            />
            <text class="time-separator">至</text>
            <u-input
              v-model="form.doNotDisturbEnd"
              placeholder="结束时间"
              :border="true"
              type="text"
              @focus="showTimePicker('end')"
            />
          </view>
        </view>
      </view>

      <!-- 高级设置 -->
      <view class="form-card card">
        <text class="section-title">高级设置</text>

        <view class="form-item">
          <view class="switch-item">
            <text class="switch-label">启用调试模式</text>
            <text class="switch-desc">记录详细的监控日志用于问题排查</text>
            <u-switch v-model="form.debugMode" />
          </view>
        </view>

        <view class="form-item">
          <text class="form-label">监控频率</text>
          <u-slider
            v-model="form.monitorInterval"
            min="30"
            max="300"
            step="30"
            :show-tooltip="true"
            :tooltip-text="form.monitorInterval + '秒'"
          />
        </view>
      </view>
    </view>

    <!-- 操作按钮 -->
    <view class="form-actions">
      <button class="save-btn" :loading="saving" @click="saveTask">
        <text class="btn-text">{{ isEdit ? '更新任务' : '创建任务' }}</text>
      </button>
      <button class="cancel-btn" @click="goBack">
        <text class="btn-text">取消</text>
      </button>
    </view>

    <!-- 时间选择器 -->
    <u-picker
      v-model="showTimeModal"
      mode="time"
      :default-time="selectedTime"
      @confirm="onTimeConfirm"
    />
  </view>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useTaskStore } from '../../stores/task'
import api from '../../services/api'

export default {
  setup() {
    const taskStore = useTaskStore()

    // 页面参数
    const query = uni.getCurrentPages().pop().$page.options
    const isEdit = query.mode === 'edit'
    const taskId = query.id

    // 表单数据
    const form = ref({
      platform: '',
      roomId: '',
      streamerName: '',
      taskType: '',
      keywords: [],
      aiAnalysis: false,
      notificationMethods: ['wechat'],
      doNotDisturbStart: '',
      doNotDisturbEnd: '',
      debugMode: false,
      monitorInterval: 60
    })

    // 其他状态
    const keywordInput = ref('')
    const keywords = ref([])
    const saving = ref(false)
    const showTimeModal = ref(false)
    const selectedTime = ref('')
    const timePickerType = ref('start')

    // 选项数据
    const platforms = taskStore.platforms
    const taskTypes = taskStore.taskTypes
    const notificationMethods = [
      { value: 'wechat', label: '微信订阅消息' },
      { value: 'sms', label: '短信通知' },
      { value: 'email', label: '邮件通知' }
    ]

    // 页面加载
    onMounted(() => {
      if (isEdit && taskId) {
        loadTaskDetail()
      }
    })

    // 加载任务详情（编辑模式）
    const loadTaskDetail = async () => {
      try {
        // 调用API获取任务详情
        const response = await api.task.getTaskList({ id: taskId })
        const taskData = response.records?.[0] || response.data?.[0]

        if (taskData) {
          form.value = {
            platform: taskData.platform || '',
            roomId: taskData.roomId || '',
            streamerName: taskData.streamerName || '',
            taskType: taskData.taskType || '',
            keywords: taskData.keywords ? JSON.parse(taskData.keywords) : [],
            aiAnalysis: taskData.aiAnalysis || false,
            notificationMethods: taskData.notificationMethods || ['wechat'],
            doNotDisturbStart: taskData.doNotDisturbStart || '',
            doNotDisturbEnd: taskData.doNotDisturbEnd || '',
            debugMode: taskData.debugMode || false,
            monitorInterval: taskData.monitorInterval || 60
          }
          keywords.value = form.value.keywords
        }
      } catch (error) {
        console.error('Load task detail error:', error)
        uni.showToast({
          title: '加载失败',
          icon: 'none'
        })
      }
    }

    // 选择平台
    const selectPlatform = (platform) => {
      form.value.platform = platform
    }

    // 选择任务类型
    const selectTaskType = (type) => {
      form.value.taskType = type
      // 清空关键词如果切换了类型
      if (type !== 'keyword_match') {
        keywords.value = []
        form.value.keywords = []
      }
    }

    // 添加关键词
    const addKeyword = () => {
      const keyword = keywordInput.value.trim()
      if (keyword && !keywords.value.includes(keyword)) {
        keywords.value.push(keyword)
        form.value.keywords = keywords.value
        keywordInput.value = ''
      }
    }

    // 移除关键词
    const removeKeyword = (index) => {
      keywords.value.splice(index, 1)
      form.value.keywords = keywords.value
    }

    // 切换通知方式
    const toggleNotificationMethod = (method) => {
      const methods = form.value.notificationMethods
      const index = methods.indexOf(method)

      if (index === -1) {
        methods.push(method)
      } else {
        methods.splice(index, 1)
      }
    }

    // 显示时间选择器
    const showTimePicker = (type) => {
      timePickerType.value = type
      selectedTime.value = form.value[type === 'start' ? 'doNotDisturbStart' : 'doNotDisturbEnd']
      showTimeModal.value = true
    }

    // 时间选择确认
    const onTimeConfirm = (time) => {
      if (timePickerType.value === 'start') {
        form.value.doNotDisturbStart = time
      } else {
        form.value.doNotDisturbEnd = time
      }
    }

    // 验证房间号
    const validateRoomId = () => {
      if (form.value.roomId && form.value.platform) {
        // 这里可以添加房间号验证逻辑
        // 例如调用API验证房间号是否存在
      }
    }

    // 保存任务
    const saveTask = async () => {
      // 表单验证
      if (!validateForm()) {
        return
      }

      saving.value = true

      try {
        // 如果是创建新任务且选择了微信通知，需要请求订阅消息授权
        if (!isEdit && form.value.notificationMethods.includes('wechat')) {
          const authSuccess = await requestSubscribeMessageAuth()
          if (!authSuccess) {
            uni.showToast({
              title: '需要订阅消息授权才能创建任务',
              icon: 'none'
            })
            saving.value = false
            return
          }
        }

        const taskData = {
          platform: form.value.platform,
          roomId: form.value.roomId,
          streamerName: form.value.streamerName,
          taskType: form.value.taskType,
          keywords: form.value.keywords.length > 0 ? JSON.stringify(form.value.keywords) : '',
          aiAnalysis: form.value.aiAnalysis,
          notificationMethods: JSON.stringify(form.value.notificationMethods),
          doNotDisturbStart: form.value.doNotDisturbStart,
          doNotDisturbEnd: form.value.doNotDisturbEnd,
          monitorInterval: form.value.monitorInterval,
          debugMode: form.value.debugMode
        }

        if (isEdit) {
          await api.task.updateTask(taskId, taskData)
          uni.showToast({
            title: '更新成功',
            icon: 'success'
          })
        } else {
          const response = await api.task.createTask(taskData)
          taskStore.addTask(response)
          uni.showToast({
            title: '创建成功',
            icon: 'success'
          })
        }

        // 返回上一页
        setTimeout(() => {
          uni.navigateBack()
        }, 1000)

      } catch (error) {
        console.error('Save task error:', error)
        uni.showToast({
          title: isEdit ? '更新失败' : '创建失败',
          icon: 'none'
        })
      } finally {
        saving.value = false
      }
    }

    // 表单验证
    const validateForm = () => {
      if (!form.value.platform) {
        uni.showToast({ title: '请选择平台', icon: 'none' })
        return false
      }

      if (!form.value.roomId) {
        uni.showToast({ title: '请输入房间号', icon: 'none' })
        return false
      }

      if (!form.value.taskType) {
        uni.showToast({ title: '请选择监控类型', icon: 'none' })
        return false
      }

      if (form.value.taskType === 'keyword_match' && keywords.value.length === 0) {
        uni.showToast({ title: '请至少添加一个关键词', icon: 'none' })
        return false
      }

      return true
    }

    // 生成主播配置ID（临时方法）
    const generateStreamerConfigId = () => {
      // 这里应该调用后端API创建或获取主播配置
      return Date.now()
    }

    // 请求订阅消息授权
    const requestSubscribeMessageAuth = async () => {
      try {
        // 根据任务类型确定需要订阅的模板
        const templateIds = []

        switch (form.value.taskType) {
          case 'live_start':
            templateIds.push('LIVE_START_TEMPLATE_ID')
            break
          case 'product_launch':
            templateIds.push('PRODUCT_LAUNCH_TEMPLATE_ID')
            break
          case 'keyword_match':
            templateIds.push('KEYWORD_MATCH_TEMPLATE_ID')
            break
          default:
            templateIds.push('LIVE_START_TEMPLATE_ID')
        }

        // 显示授权说明
        const authResult = await new Promise((resolve) => {
          uni.showModal({
            title: '订阅消息授权',
            content: `为了及时收到${getTaskTypeLabel(form.value.taskType)}通知，需要您授权订阅消息。授权后，当监控到相关内容时会及时推送通知给您。`,
            confirmText: '去授权',
            cancelText: '取消',
            success: (res) => {
              if (res.confirm) {
                // 用户点击确认，开始请求订阅
                uni.requestSubscribeMessage({
                  tmplIds: templateIds,
                  success: (subscribeRes) => {
                    console.log('订阅消息授权成功:', subscribeRes)
                    // 检查授权结果
                    const allGranted = templateIds.every(id =>
                      subscribeRes[id] === 'accept'
                    )
                    resolve(allGranted)
                  },
                  fail: (err) => {
                    console.log('订阅消息授权失败:', err)
                    resolve(false)
                  }
                })
              } else {
                resolve(false)
              }
            }
          })
        })

        if (authResult) {
          uni.showToast({
            title: '授权成功',
            icon: 'success'
          })
          return true
        } else {
          // 授权失败，显示提示
          uni.showModal({
            title: '授权失败',
            content: '订阅消息授权失败，您将无法收到微信通知。是否继续创建任务？',
            confirmText: '继续创建',
            cancelText: '重新授权',
            success: (res) => {
              if (res.confirm) {
                // 用户选择继续创建，但不启用微信通知
                form.value.notificationMethods = form.value.notificationMethods.filter(
                  method => method !== 'wechat'
                )
              }
            }
          })
          return false
        }

      } catch (error) {
        console.error('订阅消息授权异常:', error)
        return false
      }
    }

    // 获取任务类型标签
    const getTaskTypeLabel = (type) => {
      const typeMap = {
        live_start: '开播提醒',
        product_launch: '商品上架',
        keyword_match: '关键词匹配',
        lottery: '抽奖活动',
        discount: '降价促销'
      }
      return typeMap[type] || '直播监控'
    }

    // 返回上一页
    const goBack = () => {
      uni.navigateBack()
    }

    return {
      // 状态
      isEdit,
      taskId,
      form,
      keywordInput,
      keywords,
      saving,
      showTimeModal,
      selectedTime,

      // 选项数据
      platforms,
      taskTypes,
      notificationMethods,

      // 方法
      loadTaskDetail,
      selectPlatform,
      selectTaskType,
      addKeyword,
      removeKeyword,
      toggleNotificationMethod,
      showTimePicker,
      onTimeConfirm,
      validateRoomId,
      saveTask,
      goBack
    }
  }
}
</script>

<style lang="scss" scoped>
.task-add-page {
  min-height: 100vh;
  background: #f8f8f8;
  padding-bottom: 120rpx;
}

.form-section {
  padding: 20rpx;
}

.form-card {
  margin-bottom: 20rpx;

  .section-title {
    font-size: 32rpx;
    font-weight: 600;
    color: #333;
    margin-bottom: 30rpx;
  }
}

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

.platform-selector {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15rpx;

  .platform-option {
    display: flex;
    align-items: center;
    padding: 20rpx;
    border: 2rpx solid #e5e5e5;
    border-radius: 12rpx;
    background: white;

    &.active {
      border-color: #007AFF;
      background: #f0f8ff;
    }

    .platform-icon {
      font-size: 32rpx;
      margin-right: 10rpx;
    }

    .platform-name {
      font-size: 24rpx;
      color: #333;
    }
  }
}

.task-type-selector {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15rpx;

  .task-type-option {
    text-align: center;
    padding: 30rpx 20rpx;
    border: 2rpx solid #e5e5e5;
    border-radius: 12rpx;
    background: white;

    &.active {
      border-color: #007AFF;
      background: #f0f8ff;
    }

    .type-icon {
      display: block;
      font-size: 40rpx;
      margin-bottom: 10rpx;
    }

    .type-name {
      font-size: 22rpx;
      color: #333;
    }
  }
}

.keywords-section {
  .keywords-input {
    margin-bottom: 20rpx;
  }

  .keywords-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10rpx;

    .keyword-tag {
      background: #007AFF;
      color: white;
      font-size: 20rpx;
      padding: 8rpx 16rpx;
      border-radius: 16rpx;
    }
  }
}

.switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .switch-label {
    font-size: 28rpx;
    color: #333;
    flex: 1;
  }

  .switch-desc {
    font-size: 20rpx;
    color: #666;
    margin-right: 20rpx;
  }
}

.notification-methods {
  display: flex;
  flex-wrap: wrap;
  gap: 15rpx;

  .method-option {
    padding: 12rpx 24rpx;
    border: 2rpx solid #e5e5e5;
    border-radius: 20rpx;
    background: white;

    &.active {
      border-color: #007AFF;
      background: #f0f8ff;
    }

    .method-name {
      font-size: 24rpx;
      color: #333;
    }
  }
}

.disturb-time {
  display: flex;
  align-items: center;
  gap: 15rpx;

  .time-separator {
    font-size: 24rpx;
    color: #666;
  }
}

.form-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  padding: 20rpx;
  border-top: 1rpx solid #e5e5e5;
  display: flex;
  gap: 20rpx;

  .save-btn {
    flex: 2;
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
</style>