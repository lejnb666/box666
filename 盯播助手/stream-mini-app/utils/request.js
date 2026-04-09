// 请求封装
const BASE_URL = 'http://localhost:8080' // 后端API地址

class Request {
  constructor() {
    this.baseUrl = BASE_URL
    this.isRefreshing = false
    this.requestQueue = []
  }

  // 请求拦截器
  async request(options) {
    const { url, method = 'GET', data = {}, header = {} } = options

    // 添加token
    const token = uni.getStorageSync('token')
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    // 显示loading
    if (options.showLoading !== false) {
      uni.showLoading({
        title: '加载中...',
        mask: true
      })
    }

    try {
      const response = await new Promise((resolve, reject) => {
        uni.request({
          url: this.baseUrl + url,
          method,
          data,
          header,
          success: (res) => {
            resolve(res)
          },
          fail: (err) => {
            reject(err)
          }
        })
      })

      // 隐藏loading
      if (options.showLoading !== false) {
        uni.hideLoading()
      }

      // 处理响应
      if (response.statusCode === 200) {
        const resData = response.data
        // 根据后端Result格式处理
        if (resData.code === 200 || resData.success) {
          return resData.data || resData
        } else if (resData.code === 401) {
          // Token过期，尝试刷新
          return this.handleTokenExpired(options)
        } else {
          uni.showToast({
            title: resData.message || '请求失败',
            icon: 'none'
          })
          throw new Error(resData.message || '请求失败')
        }
      } else if (response.statusCode === 401) {
        // Token过期，尝试刷新
        return this.handleTokenExpired(options)
      } else {
        uni.showToast({
          title: response.data?.message || '服务器错误',
          icon: 'none'
        })
        throw new Error(response.data?.message || '服务器错误')
      }
    } catch (error) {
      // 隐藏loading
      if (options.showLoading !== false) {
        uni.hideLoading()
      }

      console.error('Request error:', error)
      throw error
    }
  }

  // 处理Token过期
  async handleTokenExpired(originalRequest) {
    const refreshToken = uni.getStorageSync('refreshToken')

    if (!refreshToken) {
      // 没有refresh token，直接跳转到登录页
      this.redirectToLogin()
      throw new Error('登录已过期，请重新登录')
    }

    // 如果正在刷新token，将请求加入队列
    if (this.isRefreshing) {
      return new Promise((resolve, reject) => {
        this.requestQueue.push({
          request: originalRequest,
          resolve,
          reject
        })
      })
    }

    this.isRefreshing = true

    try {
      // 尝试刷新token
      const newTokenData = await this.refreshToken(refreshToken)

      // 保存新token
      uni.setStorageSync('token', newTokenData.token)
      if (newTokenData.refreshToken) {
        uni.setStorageSync('refreshToken', newTokenData.refreshToken)
      }

      // 重新发起原请求
      const result = await this.request(originalRequest)

      // 处理队列中的请求
      this.processRequestQueue(null, newTokenData.token)

      return result
    } catch (error) {
      // 刷新失败，清除token并跳转到登录页
      this.clearTokens()
      this.processRequestQueue(error)
      this.redirectToLogin()
      throw new Error('登录已过期，请重新登录')
    } finally {
      this.isRefreshing = false
    }
  }

  // 刷新Token
  async refreshToken(refreshToken) {
    try {
      const response = await new Promise((resolve, reject) => {
        uni.request({
          url: this.baseUrl + '/user/refresh-token',
          method: 'POST',
          header: {
            'Refresh-Token': refreshToken,
            'Content-Type': 'application/json'
          },
          success: (res) => {
            resolve(res)
          },
          fail: (err) => {
            reject(err)
          }
        })
      })

      if (response.statusCode === 200) {
        const resData = response.data
        if (resData.code === 200 || resData.success) {
          return resData.data || resData
        } else {
          throw new Error(resData.message || '刷新Token失败')
        }
      } else {
        throw new Error('刷新Token失败')
      }
    } catch (error) {
      console.error('Refresh token error:', error)
      throw error
    }
  }

  // 处理请求队列
  processRequestQueue(error, newToken = null) {
    this.requestQueue.forEach(({ request, resolve, reject }) => {
      if (error) {
        reject(error)
      } else {
        // 重新发起请求
        if (newToken) {
          request.header = request.header || {}
          request.header['Authorization'] = `Bearer ${newToken}`
        }
        this.request(request).then(resolve).catch(reject)
      }
    })

    // 清空队列
    this.requestQueue = []
  }

  // 清除Token
  clearTokens() {
    uni.removeStorageSync('token')
    uni.removeStorageSync('refreshToken')
  }

  // 跳转到登录页
  redirectToLogin() {
    this.clearTokens()
    uni.redirectTo({
      url: '/pages/login/login'
    })
  }

  // GET请求
  get(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'GET',
      data,
      ...options
    })
  }

  // POST请求
  post(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'POST',
      data,
      header: {
        'Content-Type': 'application/json'
      },
      ...options
    })
  }

  // PUT请求
  put(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'PUT',
      data,
      header: {
        'Content-Type': 'application/json'
      },
      ...options
    })
  }

  // DELETE请求
  delete(url, data = {}, options = {}) {
    return this.request({
      url,
      method: 'DELETE',
      data,
      ...options
    })
  }
}

export default new Request()