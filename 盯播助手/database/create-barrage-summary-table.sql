-- ============================================
-- 创建弹幕聚合数据表
-- 用于存储实时聚合的弹幕统计数据
-- ============================================

-- 创建弹幕分钟聚合表
CREATE TABLE IF NOT EXISTS barrage_summary (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    minute_time DATETIME NOT NULL COMMENT '分钟时间',
    barrage_count INT NOT NULL DEFAULT 0 COMMENT '弹幕数量',
    unique_user_count INT NOT NULL DEFAULT 0 COMMENT '独立用户数',
    total_gift_value DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '礼物总价值',
    avg_content_length DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均弹幕长度',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_time (streamer_id, minute_time),
    INDEX idx_time (minute_time),
    INDEX idx_streamer (streamer_id),
    UNIQUE KEY uk_streamer_minute (streamer_id, minute_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='弹幕分钟聚合数据表';

-- 创建弹幕小时聚合统计表（用于数据分析）
CREATE TABLE IF NOT EXISTS barrage_hourly_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    hour_time DATETIME NOT NULL COMMENT '小时时间',
    total_barrage_count INT NOT NULL DEFAULT 0 COMMENT '总弹幕数量',
    total_unique_users INT NOT NULL DEFAULT 0 COMMENT '总独立用户数',
    total_gift_value DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '总礼物价值',
    avg_content_length DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均弹幕长度',
    minute_records_count INT NOT NULL DEFAULT 0 COMMENT '分钟记录数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_time (streamer_id, hour_time),
    INDEX idx_time (hour_time),
    INDEX idx_streamer (streamer_id),
    UNIQUE KEY uk_streamer_hour (streamer_id, hour_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='弹幕小时聚合统计表';

-- 创建弹幕日聚合统计表（用于数据分析）
CREATE TABLE IF NOT EXISTS barrage_daily_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    date DATE NOT NULL COMMENT '日期',
    total_barrage_count BIGINT NOT NULL DEFAULT 0 COMMENT '总弹幕数量',
    total_unique_users INT NOT NULL DEFAULT 0 COMMENT '总独立用户数',
    total_gift_value DECIMAL(15,2) NOT NULL DEFAULT 0.00 COMMENT '总礼物价值',
    avg_content_length DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均弹幕长度',
    hour_records_count INT NOT NULL DEFAULT 0 COMMENT '小时记录数',
    peak_hour INT COMMENT '峰值小时(0-23)',
    peak_barrage_count INT NOT NULL DEFAULT 0 COMMENT '峰值小时弹幕数量',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_date (streamer_id, date),
    INDEX idx_date (date),
    INDEX idx_streamer (streamer_id),
    UNIQUE KEY uk_streamer_date (streamer_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='弹幕日聚合统计表';

-- 创建热词统计表
CREATE TABLE IF NOT EXISTS hot_words_stats (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    word VARCHAR(50) NOT NULL COMMENT '热词',
    word_count INT NOT NULL DEFAULT 0 COMMENT '词频',
    word_frequency DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '词频占比(%)',
    rank_num INT NOT NULL DEFAULT 0 COMMENT '排名',
    category VARCHAR(20) DEFAULT 'general' COMMENT '词类(general/positive/negative/gift/stream)',
    trend_direction VARCHAR(10) DEFAULT 'stable' COMMENT '趋势(up/down/stable)',
    date DATE NOT NULL COMMENT '统计日期',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_date (streamer_id, date),
    INDEX idx_word_date (word, date),
    INDEX idx_date (date),
    INDEX idx_rank (rank_num),
    UNIQUE KEY uk_streamer_word_date (streamer_id, word, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='热词统计表';

-- 创建观众活跃度热力图表
CREATE TABLE IF NOT EXISTS viewer_activity_heatmap (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    date DATE NOT NULL COMMENT '日期',
    hour TINYINT NOT NULL COMMENT '小时(0-23)',
    barrage_count INT NOT NULL DEFAULT 0 COMMENT '弹幕数量',
    active_users INT NOT NULL DEFAULT 0 COMMENT '活跃用户数',
    avg_content_length DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均内容长度',
    gift_count INT NOT NULL DEFAULT 0 COMMENT '礼物数量',
    gift_value DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '礼物价值',
    engagement_score DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '参与度分数',
    activity_level VARCHAR(10) DEFAULT 'normal' COMMENT '活跃度级别(high/medium/low)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_date (streamer_id, date),
    INDEX idx_date_hour (date, hour),
    INDEX idx_activity_level (activity_level),
    UNIQUE KEY uk_streamer_date_hour (streamer_id, date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='观众活跃度热力图表';

-- 创建情感分析表
CREATE TABLE IF NOT EXISTS sentiment_analysis (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    date DATE NOT NULL COMMENT '日期',
    hour TINYINT NOT NULL COMMENT '小时(0-23)',
    total_barrages INT NOT NULL DEFAULT 0 COMMENT '总弹幕数',
    positive_count INT NOT NULL DEFAULT 0 COMMENT '正面情感数量',
    negative_count INT NOT NULL DEFAULT 0 COMMENT '负面情感数量',
    neutral_count INT NOT NULL DEFAULT 0 COMMENT '中性情感数量',
    positive_ratio DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '正面情感占比(%)',
    negative_ratio DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '负面情感占比(%)',
    sentiment_score DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '情感分数',
    dominant_sentiment VARCHAR(10) DEFAULT 'neutral' COMMENT '主导情感(positive/negative/neutral)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_date (streamer_id, date),
    INDEX idx_date_hour (date, hour),
    INDEX idx_sentiment (dominant_sentiment),
    UNIQUE KEY uk_streamer_date_hour (streamer_id, date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='情感分析表';

-- 创建主播综合表现表
CREATE TABLE IF NOT EXISTS streamer_performance_daily (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    streamer_name VARCHAR(128) NOT NULL COMMENT '主播名称',
    date DATE NOT NULL COMMENT '日期',
    total_barrages BIGINT NOT NULL DEFAULT 0 COMMENT '总弹幕数',
    unique_viewers INT NOT NULL DEFAULT 0 COMMENT '独立观众数',
    total_gift_value DECIMAL(15,2) NOT NULL DEFAULT 0.00 COMMENT '总礼物价值',
    avg_engagement_score DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '平均参与度分数',
    performance_grade CHAR(1) DEFAULT 'D' COMMENT '表现等级(A/B/C/D)',
    top_words TEXT COMMENT 'TOP热词(JSON格式)',
    sentiment_summary TEXT COMMENT '情感分析摘要',
    peak_hours VARCHAR(100) COMMENT '高峰时段(逗号分隔)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_streamer_date (streamer_id, date),
    INDEX idx_date (date),
    INDEX idx_grade (performance_grade),
    UNIQUE KEY uk_streamer_date (streamer_id, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='主播综合表现表';

-- 创建数据质量监控表
CREATE TABLE IF NOT EXISTS data_quality_monitor (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    check_date DATE NOT NULL COMMENT '检查日期',
    check_type VARCHAR(50) NOT NULL COMMENT '检查类型',
    record_count BIGINT NOT NULL DEFAULT 0 COMMENT '记录数',
    streamer_count INT NOT NULL DEFAULT 0 COMMENT '主播数',
    user_count INT NOT NULL DEFAULT 0 COMMENT '用户数',
    data_volume_level VARCHAR(10) DEFAULT 'normal' COMMENT '数据量级别',
    completeness_score DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '完整性分数',
    quality_status VARCHAR(20) DEFAULT 'normal' COMMENT '质量状态',
    issues TEXT COMMENT '问题描述',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- 索引
    INDEX idx_check_date (check_date),
    INDEX idx_check_type (check_type),
    INDEX idx_quality_status (quality_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据质量监控表';

-- 插入示例数据（可选）
INSERT INTO barrage_summary (streamer_id, streamer_name, minute_time, barrage_count, unique_user_count, total_gift_value, avg_content_length) VALUES
('streamer_001', '主播A', DATE_SUB(NOW(), INTERVAL 1 MINUTE), 150, 80, 25.50, 12.3),
('streamer_002', '主播B', DATE_SUB(NOW(), INTERVAL 1 MINUTE), 200, 120, 45.80, 15.6),
('streamer_003', '主播C', DATE_SUB(NOW(), INTERVAL 1 MINUTE), 80, 45, 12.30, 10.2);

-- 创建存储过程：自动清理过期数据
DELIMITER //
CREATE PROCEDURE cleanup_expired_data()
BEGIN
    DECLARE thirty_days_ago DATETIME;
    SET thirty_days_ago = DATE_SUB(NOW(), INTERVAL 30 DAY);

    -- 清理30天前的分钟聚合数据
    DELETE FROM barrage_summary WHERE minute_time < thirty_days_ago;

    -- 清理30天前的小时聚合数据
    DELETE FROM barrage_hourly_stats WHERE hour_time < thirty_days_ago;

    -- 清理90天前的热词统计数据
    DELETE FROM hot_words_stats WHERE date < DATE_SUB(NOW(), INTERVAL 90 DAY);

    -- 清理90天前的活跃度热力图数据
    DELETE FROM viewer_activity_heatmap WHERE date < DATE_SUB(NOW(), INTERVAL 90 DAY);

    -- 清理90天前情感分析数据
    DELETE FROM sentiment_analysis WHERE date < DATE_SUB(NOW(), INTERVAL 90 DAY);

    SELECT '数据清理完成' as result;
END //
DELIMITER ;

-- 创建事件：每天凌晨3点执行数据清理
CREATE EVENT IF NOT EXISTS daily_data_cleanup
ON SCHEDULE EVERY 1 DAY
STARTS TIMESTAMP(CURDATE() + INTERVAL 1 DAY, '03:00:00')
DO CALL cleanup_expired_data();

-- 启用事件调度器
SET GLOBAL event_scheduler = ON;