import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 用户状态
  const token = ref('')
  const userInfo = ref(null)
  const isLoggedIn = ref(false)

  // 获取token
  const getToken = () => {
    if (token.value) {
      return token.value
    }
    // 从本地存储获取
    const stored = uni.getStorageSync('token')
    if (stored) {
      token.value = stored
      return stored
    }
    return null
  }

  // 设置用户信息
  const setUserInfo = (user) => {
    userInfo.value = user
    isLoggedIn.value = !!user
    if (user) {
      uni.setStorageSync('userInfo', user)
    } else {
      uni.removeStorageSync('userInfo')
    }
  }

  // 设置token
  const setToken = (newToken) => {
    token.value = newToken
    isLoggedIn.value = !!newToken
    if (newToken) {
      uni.setStorageSync('token', newToken)
    } else {
      uni.removeStorageSync('token')
    }
  }

  // 初始化用户状态
  const initUser = () => {
    const storedUserInfo = uni.getStorageSync('userInfo')
    const storedToken = uni.getStorageSync('token')

    if (storedUserInfo && storedToken) {
      userInfo.value = storedUserInfo
      token.value = storedToken
      isLoggedIn.value = true
    }
  }

  // 退出登录
  const logout = () => {
    userInfo.value = null
    token.value = ''
    isLoggedIn.value = false
    uni.removeStorageSync('userInfo')
    uni.removeStorageSync('token')
  }

  // 检查登录状态
  const checkLogin = () => {
    if (!isLoggedIn.value || !token.value) {
      uni.redirectTo({
        url: '/pages/login/login'
      })
      return false
    }
    return true
  }

  return {
    // 状态
    token,
    userInfo,
    isLoggedIn,

    // 方法
    getToken,
    setUserInfo,
    setToken,
    initUser,
    logout,
    checkLogin
  }
})