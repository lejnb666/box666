<template>
  <view class="markdown-renderer">
    <!-- 标题 -->
    <block v-for="(line, index) in processedLines" :key="index">
      <view v-if="line.type === 'heading'" :class="['heading', `h${line.level}`]">
        {{ line.content }}
      </view>

      <!-- 段落 -->
      <view v-else-if="line.type === 'paragraph'" class="paragraph">
        <text v-for="(part, partIndex) in line.parts" :key="partIndex" :class="part.style">
          {{ part.text }}
        </text>
      </view>

      <!-- 列表 -->
      <view v-else-if="line.type === 'list-item'" class="list-item">
        <text class="bullet">•</text>
        <text>{{ line.content }}</text>
      </view>

      <!-- 代码块 -->
      <view v-else-if="line.type === 'code-block'" class="code-block">
        <text class="code-content">{{ line.content }}</text>
      </view>

      <!-- 行内代码 -->
      <view v-else-if="line.type === 'inline-code'" class="inline-code">
        <text class="code-text">{{ line.content }}</text>
      </view>

      <!-- 普通文本 -->
      <view v-else class="text-line">
        {{ line.content }}
      </view>
    </block>
  </view>
</template>

<script>
export default {
  name: 'MarkdownRenderer',
  props: {
    content: {
      type: String,
      default: ''
    }
  },
  computed: {
    processedLines() {
      if (!this.content) return []

      const lines = this.content.split('\n')
      const processed = []

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]

        // 空行
        if (!line.trim()) {
          continue
        }

        // 标题 (# ## ###)
        const headingMatch = line.match(/^(#{1,6})\s+(.+)$/)
        if (headingMatch) {
          processed.push({
            type: 'heading',
            level: headingMatch[1].length,
            content: headingMatch[2]
          })
          continue
        }

        // 代码块 (```code```)
        if (line.startsWith('```') && line.endsWith('```')) {
          processed.push({
            type: 'code-block',
            content: line.slice(3, -3)
          })
          continue
        }

        // 列表项
        if (line.match(/^[-*+]\s+/)) {
          processed.push({
            type: 'list-item',
            content: line.replace(/^[-*+]\s+/, '')
          })
          continue
        }

        // 处理段落（包含行内格式）
        const paragraphParts = this.parseInlineMarkdown(line)
        processed.push({
          type: 'paragraph',
          parts: paragraphParts
        })
      }

      return processed
    }
  },
  methods: {
    parseInlineMarkdown(text) {
      const parts = []
      let remaining = text

      while (remaining.length > 0) {
        // 粗体 **text**
        const boldMatch = remaining.match(/^\*\*(.+?)\*\*/)
        if (boldMatch) {
          parts.push({
            text: boldMatch[1],
            style: 'bold'
          })
          remaining = remaining.slice(boldMatch[0].length)
          continue
        }

        // 斜体 *text*
        const italicMatch = remaining.match(/^\*(.+?)\*/)
        if (italicMatch) {
          parts.push({
            text: italicMatch[1],
            style: 'italic'
          })
          remaining = remaining.slice(italicMatch[0].length)
          continue
        }

        // 行内代码 `code`
        const codeMatch = remaining.match(/^`(.+?)`/)
        if (codeMatch) {
          parts.push({
            text: codeMatch[1],
            style: 'code'
          })
          remaining = remaining.slice(codeMatch[0].length)
          continue
        }

        // 链接 [text](url)
        const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^\)]+)\)/)
        if (linkMatch) {
          parts.push({
            text: linkMatch[1],
            style: 'link',
            url: linkMatch[2]
          })
          remaining = remaining.slice(linkMatch[0].length)
          continue
        }

        // 普通文本
        const nextSpecial = this.findNextSpecialChar(remaining)
        if (nextSpecial === -1) {
          parts.push({
            text: remaining,
            style: 'normal'
          })
          break
        } else {
          parts.push({
            text: remaining.slice(0, nextSpecial),
            style: 'normal'
          })
          remaining = remaining.slice(nextSpecial)
        }
      }

      return parts
    },

    findNextSpecialChar(text) {
      const specialChars = ['*', '`', '[', '_']
      let minIndex = text.length

      for (const char of specialChars) {
        const index = text.indexOf(char)
        if (index !== -1 && index < minIndex) {
          minIndex = index
        }
      }

      return minIndex === text.length ? -1 : minIndex
    }
  }
}
</script>

<style>
.markdown-renderer {
  font-size: 28rpx;
  line-height: 1.6;
  color: #333;
}

.heading {
  font-weight: bold;
  margin: 20rpx 0 10rpx 0;
  color: #2c3e50;
}

.h1 {
  font-size: 40rpx;
  border-bottom: 2rpx solid #eee;
  padding-bottom: 10rpx;
}

.h2 {
  font-size: 36rpx;
}

.h3 {
  font-size: 32rpx;
}

.h4, .h5, .h6 {
  font-size: 28rpx;
}

.paragraph {
  margin: 10rpx 0;
}

.list-item {
  margin: 8rpx 0 8rpx 20rpx;
  display: flex;
  align-items: flex-start;
}

.bullet {
  margin-right: 10rpx;
  color: #007AFF;
}

.code-block {
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 8rpx;
  padding: 15rpx;
  margin: 10rpx 0;
  font-family: monospace;
  font-size: 26rpx;
  overflow-x: auto;
}

.code-content {
  color: #d63384;
}

.inline-code {
  background-color: #f5f5f5;
  border: 1px solid #ddd;
  border-radius: 4rpx;
  padding: 2rpx 6rpx;
  font-family: monospace;
  font-size: 26rpx;
}

.code-text {
  color: #d63384;
}

.bold {
  font-weight: bold;
  color: #2c3e50;
}

.italic {
  font-style: italic;
  color: #666;
}

.link {
  color: #007AFF;
  text-decoration: underline;
}

.text-line {
  margin: 5rpx 0;
}
</style>