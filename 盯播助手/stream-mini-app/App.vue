<template>
  <App>
    <uni-tabbar></uni-tabbar>
  </App>
</template>

<script>
export default {
  onLaunch() {
    console.log('App Launch')
  },
  onShow() {
    console.log('App Show')
  },
  onHide() {
    console.log('App Hide')
  }
}
</script>

<style lang="scss">
/* 全局样式 */
@import "uview-ui/index.scss";

/* 全局变量 */
:root {
  --primary-color: #007AFF;
  --success-color: #4cd964;
  --warning-color: #f0ad4e;
  --error-color: #dd524d;
  --text-primary: #333333;
  --text-secondary: #666666;
  --text-light: #999999;
  --bg-primary: #ffffff;
  --bg-secondary: #f8f8f8;
  --border-color: #e5e5e5;
}

/* 通用样式 */
.page {
  min-height: 100vh;
  background-color: var(--bg-secondary);
}

.container {
  padding: 20rpx;
}

.card {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.btn-primary {
  background: var(--primary-color);
  color: white;
  border-radius: 8rpx;
  padding: 20rpx 40rpx;
  text-align: center;
  font-size: 28rpx;
  font-weight: 500;
}

.btn-disabled {
  background: #cccccc;
  color: #666666;
}

/* 文本样式 */
.text-primary {
  color: var(--text-primary);
  font-size: 32rpx;
  font-weight: 600;
}

.text-secondary {
  color: var(--text-secondary);
  font-size: 28rpx;
}

.text-light {
  color: var(--text-light);
  font-size: 24rpx;
}

/* 间距 */
.mt-20 {
  margin-top: 20rpx;
}

.mb-20 {
  margin-bottom: 20rpx;
}

.p-20 {
  padding: 20rpx;
}
</style>