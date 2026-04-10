<template>
  <view class="typing-container">
    <view v-if="isTyping" class="typing-indicator">
      <text class="typing-text">对方正在输入</text>
      <view class="typing-dots">
        <view class="dot dot1"></view>
        <view class="dot dot2"></view>
        <view class="dot dot3"></view>
      </view>
    </view>

    <view v-else-if="showContent" class="typing-content">
      <view v-for="(char, index) in displayedText" :key="index" class="char" :style="{ animationDelay: `${index * charDelay}ms` }">
        {{ char === ' ' ? ' ' : char }}
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'TypingEffect',
  props: {
    text: {
      type: String,
      default: ''
    },
    charDelay: {
      type: Number,
      default: 50 // 每个字符的延迟时间（毫秒）
    },
    showTypingIndicator: {
      type: Boolean,
      default: true
    }
  },
  data() {
    return {
      isTyping: false,
      showContent: false,
      displayedText: '',
      currentIndex: 0,
      timer: null
    }
  },
  watch: {
    text: {
      immediate: true,
      handler(newText) {
        if (newText) {
          this.startTyping(newText)
        }
      }
    }
  },
  methods: {
    startTyping(text) {
      // 重置状态
      this.isTyping = false
      this.showContent = false
      this.displayedText = ''
      this.currentIndex = 0

      if (this.timer) {
        clearTimeout(this.timer)
      }

      // 如果需要显示输入指示器
      if (this.showTypingIndicator) {
        this.isTyping = true

        // 模拟输入时间（基于文本长度）
        const typingDuration = Math.min(text.length * 30, 2000) // 最多2秒

        setTimeout(() => {
          this.isTyping = false
          this.showContent = true
          this.typeText(text)
        }, typingDuration)
      } else {
        // 直接开始打字效果
        this.showContent = true
        this.typeText(text)
      }
    },

    typeText(text) {
      if (this.currentIndex < text.length) {
        this.displayedText += text.charAt(this.currentIndex)
        this.currentIndex++

        this.timer = setTimeout(() => {
          this.typeText(text)
        }, this.charDelay)
      } else {
        // 打字完成，通知父组件
        this.$emit('typing-complete')
      }
    },

    skipTyping() {
      // 跳过打字效果，直接显示完整文本
      if (this.timer) {
        clearTimeout(this.timer)
      }
      this.isTyping = false
      this.displayedText = this.text
      this.$emit('typing-complete')
    }
  },
  beforeDestroy() {
    if (this.timer) {
      clearTimeout(this.timer)
    }
  }
}
</script>

<style>
.typing-container {
  min-height: 40rpx;
}

.typing-indicator {
  display: flex;
  align-items: center;
  color: #999;
  font-size: 24rpx;
  padding: 10rpx 0;
}

.typing-text {
  margin-right: 10rpx;
}

.typing-dots {
  display: flex;
  align-items: center;
}

.dot {
  width: 8rpx;
  height: 8rpx;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2rpx;
  animation: typing-dot 1.4s infinite ease-in-out;
}

.dot1 {
  animation-delay: -0.32s;
}

.dot2 {
  animation-delay: -0.16s;
}

.dot3 {
  animation-delay: 0s;
}

@keyframes typing-dot {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.typing-content {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
}

.char {
  opacity: 0;
  animation: char-appear 0.1s ease-in-out forwards;
}

@keyframes char-appear {
  from {
    opacity: 0;
    transform: translateY(10rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>