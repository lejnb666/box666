<template>
  <view class="analytics-dashboard">
    <!-- 顶部导航栏 -->
    <view class="header">
      <view class="header-content">
        <text class="header-title">数据分析中心</text>
        <view class="header-actions">
          <picker mode="date" :value="selectedDate" @change="onDateChange">
            <view class="date-picker">
              <text class="date-text">{{selectedDate}}</text>
              <text class="iconfont">📅</text>
            </view>
          </picker>
        </view>
      </view>
    </view>

    <!-- 数据概览卡片 -->
    <view class="overview-section">
      <view class="section-title">数据概览</view>
      <view class="overview-grid">
        <view class="overview-card" v-for="item in overviewData" :key="item.title">
          <view class="card-icon" :style="{backgroundColor: item.color}">
            <text class="iconfont">{{item.icon}}</text>
          </view>
          <view class="card-content">
            <text class="card-value">{{item.value}}</text>
            <text class="card-title">{{item.title}}</text>
            <text class="card-change" :class="item.trend > 0 ? 'trend-up' : 'trend-down'">
              {{item.trend > 0 ? '↗' : '↘'}} {{Math.abs(item.trend)}}%
            </text>
          </view>
        </view>
      </view>
    </view>

    <!-- 主播排行榜 -->
    <view class="ranking-section">
      <view class="section-title">主播排行榜</view>
      <view class="ranking-tabs">
        <view
          class="tab"
          v-for="tab in rankingTabs"
          :key="tab.key"
          :class="{active: currentTab === tab.key}"
          @click="switchTab(tab.key)"
        >
          {{tab.name}}
        </view>
      </view>
      <view class="ranking-list">
        <view
          class="ranking-item"
          v-for="(streamer, index) in streamerRanking"
          :key="streamer.streamerId"
          @click="navigateToStreamerDetail(streamer.streamerId)"
        >
          <view class="rank-number" :class="getRankClass(index)">
            {{index + 1}}
          </view>
          <view class="streamer-avatar">
            <image :src="streamer.avatar || '/static/default-avatar.png'" mode="aspectFill"></image>
          </view>
          <view class="streamer-info">
            <text class="streamer-name">{{streamer.streamerName}}</text>
            <text class="streamer-stats">{{getStatsText(streamer)}}</text>
          </view>
          <view class="streamer-score">
            <text class="score-value">{{getScoreValue(streamer)}}</text>
            <text class="score-label">{{getScoreLabel()}}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 活跃度热力图 -->
    <view class="heatmap-section">
      <view class="section-title">观众活跃度热力图</view>
      <view class="heatmap-container">
        <view class="heatmap-header">
          <text class="heatmap-title">{{selectedStreamer}}</text>
          <picker :range="streamerList" range-key="name" @change="onStreamerChange">
            <view class="streamer-selector">
              <text>选择主播</text>
              <text class="iconfont">▼</text>
            </view>
          </picker>
        </view>
        <view class="heatmap-grid">
          <view class="hour-labels">
            <text class="label-item" v-for="hour in 24" :key="hour">{{hour-1}}</text>
          </view>
          <view class="heatmap-cells">
            <view
              class="heatmap-cell"
              v-for="(value, index) in heatmapData"
              :key="index"
              :style="{backgroundColor: getHeatmapColor(value)}"
              @click="showHeatmapDetail(index, value)"
            >
              <text class="cell-value">{{value}}</text>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 热词分析 -->
    <view class="hotwords-section">
      <view class="section-title">热词分析</view>
      <view class="hotwords-container">
        <view class="hotwords-header">
          <text class="hotwords-title">TOP 20 热词</text>
          <view class="sentiment-filter">
            <view
              class="sentiment-tab"
              v-for="filter in sentimentFilters"
              :key="filter.key"
              :class="{active: currentSentimentFilter === filter.key}"
              @click="filterHotWords(filter.key)"
            >
              {{filter.name}}
            </view>
          </view>
        </view>
        <view class="word-cloud">
          <view
            class="word-item"
            v-for="(word, index) in filteredHotWords"
            :key="word.word"
            :style="{
              fontSize: getWordSize(word.rank),
              color: getWordColor(word.category),
              opacity: getWordOpacity(word.rank)
            }"
            @click="showWordDetail(word)"
          >
            {{word.word}}({{word.count}})
          </view>
        </view>
      </view>
    </view>

    <!-- 情感分析趋势 -->
    <view class="sentiment-section">
      <view class="section-title">情感分析趋势</view>
      <view class="sentiment-chart">
        <view class="chart-header">
          <view class="sentiment-legend">
            <view class="legend-item">
              <view class="legend-color positive"></view>
              <text>正面</text>
            </view>
            <view class="legend-item">
              <view class="legend-color negative"></view>
              <text>负面</text>
            </view>
            <view class="legend-item">
              <view class="legend-color neutral"></view>
              <text>中性</text>
            </view>
          </view>
        </view>
        <view class="chart-container">
          <view
            class="sentiment-bar"
            v-for="(data, hour) in sentimentTrend"
            :key="hour"
          >
            <view class="bar-container">
              <view
                class="bar positive"
                :style="{height: data.positive + '%'}"
              ></view>
              <view
                class="bar negative"
                :style="{height: data.negative + '%'}"
              ></view>
              <view
                class="bar neutral"
                :style="{height: data.neutral + '%'}"
              ></view>
            </view>
            <text class="hour-label">{{hour}}时</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 数据导出 -->
    <view class="export-section">
      <button class="export-btn" @click="exportData">
        <text class="iconfont">📊</text>
        导出分析报告
      </button>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      selectedDate: this.formatDate(new Date()),
      currentTab: 'barrage',
      currentSentimentFilter: 'all',
      selectedStreamer: '全部主播',

      // 数据概览
      overviewData: [
        {
          title: '总弹幕数',
          value: '125,430',
          icon: '💬',
          color: '#007AFF',
          trend: 12.5
        },
        {
          title: '活跃主播',
          value: '156',
          icon: '🎤',
          color: '#4CD964',
          trend: 8.3
        },
        {
          title: '独立观众',
          value: '45,230',
          icon: '👥',
          color: '#FF9500',
          trend: -2.1
        },
        {
          title: '礼物价值',
          value: '¥8,950',
          icon: '🎁',
          color: '#FF3B30',
          trend: 15.7
        }
      ],

      // 排行榜标签
      rankingTabs: [
        {key: 'barrage', name: '弹幕量'},
        {key: 'viewers', name: '观众数'},
        {key: 'gifts', name: '礼物价值'},
        {key: 'engagement', name: '参与度'}
      ],

      // 主播排行榜数据
      streamerRanking: [],

      // 主播列表
      streamerList: [],

      // 热力图数据
      heatmapData: [],

      // 热词数据
      hotWords: [],
      filteredHotWords: [],

      // 情感过滤器
      sentimentFilters: [
        {key: 'all', name: '全部'},
        {key: 'positive', name: '正面'},
        {key: 'negative', name: '负面'},
        {key: 'gift', name: '礼物'},
        {key: 'stream', name: '直播'}
      ],

      // 情感趋势数据
      sentimentTrend: []
    }
  },

  onLoad() {
    this.loadAnalyticsData();
  },

  methods: {
    formatDate(date) {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },

    async loadAnalyticsData() {
      try {
        // 加载数据概览
        await this.loadOverviewData();

        // 加载主播排行榜
        await this.loadStreamerRanking();

        // 加载主播列表
        await this.loadStreamerList();

        // 加载热力图数据
        await this.loadHeatmapData();

        // 加载热词数据
        await this.loadHotWords();

        // 加载情感趋势
        await this.loadSentimentTrend();
      } catch (error) {
        console.error('加载分析数据失败:', error);
      }
    },

    async loadOverviewData() {
      // 模拟API调用
      const response = await uni.request({
        url: `/api/analytics/overview?date=${this.selectedDate}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        const data = response[1].data;
        this.overviewData = [
          {
            title: '总弹幕数',
            value: this.formatNumber(data.totalBarrages),
            icon: '💬',
            color: '#007AFF',
            trend: data.barrageTrend
          },
          {
            title: '活跃主播',
            value: data.activeStreamers,
            icon: '🎤',
            color: '#4CD964',
            trend: data.streamerTrend
          },
          {
            title: '独立观众',
            value: this.formatNumber(data.uniqueViewers),
            icon: '👥',
            color: '#FF9500',
            trend: data.viewerTrend
          },
          {
            title: '礼物价值',
            value: `¥${this.formatNumber(data.totalGiftValue)}`,
            icon: '🎁',
            color: '#FF3B30',
            trend: data.giftTrend
          }
        ];
      }
    },

    async loadStreamerRanking() {
      const response = await uni.request({
        url: `/api/analytics/streamer-ranking?date=${this.selectedDate}&type=${this.currentTab}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        this.streamerRanking = response[1].data;
      }
    },

    async loadStreamerList() {
      const response = await uni.request({
        url: `/api/analytics/streamer-list?date=${this.selectedDate}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        this.streamerList = response[1].data;
      }
    },

    async loadHeatmapData() {
      const response = await uni.request({
        url: `/api/analytics/heatmap?date=${this.selectedDate}&streamer=${this.selectedStreamer}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        this.heatmapData = response[1].data;
      }
    },

    async loadHotWords() {
      const response = await uni.request({
        url: `/api/analytics/hot-words?date=${this.selectedDate}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        this.hotWords = response[1].data;
        this.filteredHotWords = this.hotWords;
      }
    },

    async loadSentimentTrend() {
      const response = await uni.request({
        url: `/api/analytics/sentiment-trend?date=${this.selectedDate}`,
        method: 'GET'
      });

      if (response[1].statusCode === 200) {
        this.sentimentTrend = response[1].data;
      }
    },

    onDateChange(event) {
      this.selectedDate = event.detail.value;
      this.loadAnalyticsData();
    },

    switchTab(tab) {
      this.currentTab = tab;
      this.loadStreamerRanking();
    },

    onStreamerChange(event) {
      const index = event.detail.value;
      this.selectedStreamer = this.streamerList[index].name;
      this.loadHeatmapData();
    },

    filterHotWords(filter) {
      this.currentSentimentFilter = filter;
      if (filter === 'all') {
        this.filteredHotWords = this.hotWords;
      } else {
        this.filteredHotWords = this.hotWords.filter(word => word.category === filter);
      }
    },

    navigateToStreamerDetail(streamerId) {
      uni.navigateTo({
        url: `/pages/analytics/streamer-detail?streamerId=${streamerId}&date=${this.selectedDate}`
      });
    },

    showHeatmapDetail(hour, value) {
      uni.showModal({
        title: `${hour}时活跃度详情`,
        content: `弹幕数量: ${value}\n参与用户: ${Math.floor(value * 0.6)}\n礼物数量: ${Math.floor(value * 0.1)}`,
        showCancel: false
      });
    },

    showWordDetail(word) {
      uni.showModal({
        title: '热词详情',
        content: `词语: ${word.word}\n出现次数: ${word.count}\n占比: ${word.frequency}%\n类别: ${this.getCategoryName(word.category)}`,
        showCancel: false
      });
    },

    getRankClass(index) {
      if (index === 0) return 'rank-gold';
      if (index === 1) return 'rank-silver';
      if (index === 2) return 'rank-bronze';
      return 'rank-normal';
    },

    getStatsText(streamer) {
      switch (this.currentTab) {
        case 'barrage':
          return `观众: ${this.formatNumber(streamer.uniqueViewers)}`;
        case 'viewers':
          return `弹幕: ${this.formatNumber(streamer.totalBarrages)}`;
        case 'gifts':
          return `观众: ${this.formatNumber(streamer.uniqueViewers)}`;
        case 'engagement':
          return `分数: ${streamer.engagementScore}`;
        default:
          return '';
      }
    },

    getScoreValue(streamer) {
      switch (this.currentTab) {
        case 'barrage':
          return this.formatNumber(streamer.totalBarrages);
        case 'viewers':
          return this.formatNumber(streamer.uniqueViewers);
        case 'gifts':
          return `¥${this.formatNumber(streamer.totalGiftValue)}`;
        case 'engagement':
          return streamer.engagementScore;
        default:
          return '';
      }
    },

    getScoreLabel() {
      switch (this.currentTab) {
        case 'barrage':
          return '弹幕';
        case 'viewers':
          return '观众';
        case 'gifts':
          return '礼物';
        case 'engagement':
          return '分数';
        default:
          return '';
      }
    },

    getHeatmapColor(value) {
      const max = Math.max(...this.heatmapData);
      const intensity = value / max;

      if (intensity > 0.8) return '#FF3B30';
      if (intensity > 0.6) return '#FF9500';
      if (intensity > 0.4) return '#FFCC00';
      if (intensity > 0.2) return '#4CD964';
      return '#007AFF';
    },

    getWordSize(rank) {
      if (rank <= 3) return '24px';
      if (rank <= 8) return '20px';
      if (rank <= 15) return '16px';
      return '14px';
    },

    getWordColor(category) {
      const colors = {
        positive: '#4CD964',
        negative: '#FF3B30',
        gift: '#FF9500',
        stream: '#007AFF',
        general: '#666666'
      };
      return colors[category] || '#666666';
    },

    getWordOpacity(rank) {
      return Math.max(0.4, 1 - (rank - 1) * 0.05);
    },

    getCategoryName(category) {
      const names = {
        positive: '正面',
        negative: '负面',
        gift: '礼物',
        stream: '直播',
        general: '一般'
      };
      return names[category] || category;
    },

    formatNumber(num) {
      if (num >= 10000) {
        return (num / 10000).toFixed(1) + 'w';
      }
      if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
      }
      return num.toString();
    },

    async exportData() {
      try {
        uni.showLoading({ title: '导出中...' });

        const response = await uni.request({
          url: `/api/analytics/export?date=${this.selectedDate}`,
          method: 'GET'
        });

        if (response[1].statusCode === 200) {
          const downloadUrl = response[1].data.downloadUrl;

          // 下载文件
          uni.downloadFile({
            url: downloadUrl,
            success: (downloadRes) => {
              if (downloadRes.statusCode === 200) {
                uni.openDocument({
                  filePath: downloadRes.tempFilePath,
                  success: () => {
                    uni.showToast({ title: '导出成功', icon: 'success' });
                  }
                });
              }
            }
          });
        }
      } catch (error) {
        uni.showToast({ title: '导出失败', icon: 'error' });
      } finally {
        uni.hideLoading();
      }
    }
  }
}
</script>

<style lang="scss">
.analytics-dashboard {
  min-height: 100vh;
  background-color: var(--bg-secondary);
}

.header {
  background: var(--bg-primary);
  padding: 20rpx 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 36rpx;
  font-weight: 600;
  color: var(--text-primary);
}

.date-picker {
  display: flex;
  align-items: center;
  padding: 12rpx 20rpx;
  background: var(--bg-secondary);
  border-radius: 8rpx;
}

.date-text {
  font-size: 28rpx;
  color: var(--text-primary);
  margin-right: 10rpx;
}

.overview-section,
.ranking-section,
.heatmap-section,
.hotwords-section,
.sentiment-section,
.export-section {
  margin: 30rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20rpx;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.overview-card {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 20rpx;
  display: flex;
  align-items: center;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.card-icon {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.card-content {
  flex: 1;
}

.card-value {
  font-size: 36rpx;
  font-weight: 600;
  color: var(--text-primary);
  display: block;
}

.card-title {
  font-size: 24rpx;
  color: var(--text-secondary);
  margin: 4rpx 0;
}

.card-change {
  font-size: 20rpx;
  font-weight: 500;
}

.trend-up {
  color: #4CD964;
}

.trend-down {
  color: #FF3B30;
}

.ranking-tabs {
  display: flex;
  background: var(--bg-primary);
  border-radius: 8rpx;
  padding: 8rpx;
  margin-bottom: 20rpx;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 16rpx;
  font-size: 26rpx;
  color: var(--text-secondary);
  border-radius: 6rpx;
}

.tab.active {
  background: var(--primary-color);
  color: white;
}

.ranking-item {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
  display: flex;
  align-items: center;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.rank-number {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20rpx;
  font-weight: 600;
  margin-right: 20rpx;
}

.rank-gold {
  background: #FFD700;
  color: #fff;
}

.rank-silver {
  background: #C0C0C0;
  color: #fff;
}

.rank-bronze {
  background: #CD7F32;
  color: #fff;
}

.rank-normal {
  background: #E5E5E5;
  color: #666;
}

.streamer-avatar {
  width: 60rpx;
  height: 60rpx;
  border-radius: 50%;
  margin-right: 16rpx;
  overflow: hidden;
}

.streamer-avatar image {
  width: 100%;
  height: 100%;
}

.streamer-info {
  flex: 1;
}

.streamer-name {
  font-size: 28rpx;
  font-weight: 500;
  color: var(--text-primary);
  display: block;
}

.streamer-stats {
  font-size: 22rpx;
  color: var(--text-light);
  margin-top: 4rpx;
}

.streamer-score {
  text-align: right;
}

.score-value {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--primary-color);
  display: block;
}

.score-label {
  font-size: 20rpx;
  color: var(--text-light);
  margin-top: 4rpx;
}

.heatmap-container {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.heatmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.heatmap-title {
  font-size: 28rpx;
  font-weight: 500;
  color: var(--text-primary);
}

.streamer-selector {
  display: flex;
  align-items: center;
  padding: 8rpx 16rpx;
  background: var(--bg-secondary);
  border-radius: 6rpx;
  font-size: 24rpx;
  color: var(--text-secondary);
}

.heatmap-grid {
  display: flex;
  align-items: flex-end;
}

.hour-labels {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 240rpx;
  margin-right: 10rpx;
}

.label-item {
  font-size: 20rpx;
  color: var(--text-light);
  text-align: right;
  height: 10rpx;
}

.heatmap-cells {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 2rpx;
  flex: 1;
}

.heatmap-cell {
  aspect-ratio: 1;
  border-radius: 2rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.cell-value {
  font-size: 16rpx;
  color: white;
  font-weight: 500;
}

.hotwords-container {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.hotwords-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.hotwords-title {
  font-size: 28rpx;
  font-weight: 500;
  color: var(--text-primary);
}

.sentiment-filter {
  display: flex;
}

.sentiment-tab {
  padding: 8rpx 16rpx;
  font-size: 22rpx;
  color: var(--text-secondary);
  border-radius: 6rpx;
  margin-left: 8rpx;
}

.sentiment-tab.active {
  background: var(--primary-color);
  color: white;
}

.word-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  min-height: 200rpx;
}

.word-item {
  padding: 8rpx 12rpx;
  border-radius: 6rpx;
  font-weight: 500;
  cursor: pointer;
}

.sentiment-chart {
  background: var(--bg-primary);
  border-radius: 12rpx;
  padding: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.chart-header {
  margin-bottom: 20rpx;
}

.sentiment-legend {
  display: flex;
  justify-content: center;
}

.legend-item {
  display: flex;
  align-items: center;
  margin: 0 16rpx;
}

.legend-color {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  margin-right: 8rpx;
}

.legend-color.positive {
  background: #4CD964;
}

.legend-color.negative {
  background: #FF3B30;
}

.legend-color.neutral {
  background: #007AFF;
}

.chart-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 200rpx;
}

.sentiment-bar {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 2rpx;
}

.bar-container {
  width: 100%;
  height: 160rpx;
  display: flex;
  flex-direction: column-reverse;
  position: relative;
}

.bar {
  width: 100%;
  transition: height 0.3s ease;
}

.bar.positive {
  background: #4CD964;
}

.bar.negative {
  background: #FF3B30;
}

.bar.neutral {
  background: #007AFF;
}

.hour-label {
  font-size: 18rpx;
  color: var(--text-light);
  margin-top: 8rpx;
}

.export-section {
  text-align: center;
  margin-bottom: 40rpx;
}

.export-btn {
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8rpx;
  padding: 20rpx 40rpx;
  font-size: 28rpx;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.export-btn .iconfont {
  margin-right: 8rpx;
}

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }

  .heatmap-cells {
    grid-template-columns: repeat(6, 1fr);
  }

  .chart-container {
    height: 150rpx;
  }

  .bar-container {
    height: 120rpx;
  }
}
</style>