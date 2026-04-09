import { createSSRApp } from "vue"
import { createPinia } from 'pinia'
import uView from "uview-ui"

export function createApp() {
  const app = createSSRApp({
    onLaunch: function() {
      console.log('App Launch')
    },
    onShow: function() {
      console.log('App Show')
    },
    onHide: function() {
      console.log('App Hide')
    }
  })

  app.use(createPinia())
  app.use(uView)

  return {
    app
  }
}