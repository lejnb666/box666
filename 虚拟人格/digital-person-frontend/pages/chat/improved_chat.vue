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
            <!-- 流式消息显示 -->
            <block v-if="message.type === 'bot' && message.isStreaming">
              <TypingEffect
                :text="message.content"
                :char-delay="30"
                :show-typing-indicator="true"
                @typing-complete="onTypingComplete(index)"
              />
            </block>

            <!-- 普通消息显示 -->
            <block v-else-if="message.type === 'bot' && message.isMarkdown">
              <MarkdownRenderer :content="message.content" />
            </block>

            <!-- 工具使用提示 -->
            <block v-else-if="message.toolUsed">
              <view class="tool-indicator">
                <text class="tool-icon">🔧</text>
                <text class="tool-text">使用了 {{ message.toolUsed }} 工具</text>
              </view>
              <MarkdownRenderer v-if="message.isMarkdown" :content="message.content" />
              <text v-else>{{ message.content }}</text>
            </block>

            <!-- 普通文本消息 -->
            <block v-else>
              <text>{{ message.content }}</text>
            </block>
          </view>
          <view class="message-time">
            {{ message.time }}
          </view>
        </view>
      </view>

      <!-- 加载指示器 -->
      <view v-if="isLoading" class="loading-container">
        <TypingEffect text="" :show-typing-indicator="true" />
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
        :disabled="isLoading"
      />
      <button class="send-btn" @tap="sendMessage" :disabled="!inputMessage.trim() || isLoading">
        <text v-if="!isLoading">发送</text>
        <text v-else>...</text>
      </button>
    </view>

    <!-- 工具选择面板 -->
    <view v-if="showToolsPanel" class="tools-panel">
      <view class="tools-header">
        <text class="tools-title">可用工具</text>
        <text class="tools-close" @tap="showToolsPanel = false">×</text>
      </view>
      <scroll-view class="tools-list" scroll-x="true">
        <view
          v-for="tool in availableTools"
          :key="tool.name"
          class="tool-item"
          @tap="useTool(tool)"
        >
          <text class="tool-name">{{ tool.name }}</text>
          <text class="tool-description">{{ tool.description }}</text>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script>
import TypingEffect from '@/components/TypingEffect.vue'
import MarkdownRenderer from '@/components/MarkdownRenderer.vue'

export default {
  components: {
    TypingEffect,
    MarkdownRenderer
  },
  data() {
    return {
      messages: [
        {
          type: 'bot',
          content: '你好！我是李四，很高兴和你聊天！',
          time: this.formatTime(new Date()),
          isStreaming: false,
          isMarkdown: false
        }
      ],
      inputMessage: '',
      scrollTop: 0,
      userAvatar: '/static/user-avatar.png',
      botAvatar: '/static/bot-avatar.png',
      isLoading: false,
      showToolsPanel: false,
      availableTools: [],
      currentStreamingMessage: null
    }
  },
  created() {
    this.loadAvailableTools()
  },
  methods: {
    formatTime(date) {
      const hours = date.getHours().toString().padStart(2, '0')
      const minutes = date.getMinutes().toString().padStart(2, '0')
      return `${hours}:${minutes}`
    },

    async loadAvailableTools() {
      try {
        const response = await uni.request({
          url: 'http://localhost:8080/api/tools',
          method: 'GET'
        })

        if (response[1].statusCode === 200) {
          const result = response[1].data
          if (result.success) {
            this.availableTools = result.tools
          }
        }
      } catch (error) {
        console.error('加载工具列表失败:', error)
      }
    },

    async sendMessage() {
      if (!this.inputMessage.trim() || this.isLoading) {
        return
      }

      const userMessage = this.inputMessage.trim()
      this.inputMessage = ''

      // 添加用户消息
      this.messages.push({
        type: 'user',
        content: userMessage,
        time: this.formatTime(new Date())
      })

      this.isLoading = true
      this.scrollToBottom()

      try {
        // 首先尝试使用Function Calling
        await this.sendFunctionCallMessage(userMessage)
      } catch (error) {
        console.error('Function Calling失败，降级到普通聊天:', error)
        // 降级到普通聊天
        await this.sendNormalMessage(userMessage)
      } finally {
        this.isLoading = false
        this.scrollToBottom()
      }
    },

    async sendFunctionCallMessage(userMessage) {
      try {
        const response = await uni.request({
          url: 'http://localhost:8080/api/chat/function',
          method: 'POST',
          header: {
            'Content-Type': 'application/json'
          },
          data: {
            message: userMessage
          }
        })

        const result = response[1].data
        if (result.success) {
          this.addBotMessage({
            content: result.response,
            toolUsed: result.tool_used,
            isMarkdown: this.containsMarkdown(result.response)
          })
        } else {
          throw new Error(result.error || 'Function Calling失败')
        }
      } catch (error) {
        throw error
      }
    },

    async sendNormalMessage(userMessage) {
      try {
        // 尝试使用流式API
        await this.sendStreamingMessage(userMessage)
      } catch (streamingError) {
        console.error('流式API失败，使用普通API:', streamingError)
        // 降级到普通API
        const response = await uni.request({
          url: 'http://localhost:8080/api/chat',
          method: 'POST',
          header: {
            'Content-Type': 'application/json'
          },
          data: {
            message: userMessage
          }
        })

        const result = response[1].data
        if (result.success) {
          this.addBotMessage({
            content: result.response,
            isMarkdown: this.containsMarkdown(result.response)
          })
        } else {
          this.addBotMessage({
            content: '抱歉，服务器出错了，请稍后再试。'
          })
        }
      }
    },

    async sendStreamingMessage(userMessage) {
      return new Promise((resolve, reject) => {
        let fullResponse = ''
        let isFirstChunk = true

        // 添加流式消息占位符
        const messageIndex = this.messages.length
        this.messages.push({
          type: 'bot',
          content: '',
          time: this.formatTime(new Date()),
          isStreaming: true
        })

        // 创建SSE连接
        const eventSource = new EventSource(`http://localhost:8080/api/chat/stream?message=${encodeURIComponent(userMessage)}`)

        eventSource.onmessage = (event) => {
          try {
            if (event.data === '[DONE]') {
              // 流式传输完成
              eventSource.close()
              this.messages[messageIndex].isStreaming = false
              this.messages[messageIndex].isMarkdown = this.containsMarkdown(fullResponse)
              resolve()
              return
            }

            const chunk = event.data
            fullResponse += chunk

            // 更新消息内容
            this.messages[messageIndex].content = fullResponse

            if (isFirstChunk) {
              isFirstChunk = false
              this.scrollToBottom()
            }
          } catch (error) {
            console.error('处理流式消息失败:', error)
            eventSource.close()
            reject(error)
          }
        }

        eventSource.onerror = (error) => {
          console.error('SSE连接错误:', error)
          eventSource.close()
          reject(error)
        }
      })
    },

    addBotMessage({ content, toolUsed = null, isMarkdown = false }) {
      this.messages.push({
        type: 'bot',
        content: content,
        time: this.formatTime(new Date()),
        toolUsed: toolUsed,
        isMarkdown: isMarkdown,
        isStreaming: false
      })
    },

    containsMarkdown(text) {
      // 检查是否包含Markdown语法
      const markdownPatterns = [
        /\*\*(.+?)\*\*/,  // 粗体
        /\*(.+?)\*/,      // 斜体
        /`(.+?)`/,        // 行内代码
        /^#{1,6}\s+.+$/m, // 标题
        /^[-*+]\s+/m,     // 列表
        /^```[\s\S]*?```$/m // 代码块
      ]

      return markdownPatterns.some(pattern => pattern.test(text))
    },

    onTypingComplete(messageIndex) {
      // 打字效果完成后的回调
      this.scrollToBottom()
    },

    useTool(tool) {
      // 使用特定工具
      this.inputMessage = tool.example || `使用${tool.name}工具`
      this.showToolsPanel = false
    },

    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTop = this.messages.length * 1000
      })
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
  position: relative;
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
  max-width: 70%;
}

.message-bubble {
  background-color: #fff;
  padding: 20rpx;
  border-radius: 20rpx;
  font-size: 28rpx;
  line-height: 1.4;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.1);
  word-break: break-word;
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

.tool-indicator {
  display: flex;
  align-items: center;
  margin-bottom: 10rpx;
  padding: 8rpx;
  background-color: #f0f8ff;
  border-radius: 8rpx;
  border-left: 3px solid #007AFF;
}

.tool-icon {
  font-size: 24rpx;
  margin-right: 8rpx;
}

.tool-text {
  font-size: 24rpx;
  color: #007AFF;
  font-weight: 500;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 20rpx;
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

.message-input[disabled] {
  background-color: #f5f5f5;
  color: #999;
}

.send-btn {
  background-color: #007AFF;
  color: white;
  border: none;
  border-radius: 40rpx;
  padding: 20rpx 40rpx;
  font-size: 28rpx;
  min-width: 100rpx;
}

.send-btn[disabled] {
  background-color: #ccc;
}

/* 工具面板样式 */
.tools-panel {
  position: absolute;
  bottom: 120rpx;
  left: 20rpx;
  right: 20rpx;
  background-color: #fff;
  border-radius: 15rpx;
  box-shadow: 0 -2rpx 20rpx rgba(0,0,0,0.1);
  z-index: 1000;
}

.tools-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx;
  border-bottom: 1rpx solid #eee;
}

.tools-title {
  font-weight: bold;
  color: #333;
}

.tools-close {
  font-size: 36rpx;
  color: #999;
  cursor: pointer;
}

.tools-list {
  padding: 20rpx;
  white-space: nowrap;
}

.tool-item {
  display: inline-block;
  margin-right: 20rpx;
  padding: 15rpx;
  background-color: #f8f9fa;
  border-radius: 10rpx;
  min-width: 200rpx;
}

.tool-name {
  font-weight: bold;
  color: #007AFF;
  display: block;
  margin-bottom: 5rpx;
}

.tool-description {
  font-size: 24rpx;
  color: #666;
  white-space: normal;
}
</style>