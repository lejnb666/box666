import request from '../utils/request'

// API接口封装
export default {
  // 用户相关
  user: {
    // 微信登录
    wechatLogin: (data) => request.post('/user/login', data),

    // 获取用户信息
    getUserProfile: () => request.get('/user/profile'),

    // 更新用户信息
    updateUserProfile: (data) => request.put('/user/profile', data),

    // 退出登录
    logout: () => request.post('/user/logout'),

    // 获取用户统计
    getUserStats: () => request.get('/user/stats'),

    // 刷新Token
    refreshToken: (token) => request.post('/user/refresh-token', {}, {
      header: {
        'Refresh-Token': token
      },
      showLoading: false // 刷新token时不要显示loading
    })
  },

  // 监控任务相关
  task: {
    // 获取任务列表
    getTaskList: (params) => request.get('/tasks', params),

    // 创建任务
    createTask: (data) => request.post('/tasks', data),

    // 更新任务
    updateTask: (id, data) => request.put(`/tasks/${id}`, data),

    // 删除任务
    deleteTask: (id) => request.delete(`/tasks/${id}`),

    // 启动任务
    startTask: (id) => request.post(`/tasks/${id}/start`),

    // 停止任务
    stopTask: (id) => request.post(`/tasks/${id}/stop`)
  },

  // 主播配置相关
  streamer: {
    // 获取主播配置列表
    getStreamerList: (params) => request.get('/streamers', params),

    // 创建主播配置
    createStreamer: (data) => request.post('/streamers', data),

    // 更新主播配置
    updateStreamer: (id, data) => request.put(`/streamers/${id}`, data),

    // 删除主播配置
    deleteStreamer: (id) => request.delete(`/streamers/${id}`),

    // 获取热门主播列表
    getHotList: (params) => request.get('/streamers/hot', params)
  },

  // 推送历史相关
  history: {
    // 获取推送历史
    getPushHistory: (params) => request.get('/push-history', params),

    // 标记为已读
    markAsRead: (id) => request.post(`/push-history/${id}/read`),

    // 删除历史记录
    deleteHistory: (id) => request.delete(`/push-history/${id}`)
  },

  // AI分析相关
  ai: {
    // 分析弹幕
    analyzeBarrages: (data) => request.post('/api/v1/ai/analyze', data)
  },

  // 爬虫相关
  crawler: {
    // 启动爬虫
    startCrawler: (data) => request.post('/api/v1/crawler/start', data),

    // 停止爬虫
    stopCrawler: (data) => request.post('/api/v1/crawler/stop', data),

    // 获取爬虫状态
    getCrawlerStatus: () => request.get('/api/v1/crawler/status')
  }
}