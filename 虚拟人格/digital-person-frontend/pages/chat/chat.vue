<template>
  <view class="chat-container">
    <!-- 消息列表 -->
    <scroll-view class="message-list" scroll-y="true" scroll-with-animation="true" :scroll-top="scrollTop">
      <view v-for="(message, index) in messages" :key="index" :class="['message-item', message.type]">
        <view class="avatar">
          <image :src="message.type === 'user' ? userAvatar : botAvatar" class="avatar-img"></image>
        </view>
        <view class="message-content">
          <view class="message-bubble">
            {{ message.content }}
          </view>
          <view class="message-time">
            {{ message.time }}
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 输入区域 -->
    <view class="input-area">
      <input
        class="message-input"
        v-model="inputMessage"
        placeholder="输入消息..."
        @confirm="sendMessage"
        confirm-type="send"
      />
      <button class="send-btn" @tap="sendMessage" :disabled="!inputMessage.trim()">
        发送
      </button>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      messages: [
        {
          type: 'bot',
          content: '你好！我是李四，很高兴和你聊天！',
          time: this.formatTime(new Date())
        }
      ],
      inputMessage: '',
      scrollTop: 0,
      userAvatar: '/static/user-avatar.png',
      botAvatar: '/static/bot-avatar.png',
      isLoading: false
    }
  },

  methods: {
    formatTime(date) {
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${hours}:${minutes}`;
    },

    async sendMessage() {
      if (!this.inputMessage.trim() || this.isLoading) {
        return;
      }

      const userMessage = this.inputMessage.trim();
      this.inputMessage = '';

      // 添加用户消息
      this.messages.push({
        type: 'user',
        content: userMessage,
        time: this.formatTime(new Date())
      });

      this.isLoading = true;
      this.scrollToBottom();

      try {
        // 调用后端API
        const response = await uni.request({
          url: 'http://localhost:8080/api/chat',
          method: 'POST',
          header: {
            'Content-Type': 'application/json'
          },
          data: {
            message: userMessage
          }
        });

        const result = response[1].data;
        if (result.success) {
          this.messages.push({
            type: 'bot',
            content: result.response,
            time: this.formatTime(new Date())
          });
        } else {
          this.messages.push({
            type: 'bot',
            content: '抱歉，服务器出错了，请稍后再试。',
            time: this.formatTime(new Date())
          });
        }
      } catch (error) {
        console.error('发送消息失败:', error);
        this.messages.push({
          type: 'bot',
          content: '网络连接失败，请检查网络设置。',
          time: this.formatTime(new Date())
        });
      } finally {
        this.isLoading = false;
        this.scrollToBottom();
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTop = this.messages.length * 100;
      });
    }
  }
}
</script>

<style>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.message-list {
  flex: 1;
  padding: 20rpx;
  overflow-y: auto;
}

.message-item {
  display: flex;
  margin-bottom: 20rpx;
  align-items: flex-start;
}

.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  overflow: hidden;
  margin: 0 20rpx;
}

.avatar-img {
  width: 100%;
  height: 100%;
}

.message-content {
  max-width: 60%;
}

.message-bubble {
  background-color: #fff;
  padding: 20rpx;
  border-radius: 20rpx;
  font-size: 28rpx;
  line-height: 1.4;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.1);
}

.message-item.user .message-bubble {
  background-color: #007AFF;
  color: white;
}

.message-time {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  text-align: center;
}

.input-area {
  display: flex;
  padding: 20rpx;
  background-color: #fff;
  border-top: 1rpx solid #eee;
  align-items: center;
}

.message-input {
  flex: 1;
  height: 80rpx;
  border: 1rpx solid #ddd;
  border-radius: 40rpx;
  padding: 0 30rpx;
  font-size: 28rpx;
  margin-right: 20rpx;
}

.send-btn {
  background-color: #007AFF;
  color: white;
  border: none;
  border-radius: 40rpx;
  padding: 20rpx 40rpx;
  font-size: 28rpx;
}

.send-btn[disabled] {
  background-color: #ccc;
}
</style>