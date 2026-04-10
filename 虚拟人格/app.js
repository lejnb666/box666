// app.js
App({
  onLaunch(options) {
    try {
      console.log('App Launch', options)
    } catch (error) {
      console.warn('App Launch Error:', error)
    }
  },
  onShow(options) {
    try {
      console.log('App Show', options)
    } catch (error) {
      console.warn('App Show Error:', error)
    }
  },
  onHide() {
    try {
      console.log('App Hide')
    } catch (error) {
      console.warn('App Hide Error:', error)
    }
  },
  onError(error) {
    console.error('App Error:', error)
  }
})
