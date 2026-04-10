// index.js
Page({
  onLoad(options) {
    try {
      console.log('Page loaded', options)
    } catch (error) {
      console.warn('Page load error:', error)
    }
  },
  onShow() {
    try {
      console.log('Page shown')
    } catch (error) {
      console.warn('Page show error:', error)
    }
  },
  onReady() {
    try {
      console.log('Page ready')
    } catch (error) {
      console.warn('Page ready error:', error)
    }
  },
  onHide() {
    try {
      console.log('Page hidden')
    } catch (error) {
      console.warn('Page hide error:', error)
    }
  },
  onUnload() {
    try {
      console.log('Page unloaded')
    } catch (error) {
      console.warn('Page unload error:', error)
    }
  }
})
