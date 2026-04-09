-- ============================================
-- 离线分析流水线 - Hive SQL脚本
-- 用于大数据架构的T+1离线分析
-- ============================================

-- 使用stream_analysis数据库
USE stream_analysis;

-- =======================
-- 1. 基础数据表维护
-- =======================

-- 创建分区维护存储过程
CREATE OR REPLACE PROCEDURE maintain_partitions()
BEGIN
    -- 自动添加最近7天的分区
    DECLARE i INT DEFAULT 0;
    WHILE i < 7 DO
        DECLARE partition_date DATE;
        SET partition_date = DATE_SUB(CURRENT_DATE, i);

        -- 检查分区是否存在
        SET @sql = CONCAT(
            'ALTER TABLE barrage_data ADD IF NOT EXISTS PARTITION ',
            '(year=', YEAR(partition_date),
            ', month=', LPAD(MONTH(partition_date), 2, '0'),
            ', day=', LPAD(DAY(partition_date), 2, '0'),
            ') LOCATION ''hdfs://namenode:9000/barrage_data/',
            YEAR(partition_date), '/',
            LPAD(MONTH(partition_date), 2, '0'), '/',
            LPAD(DAY(partition_date), 2, '0'), "/''"
        );

        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;

        SET i = i + 1;
    END WHILE;
END;

-- =======================
-- 2. 热词分析模块
-- =======================

-- 创建热词分析函数
CREATE OR REPLACE FUNCTION extract_chinese_words(content STRING)
RETURNS ARRAY<STRING>
LANGUAGE JAVA
USING JAR 'hdfs://namenode:9000/jars/chinese-word-segmenter.jar';

-- 创建热词统计视图（按天）
CREATE OR REPLACE VIEW hot_words_daily_detailed AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    word,
    word_count,
    word_frequency,
    rank(),
    trend_direction,
    category
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY streamer_id, year, month, day ORDER BY word_count DESC) as rank,
        LAG(word_count, 1, 0) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day) as prev_count,
        CASE
            WHEN word_count > LAG(word_count, 1, 0) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day) THEN 'up'
            WHEN word_count < LAG(word_count, 1, 0) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day) THEN 'down'
            ELSE 'stable'
        END as trend_direction,
        CASE
            WHEN word IN ('666', '厉害', '牛逼', '强', '棒', '好', '赞', '喜欢', '爱', '支持') THEN 'positive'
            WHEN word IN ('垃圾', '差', '烂', '无语', '失望', '讨厌', '恶心', '烦', '无聊') THEN 'negative'
            WHEN word IN ('礼物', '打赏', '刷', '送', '火箭', '跑车', '鲜花') THEN 'gift'
            WHEN word IN ('主播', '主播名', '直播间', '直播', '观看', '粉丝') THEN 'stream'
            ELSE 'general'
        END as category
    FROM (
        SELECT
            streamer_id,
            streamer_name,
            year, month, day,
            word,
            COUNT(*) as word_count,
            COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY streamer_id, year, month, day) as word_frequency
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                year, month, day,
                EXPLODE(SPLIT(REGEXP_REPLACE(LOWER(content), '[^\\u4e00-\\u9fa5a-zA-Z0-9]', ' '), ' ')) as word
            FROM barrage_data
            WHERE LENGTH(TRIM(content)) > 0
              AND year = YEAR(CURRENT_DATE - 1)
              AND month = MONTH(CURRENT_DATE - 1)
              AND day = DAY(CURRENT_DATE - 1)
        ) words
        WHERE LENGTH(word) > 1
          AND word NOT IN (
              '的', '了', '是', '我', '你', '在', '有', '不', '这', '就', '都', '也', '和', '要', '会', '能', '可以', '很', '好', '太', '真', '啊', '哦', '嗯',
              '一个', '这个', '那个', '什么', '怎么', '为什么', '然后', '但是', '所以', '因为', '如果', '虽然', '但是', '而且', '或者', '还是', '就是', '不是', '没有', '不会', '可以', '可能', '应该', '一定', '真的', '非常', '特别', '比较', '有点', '一些', '一点'
          )
        GROUP BY streamer_id, streamer_name, year, month, day, word
    ) word_stats
) final_stats
WHERE rank <= 50;

-- 创建热词趋势分析视图
CREATE OR REPLACE VIEW hot_words_trend AS
SELECT
    streamer_id,
    streamer_name,
    word,
    year, month, day,
    word_count,
    word_frequency,
    trend_direction,
    category,
    moving_avg_3day,
    moving_avg_7day,
    growth_rate
FROM (
    SELECT
        *,
        AVG(word_count) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as moving_avg_3day,
        AVG(word_count) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as moving_avg_7day,
        (word_count - LAG(word_count, 7, 0) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day)) * 100.0 / NULLIF(LAG(word_count, 7, 0) OVER (PARTITION BY streamer_id, word ORDER BY year, month, day), 0) as growth_rate
    FROM hot_words_daily_detailed
) trend_data
WHERE word_count >= 5;  -- 只显示出现5次以上的热词

-- =======================
-- 3. 观众活跃度分析模块
-- =======================

-- 创建观众活跃度热力图（按小时）
CREATE OR REPLACE VIEW viewer_activity_heatmap_hourly AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    hour,
    barrage_count,
    active_users,
    avg_content_length,
    gift_count,
    gift_value,
    engagement_score,
    activity_level
FROM (
    SELECT
        *,
        ROUND(
            (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2 + avg_content_length * 0.1) /
            MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2 + avg_content_length * 0.1) OVER (PARTITION BY streamer_id, year, month, day) * 100,
            2
        ) as engagement_score,
        CASE
            WHEN barrage_count >= PERCENTILE(barrage_count, 0.8) OVER (PARTITION BY streamer_id, year, month, day) THEN 'high'
            WHEN barrage_count >= PERCENTILE(barrage_count, 0.5) OVER (PARTITION BY streamer_id, year, month, day) THEN 'medium'
            ELSE 'low'
        END as activity_level
    FROM (
        SELECT
            streamer_id,
            streamer_name,
            year, month, day,
            HOUR(timestamp) as hour,
            COUNT(*) as barrage_count,
            COUNT(DISTINCT user_id) as active_users,
            AVG(content_length) as avg_content_length,
            SUM(CASE WHEN gift_value > 0 THEN 1 ELSE 0 END) as gift_count,
            SUM(gift_value) as gift_value
        FROM barrage_data
        WHERE year = YEAR(CURRENT_DATE - 1)
          AND month = MONTH(CURRENT_DATE - 1)
          AND day = DAY(CURRENT_DATE - 1)
        GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp)
    ) hourly_stats
) final_stats
ORDER BY streamer_id, year, month, day, hour;

-- 创建观众留存分析视图
CREATE OR REPLACE VIEW viewer_retention_analysis AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    new_users,
    returning_users,
    retention_rate,
    avg_session_duration,
    peak_hours
FROM (
    SELECT
        *,
        ROUND(returning_users * 100.0 / NULLIF(new_users + returning_users, 0), 2) as retention_rate,
        CASE
            WHEN hour IN (20, 21, 22, 23) THEN 'peak'
            WHEN hour IN (19, 24, 1, 2) THEN 'sub_peak'
            ELSE 'normal'
        END as peak_hours
    FROM (
        SELECT
            streamer_id,
            streamer_name,
            year, month, day,
            COUNT(DISTINCT CASE WHEN is_new_user = 1 THEN user_id END) as new_users,
            COUNT(DISTINCT CASE WHEN is_new_user = 0 THEN user_id END) as returning_users,
            AVG(session_duration) as avg_session_duration,
            HOUR(timestamp) as hour
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                year, month, day,
                user_id,
                timestamp,
                CASE
                    WHEN LAG(timestamp, 1) OVER (PARTITION BY streamer_id, user_id ORDER BY timestamp) IS NULL
                         OR DATEDIFF(timestamp, LAG(timestamp, 1) OVER (PARTITION BY streamer_id, user_id ORDER BY timestamp)) > 7
                    THEN 1
                    ELSE 0
                END as is_new_user,
                UNIX_TIMESTAMP(timestamp) - UNIX_TIMESTAMP(LAG(timestamp, 1) OVER (PARTITION BY streamer_id, user_id ORDER BY timestamp)) as session_duration
            FROM barrage_data
            WHERE year = YEAR(CURRENT_DATE - 1)
              AND month = MONTH(CURRENT_DATE - 1)
              AND day = DAY(CURRENT_DATE - 1)
        ) user_sessions
        GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp)
    ) daily_stats
) final_stats;

-- =======================
-- 4. 弹幕情感分析模块
-- =======================

-- 创建情感词典表
CREATE TABLE IF NOT EXISTS sentiment_dictionary (
    word STRING,
    sentiment_type STRING,
    sentiment_score DOUBLE,
    category STRING
);

-- 插入情感词典数据
INSERT OVERWRITE TABLE sentiment_dictionary VALUES
-- 正面情感词汇
('好', 'positive', 0.8, 'general'),
('棒', 'positive', 0.9, 'general'),
('赞', 'positive', 0.8, 'general'),
('666', 'positive', 1.0, 'internet'),
('厉害', 'positive', 0.9, 'general'),
('牛逼', 'positive', 0.9, 'internet'),
('强', 'positive', 0.8, 'general'),
('喜欢', 'positive', 0.8, 'emotion'),
('爱', 'positive', 0.9, 'emotion'),
('支持', 'positive', 0.7, 'action'),
('开心', 'positive', 0.8, 'emotion'),
('高兴', 'positive', 0.8, 'emotion'),
('满意', 'positive', 0.7, 'emotion'),
('完美', 'positive', 0.9, 'general'),
('精彩', 'positive', 0.8, 'general'),

-- 负面情感词汇
('差', 'negative', -0.8, 'general'),
('烂', 'negative', -0.9, 'general'),
('垃圾', 'negative', -1.0, 'general'),
('无语', 'negative', -0.7, 'emotion'),
('失望', 'negative', -0.8, 'emotion'),
('讨厌', 'negative', -0.8, 'emotion'),
('恶心', 'negative', -0.9, 'emotion'),
('烦', 'negative', -0.7, 'emotion'),
('无聊', 'negative', -0.6, 'emotion'),
('生气', 'negative', -0.8, 'emotion'),
('愤怒', 'negative', -0.9, 'emotion'),
('难过', 'negative', -0.7, 'emotion'),
('伤心', 'negative', -0.8, 'emotion'),
('崩溃', 'negative', -0.9, 'emotion');

-- 创建情感分析视图
CREATE OR REPLACE VIEW sentiment_analysis_detailed AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    hour,
    total_barrages,
    positive_count,
    negative_count,
    neutral_count,
    positive_ratio,
    negative_ratio,
    sentiment_score,
    dominant_sentiment
FROM (
    SELECT
        *,
        ROUND(positive_count * 100.0 / total_barrages, 2) as positive_ratio,
        ROUND(negative_count * 100.0 / total_barrages, 2) as negative_ratio,
        ROUND((positive_count - negative_count) * 100.0 / total_barrages, 2) as sentiment_score,
        CASE
            WHEN positive_count > negative_count AND positive_count > neutral_count THEN 'positive'
            WHEN negative_count > positive_count AND negative_count > neutral_count THEN 'negative'
            ELSE 'neutral'
        END as dominant_sentiment
    FROM (
        SELECT
            streamer_id,
            streamer_name,
            year, month, day,
            HOUR(timestamp) as hour,
            COUNT(*) as total_barrages,
            SUM(CASE WHEN sentiment_sum > 0 THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_sum < 0 THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_sum = 0 THEN 1 ELSE 0 END) as neutral_count
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                year, month, day,
                timestamp,
                content,
                SUM(COALESCE(sd.sentiment_score, 0)) as sentiment_sum
            FROM barrage_data bd
            LEFT JOIN (
                SELECT
                    streamer_id, year, month, day, timestamp, content,
                    EXPLODE(SPLIT(LOWER(content), ' ')) as word
                FROM barrage_data
                WHERE year = YEAR(CURRENT_DATE - 1)
                  AND month = MONTH(CURRENT_DATE - 1)
                  AND day = DAY(CURRENT_DATE - 1)
            ) words ON bd.streamer_id = words.streamer_id
                AND bd.year = words.year
                AND bd.month = words.month
                AND bd.day = words.day
                AND bd.timestamp = words.timestamp
            LEFT JOIN sentiment_dictionary sd ON words.word = sd.word
            WHERE bd.year = YEAR(CURRENT_DATE - 1)
              AND bd.month = MONTH(CURRENT_DATE - 1)
              AND bd.day = DAY(CURRENT_DATE - 1)
            GROUP BY streamer_id, streamer_name, year, month, day, timestamp, content
        ) sentiment_scores
        GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp)
    ) hourly_sentiment
) final_sentiment;

-- =======================
-- 5. 综合分析报表
-- =======================

-- 创建主播综合表现报表
CREATE OR REPLACE VIEW streamer_performance_daily AS
SELECT
    s.streamer_id,
    s.streamer_name,
    s.year, s.month, s.day,
    s.total_barrages,
    s.unique_viewers,
    s.total_gift_value,
    s.avg_engagement_score,
    hw.top_words,
    sa.sentiment_summary,
    va.peak_hours,
    s.performance_grade
FROM (
    SELECT
        streamer_id,
        streamer_name,
        year, month, day,
        COUNT(*) as total_barrages,
        COUNT(DISTINCT user_id) as unique_viewers,
        SUM(gift_value) as total_gift_value,
        AVG(
            (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) /
            MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) OVER (PARTITION BY streamer_id, year, month, day) * 100
        ) as avg_engagement_score,
        CASE
            WHEN AVG(
                (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) /
                MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) OVER (PARTITION BY streamer_id, year, month, day) * 100
            ) >= 80 THEN 'A'
            WHEN AVG(
                (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) /
                MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) OVER (PARTITION BY streamer_id, year, month, day) * 100
            ) >= 60 THEN 'B'
            WHEN AVG(
                (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) /
                MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2) OVER (PARTITION BY streamer_id, year, month, day) * 100
            ) >= 40 THEN 'C'
            ELSE 'D'
        END as performance_grade
    FROM barrage_data
    LEFT JOIN viewer_activity_heatmap_hourly vah ON
        barrage_data.streamer_id = vah.streamer_id AND
        barrage_data.year = vah.year AND
        barrage_data.month = vah.month AND
        barrage_data.day = vah.day
    WHERE barrage_data.year = YEAR(CURRENT_DATE - 1)
      AND barrage_data.month = MONTH(CURRENT_DATE - 1)
      AND barrage_data.day = DAY(CURRENT_DATE - 1)
    GROUP BY streamer_id, streamer_name, year, month, day
) s
LEFT JOIN (
    SELECT
        streamer_id, year, month, day,
        CONCAT_WS(',', COLLECT_LIST(CONCAT(word, '(', word_count, ')'))) as top_words
    FROM hot_words_daily_detailed
    WHERE rank <= 5
    GROUP BY streamer_id, year, month, day
) hw ON s.streamer_id = hw.streamer_id AND s.year = hw.year AND s.month = hw.month AND s.day = hw.day
LEFT JOIN (
    SELECT
        streamer_id, year, month, day,
        CONCAT('正面:', MAX(positive_ratio), '%,负面:', MAX(negative_ratio), '%,主导情感:', MAX(dominant_sentiment)) as sentiment_summary
    FROM sentiment_analysis_detailed
    GROUP BY streamer_id, year, month, day
) sa ON s.streamer_id = sa.streamer_id AND s.year = sa.year AND s.month = sa.month AND s.day = sa.day
LEFT JOIN (
    SELECT
        streamer_id, year, month, day,
        CONCAT_WS(',', COLLECT_LIST(CONCAT(hour, '时'))) as peak_hours
    FROM viewer_activity_heatmap_hourly
    WHERE activity_level = 'high'
    GROUP BY streamer_id, year, month, day
) va ON s.streamer_id = va.streamer_id AND s.year = va.year AND s.month = va.month AND s.day = va.day;

-- =======================
-- 6. 数据质量监控
-- =======================

-- 创建数据质量检查视图
CREATE OR REPLACE VIEW data_quality_check AS
SELECT
    'data_volume' as check_type,
    year, month, day,
    COUNT(*) as record_count,
    COUNT(DISTINCT streamer_id) as streamer_count,
    COUNT(DISTINCT user_id) as user_count,
    CASE
        WHEN COUNT(*) < 1000 THEN 'low'
        WHEN COUNT(*) < 10000 THEN 'medium'
        ELSE 'high'
    END as data_volume_level
FROM barrage_data
WHERE year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
GROUP BY year, month, day

UNION ALL

SELECT
    'data_completeness' as check_type,
    year, month, day,
    COUNT(*) as record_count,
    SUM(CASE WHEN streamer_id IS NULL OR streamer_id = '' THEN 1 ELSE 0 END) as missing_streamer,
    SUM(CASE WHEN user_id IS NULL OR user_id = '' THEN 1 ELSE 0 END) as missing_user,
    CASE
        WHEN SUM(CASE WHEN streamer_id IS NULL OR streamer_id = '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 5 THEN 'low'
        WHEN SUM(CASE WHEN streamer_id IS NULL OR streamer_id = '' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) > 1 THEN 'medium'
        ELSE 'high'
    END as completeness_level
FROM barrage_data
WHERE year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
GROUP BY year, month, day;

-- =======================
-- 7. 常用查询示例
-- =======================

-- 查询昨日TOP10主播
SELECT
    streamer_id,
    streamer_name,
    total_barrages,
    unique_viewers,
    total_gift_value,
    performance_grade
FROM streamer_performance_daily
WHERE year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
ORDER BY total_barrages DESC
LIMIT 10;

-- 查询热词趋势
SELECT
    word,
    word_count,
    trend_direction,
    growth_rate
FROM hot_words_trend
WHERE streamer_id = 'streamer_001'
  AND year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
ORDER BY word_count DESC
LIMIT 20;

-- 查询观众活跃度热力图
SELECT
    hour,
    barrage_count,
    active_users,
    engagement_score,
    activity_level
FROM viewer_activity_heatmap_hourly
WHERE streamer_id = 'streamer_001'
  AND year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
ORDER BY hour;