<template>
  <view class="login-page">
    <!-- 背景图 -->
    <view class="login-bg">
      <image src="/static/login-bg.jpg" mode="aspectFill" class="bg-image" />
    </view>

    <!-- 登录卡片 -->
    <view class="login-card">
      <view class="logo-section">
        <image src="/static/logo.png" mode="aspectFit" class="logo" />
        <text class="app-name">盯播助手</text>
        <text class="app-desc">智能直播监控，不错过每一个精彩瞬间</text>
      </view>

      <view class="features-section">
        <view class="feature-item">
          <text class="feature-icon">🔴</text>
          <text class="feature-text">开播提醒</text>
        </view>
        <view class="feature-item">
          <text class="feature-icon">🛍️</text>
          <text class="feature-text">商品上架</text>
        </view>
        <view class="feature-item">
          <text class="feature-icon">🎯</text>
          <text class="feature-text">AI智能分析</text>
        </view>
      </view>

      <view class="login-section">
        <button
          class="wechat-login-btn"
          :loading="loading"
          :disabled="loading"
          @click="handleWechatLogin"
        >
          <text class="btn-icon">💬</text>
          <text class="btn-text">{{ loading ? '授权中...' : '微信授权登录' }}</text>
        </button>

        <view class="agreement-section">
          <text class="agreement-text">登录即表示同意</text>
          <text class="agreement-link" @click="showPrivacyPolicy">《隐私政策》</text>
          <text class="agreement-text">和</text>
          <text class="agreement-link" @click="showUserAgreement">《用户协议》</text>
        </view>
      </view>
    </view>

    <!-- 隐私政策弹窗 -->
    <u-modal
      v-model="showPrivacyModal"
      title="隐私政策"
      :content="privacyContent"
      :show-cancel-button="false"
      confirm-text="我知道了"
    />

    <!-- 用户协议弹窗 -->
    <u-modal
      v-model="showAgreementModal"
      title="用户协议"
      :content="agreementContent"
      :show-cancel-button="false"
      confirm-text="我知道了"
    />
  </view>
</template>

<script>
import { ref } from 'vue'
import { useUserStore } from '../../stores/user'
import api from '../../services/api'

export default {
  setup() {
    const userStore = useUserStore()
    const loading = ref(false)
    const showPrivacyModal = ref(false)
    const showAgreementModal = ref(false)

    // 隐私政策内容
    const privacyContent = ref(`
我们非常重视您的隐私保护，本隐私政策说明我们如何收集、使用和保护您的个人信息：

1. 信息收集
- 微信基本信息：昵称、头像等公开信息
- 设备信息：设备型号、操作系统版本等

2. 信息使用
- 提供直播监控服务
- 发送重要通知消息
- 改善用户体验

3. 信息保护
- 采用加密技术保护数据传输
- 严格限制内部人员访问权限
- 不会向第三方泄露您的个人信息

4. 联系我们
如有疑问，请联系：support@streammonitor.com
    `.trim())

    // 用户协议内容
    const agreementContent = ref(`
欢迎使用盯播助手服务，请仔细阅读以下条款：

1. 服务说明
- 提供直播内容监控服务
- 支持多平台主播监控
- 提供AI智能分析功能

2. 用户责任
- 遵守相关法律法规
- 不得滥用监控功能
- 保护账号安全

3. 服务限制
- 禁止商业性使用
- 禁止反向工程
- 保留服务调整权利

4. 免责声明
- 服务按现状提供
- 不承担间接损失
- 保留最终解释权
    `.trim())

    // 微信授权登录
    const handleWechatLogin = async () => {
      if (loading.value) return

      loading.value = true

      try {
        // 1. 获取微信code
        const wxLoginRes = await new Promise((resolve, reject) => {
          uni.login({
            provider: 'weixin',
            success: resolve,
            fail: reject
          })
        })

        // 2. 获取用户信息
        const wxUserInfoRes = await new Promise((resolve, reject) => {
          uni.getUserProfile({
            desc: '获取用户信息用于登录',
            success: resolve,
            fail: reject
          })
        })

        // 3. 调用后端登录接口
        const loginData = {
          code: wxLoginRes.code,
          nickname: wxUserInfoRes.userInfo.nickName,
          avatarUrl: wxUserInfoRes.userInfo.avatarUrl,
          gender: wxUserInfoRes.userInfo.gender
        }

        const response = await api.user.wechatLogin(loginData)

        // 4. 保存用户信息和token
        userStore.setToken(response.token)
        userStore.setUserInfo(response.user)

        // 5. 请求订阅消息权限
        await requestSubscribeMessage()

        // 6. 跳转到首页
        uni.switchTab({
          url: '/pages/index/index'
        })

      } catch (error) {
        console.error('Login error:', error)
        uni.showToast({
          title: error.message || '登录失败，请重试',
          icon: 'none'
        })
      } finally {
        loading.value = false
      }
    }

    // 请求订阅消息权限
    const requestSubscribeMessage = async () => {
      try {
        // 微信订阅消息模板ID需要后端配置
        const tmplIds = [
          'LIVE_START_TEMPLATE_ID',    // 开播提醒
          'PRODUCT_LAUNCH_TEMPLATE_ID', // 商品上架
          'KEYWORD_MATCH_TEMPLATE_ID'   // 关键词匹配
        ]

        await new Promise((resolve, reject) => {
          uni.requestSubscribeMessage({
            tmplIds,
            success: (res) => {
              console.log('Subscribe message success:', res)
              resolve(res)
            },
            fail: (err) => {
              console.log('Subscribe message fail:', err)
              // 不强制要求订阅，继续流程
              resolve(err)
            }
          })
        })
      } catch (error) {
        console.log('Subscribe message error:', error)
      }
    }

    // 显示隐私政策
    const showPrivacyPolicy = () => {
      showPrivacyModal.value = true
    }

    // 显示用户协议
    const showUserAgreement = () => {
      showAgreementModal.value = true
    }

    return {
      loading,
      showPrivacyModal,
      showAgreementModal,
      privacyContent,
      agreementContent,
      handleWechatLogin,
      showPrivacyPolicy,
      showUserAgreement
    }
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.login-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;

  .bg-image {
    width: 100%;
    height: 100%;
    opacity: 0.3;
  }
}

.login-card {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 600rpx;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 24rpx;
  padding: 60rpx 40rpx;
  box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

.logo-section {
  text-align: center;
  margin-bottom: 60rpx;

  .logo {
    width: 120rpx;
    height: 120rpx;
    margin-bottom: 20rpx;
  }

  .app-name {
    display: block;
    font-size: 48rpx;
    font-weight: bold;
    color: #333;
    margin-bottom: 10rpx;
  }

  .app-desc {
    display: block;
    font-size: 28rpx;
    color: #666;
    line-height: 1.4;
  }
}

.features-section {
  display: flex;
  justify-content: space-around;
  margin-bottom: 60rpx;

  .feature-item {
    text-align: center;

    .feature-icon {
      display: block;
      font-size: 48rpx;
      margin-bottom: 10rpx;
    }

    .feature-text {
      font-size: 24rpx;
      color: #666;
    }
  }
}

.login-section {
  .wechat-login-btn {
    width: 100%;
    height: 88rpx;
    background: linear-gradient(135deg, #07C160, #05A84F);
    border-radius: 44rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 30rpx;

    .btn-icon {
      font-size: 32rpx;
      margin-right: 10rpx;
    }

    .btn-text {
      color: white;
      font-size: 32rpx;
      font-weight: 500;
    }
  }
}

.agreement-section {
  text-align: center;
  font-size: 24rpx;

  .agreement-text {
    color: #999;
  }

  .agreement-link {
    color: #007AFF;
    text-decoration: underline;
  }
}
</style>