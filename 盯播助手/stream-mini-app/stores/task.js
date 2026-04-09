import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useTaskStore = defineStore('task', () => {
  // 任务列表
  const tasks = ref([])
  const totalTasks = ref(0)
  const activeTasks = ref(0)

  // 平台选项
  const platforms = [
    { value: 'bilibili', label: '哔哩哔哩', icon: '🎬' },
    { value: 'douyu', label: '斗鱼直播', icon: '🐟' },
    { value: 'huya', label: '虎牙直播', icon: '🐯' },
    { value: 'douyin', label: '抖音直播', icon: '🎵' }
  ]

  // 任务类型选项
  const taskTypes = [
    { value: 'live_start', label: '开播提醒', icon: '🔴' },
    { value: 'product_launch', label: '商品上架', icon: '🛍️' },
    { value: 'keyword_match', label: '关键词匹配', icon: '🔍' }
  ]

  // 设置任务列表
  const setTasks = (taskList) => {
    tasks.value = taskList
    totalTasks.value = taskList.length
    activeTasks.value = taskList.filter(task => task.status === 1).length
  }

  // 添加任务
  const addTask = (task) => {
    tasks.value.unshift(task)
    totalTasks.value = tasks.value.length
    if (task.status === 1) {
      activeTasks.value++
    }
  }

  // 更新任务
  const updateTask = (taskId, updates) => {
    const index = tasks.value.findIndex(task => task.id === taskId)
    if (index !== -1) {
      const oldStatus = tasks.value[index].status
      tasks.value[index] = { ...tasks.value[index], ...updates }

      // 更新活跃任务计数
      if (oldStatus === 1 && updates.status !== 1) {
        activeTasks.value--
      } else if (oldStatus !== 1 && updates.status === 1) {
        activeTasks.value++
      }
    }
  }

  // 删除任务
  const deleteTask = (taskId) => {
    const index = tasks.value.findIndex(task => task.id === taskId)
    if (index !== -1) {
      const task = tasks.value[index]
      if (task.status === 1) {
        activeTasks.value--
      }
      tasks.value.splice(index, 1)
      totalTasks.value = tasks.value.length
    }
  }

  // 切换任务状态
  const toggleTaskStatus = (taskId) => {
    const task = tasks.value.find(task => task.id === taskId)
    if (task) {
      const newStatus = task.status === 1 ? 0 : 1
      updateTask(taskId, { status: newStatus })
    }
  }

  // 获取平台标签
  const getPlatformLabel = (platform) => {
    const platformObj = platforms.find(p => p.value === platform)
    return platformObj ? platformObj.label : platform
  }

  // 获取任务类型标签
  const getTaskTypeLabel = (type) => {
    const typeObj = taskTypes.find(t => t.value === type)
    return typeObj ? typeObj.label : type
  }

  return {
    // 状态
    tasks,
    totalTasks,
    activeTasks,
    platforms,
    taskTypes,

    // 方法
    setTasks,
    addTask,
    updateTask,
    deleteTask,
    toggleTaskStatus,
    getPlatformLabel,
    getTaskTypeLabel
  }
})