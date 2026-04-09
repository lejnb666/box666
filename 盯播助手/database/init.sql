-- 盯播助手数据库初始化脚本
-- 创建时间: 2026-04-08

-- 创建数据库
CREATE DATABASE IF NOT EXISTS stream_monitor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE stream_monitor;

-- 用户信息表
CREATE TABLE IF NOT EXISTS user_info (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    openid VARCHAR(64) UNIQUE NOT NULL COMMENT '微信OpenID',
    nickname VARCHAR(100) COMMENT '用户昵称',
    avatar_url VARCHAR(500) COMMENT '用户头像URL',
    phone VARCHAR(20) COMMENT '手机号',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-正常',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_openid (openid),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- 主播配置表
CREATE TABLE IF NOT EXISTS streamer_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    streamer_id VARCHAR(64) NOT NULL COMMENT '主播ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台：bilibili、douyu、huya等',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    streamer_name VARCHAR(100) NOT NULL COMMENT '主播名称',
    avatar_url VARCHAR(500) COMMENT '主播头像',
    category VARCHAR(50) COMMENT '直播分类',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-正常',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_platform_room (platform, room_id),
    INDEX idx_streamer_id (streamer_id),
    INDEX idx_platform (platform),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='主播配置表';

-- 监控任务表
CREATE TABLE IF NOT EXISTS monitor_task (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    task_type VARCHAR(20) NOT NULL COMMENT '任务类型：live_start、product_launch、keyword_match等',
    keywords TEXT COMMENT '监控关键词，JSON格式',
    ai_analysis TINYINT DEFAULT 0 COMMENT '是否启用AI分析：0-否，1-是',
    notification_methods VARCHAR(100) DEFAULT 'wechat' COMMENT '通知方式：wechat、sms、email',
    do_not_disturb_start TIME COMMENT '免打扰开始时间',
    do_not_disturb_end TIME COMMENT '免打扰结束时间',
    status TINYINT DEFAULT 1 COMMENT '状态：0-暂停，1-运行中，2-已完成',
    last_triggered_at TIMESTAMP NULL COMMENT '最后触发时间',
    trigger_count INT DEFAULT 0 COMMENT '触发次数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES user_info(id) ON DELETE CASCADE,
    FOREIGN KEY (streamer_config_id) REFERENCES streamer_config(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_streamer_config_id (streamer_config_id),
    INDEX idx_status (status),
    INDEX idx_task_type (task_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监控任务表';

-- 推送历史记录表
CREATE TABLE IF NOT EXISTS push_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '推送ID',
    task_id BIGINT NOT NULL COMMENT '任务ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    trigger_type VARCHAR(50) NOT NULL COMMENT '触发类型',
    trigger_content TEXT COMMENT '触发内容',
    notification_method VARCHAR(20) NOT NULL COMMENT '通知方式',
    message_title VARCHAR(200) COMMENT '消息标题',
    message_content TEXT COMMENT '消息内容',
    ai_confidence FLOAT COMMENT 'AI分析置信度',
    status TINYINT DEFAULT 1 COMMENT '状态：0-失败，1-成功，2-已读',
    error_message TEXT COMMENT '错误信息',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    read_at TIMESTAMP NULL COMMENT '阅读时间',
    FOREIGN KEY (task_id) REFERENCES monitor_task(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user_info(id) ON DELETE CASCADE,
    FOREIGN KEY (streamer_config_id) REFERENCES streamer_config(id) ON DELETE CASCADE,
    INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_sent_at (sent_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推送历史记录表';

-- 弹幕数据表（用于AI分析和离线计算）
-- 注意：这是初期实现，生产环境建议使用MongoDB或Kafka+Hadoop架构
CREATE TABLE IF NOT EXISTS barrage_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '弹幕ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    user_id VARCHAR(64) NOT NULL COMMENT '弹幕用户ID',
    username VARCHAR(100) COMMENT '弹幕用户名',
    content TEXT NOT NULL COMMENT '弹幕内容',
    timestamp TIMESTAMP NOT NULL COMMENT '弹幕时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (streamer_config_id) REFERENCES streamer_config(id) ON DELETE CASCADE,
    INDEX idx_streamer_config_id (streamer_config_id),
    INDEX idx_platform_room (platform, room_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='弹幕数据表 - 生产环境建议迁移到MongoDB';

-- 弹幕摘要表（用于高频弹幕的聚合分析，减轻MySQL压力）
CREATE TABLE IF NOT EXISTS barrage_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '摘要ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    summary_minute TIMESTAMP NOT NULL COMMENT '统计分钟',
    barrage_count INT DEFAULT 0 COMMENT '弹幕总数',
    unique_users INT DEFAULT 0 COMMENT '独立用户数',
    hot_keywords JSON COMMENT '热词统计',
    sentiment_score FLOAT COMMENT '情感分析得分',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_streamer_minute (streamer_config_id, summary_minute),
    INDEX idx_platform_room_minute (platform, room_id, summary_minute)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='弹幕摘要表 - 用于快速统计分析';

-- 弹幕采样表（定期采样存储，避免全量数据膨胀）
CREATE TABLE IF NOT EXISTS barrage_sample (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '采样ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    sample_time TIMESTAMP NOT NULL COMMENT '采样时间',
    sample_rate DECIMAL(3,2) DEFAULT 1.00 COMMENT '采样率',
    content TEXT NOT NULL COMMENT '弹幕内容',
    user_level INT DEFAULT 0 COMMENT '用户等级',
    is_gift BOOLEAN DEFAULT FALSE COMMENT '是否为礼物弹幕',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_streamer_time (streamer_config_id, sample_time),
    INDEX idx_platform_room_time (platform, room_id, sample_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='弹幕采样表 - 降低存储压力';

-- 直播状态记录表
CREATE TABLE IF NOT EXISTS live_status_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    status TINYINT NOT NULL COMMENT '直播状态：0-未开播，1-直播中，2-停播',
    title VARCHAR(200) COMMENT '直播标题',
    category VARCHAR(50) COMMENT '直播分类',
    viewer_count INT DEFAULT 0 COMMENT '观看人数',
    start_time TIMESTAMP NULL COMMENT '开播时间',
    end_time TIMESTAMP NULL COMMENT '停播时间',
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    FOREIGN KEY (streamer_config_id) REFERENCES streamer_config(id) ON DELETE CASCADE,
    INDEX idx_streamer_config_id (streamer_config_id),
    INDEX idx_platform_room (platform, room_id),
    INDEX idx_recorded_at (recorded_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='直播状态记录表';

-- 商品监控记录表
CREATE TABLE IF NOT EXISTS product_monitor_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    streamer_config_id BIGINT NOT NULL COMMENT '主播配置ID',
    platform VARCHAR(20) NOT NULL COMMENT '平台',
    room_id VARCHAR(64) NOT NULL COMMENT '房间ID',
    product_name VARCHAR(200) NOT NULL COMMENT '商品名称',
    product_price DECIMAL(10,2) COMMENT '商品价格',
    original_price DECIMAL(10,2) COMMENT '原价',
    discount_info VARCHAR(100) COMMENT '折扣信息',
    launch_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上架时间',
    detected_by VARCHAR(20) NOT NULL COMMENT '检测方式：keyword、ai',
    FOREIGN KEY (streamer_config_id) REFERENCES streamer_config(id) ON DELETE CASCADE,
    INDEX idx_streamer_config_id (streamer_config_id),
    INDEX idx_platform_room (platform, room_id),
    INDEX idx_launch_time (launch_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品监控记录表';

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    config_key VARCHAR(100) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT NOT NULL COMMENT '配置值',
    config_desc VARCHAR(200) COMMENT '配置描述',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_config_key (config_key),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 插入系统默认配置
INSERT INTO system_config (config_key, config_value, config_desc) VALUES
('WECHAT_APP_ID', '', '微信小程序AppID'),
('WECHAT_APP_SECRET', '', '微信小程序AppSecret'),
('WECHAT_TEMPLATE_ID_LIVE_START', '', '开播提醒模板ID'),
('WECHAT_TEMPLATE_ID_PRODUCT_LAUNCH', '', '商品上架模板ID'),
('WECHAT_TEMPLATE_ID_KEYWORD_MATCH', '', '关键词匹配模板ID'),
('AI_API_BASE_URL', 'https://api.deepseek.com', 'AI API基础URL'),
('AI_API_KEY', '', 'AI API密钥'),
('AI_MODEL_NAME', 'deepseek-chat', 'AI模型名称'),
('CRAWLER_INTERVAL', '30', '爬虫抓取间隔（秒）'),
('BARRAGE_BUFFER_SIZE', '50', '弹幕分析缓冲区大小'),
('NOTIFICATION_RATE_LIMIT', '10', '通知频率限制（次/分钟）'),
('MAX_CONCURRENT_TASKS', '1000', '最大并发任务数');

-- 创建视图：用户监控统计
CREATE OR REPLACE VIEW user_monitor_stats AS
SELECT
    u.id as user_id,
    u.nickname,
    u.openid,
    COUNT(DISTINCT mt.id) as total_tasks,
    COUNT(DISTINCT CASE WHEN mt.status = 1 THEN mt.id END) as active_tasks,
    COUNT(DISTINCT sc.id) as monitored_streamers,
    COALESCE(SUM(mt.trigger_count), 0) as total_triggers,
    MAX(mt.last_triggered_at) as last_trigger_time
FROM user_info u
LEFT JOIN monitor_task mt ON u.id = mt.user_id
LEFT JOIN streamer_config sc ON mt.streamer_config_id = sc.id
WHERE u.status = 1
GROUP BY u.id, u.nickname, u.openid;

-- 创建视图：主播热度统计
CREATE OR REPLACE VIEW streamer_hot_stats AS
SELECT
    sc.id as streamer_config_id,
    sc.streamer_name,
    sc.platform,
    sc.category,
    COUNT(DISTINCT mt.user_id) as subscriber_count,
    COALESCE(AVG(lsl.viewer_count), 0) as avg_viewer_count,
    COUNT(DISTINCT CASE WHEN lsl.status = 1 THEN lsl.id END) as live_sessions_today,
    MAX(lsl.start_time) as last_live_start
FROM streamer_config sc
LEFT JOIN monitor_task mt ON sc.id = mt.streamer_config_id AND mt.status = 1
LEFT JOIN live_status_log lsl ON sc.id = lsl.streamer_config_id
    AND lsl.recorded_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
WHERE sc.status = 1
GROUP BY sc.id, sc.streamer_name, sc.platform, sc.category;

-- 添加注释
ALTER TABLE user_info COMMENT = '用户信息表 - 存储微信用户基本信息';
ALTER TABLE streamer_config COMMENT = '主播配置表 - 存储主播基本信息和平台配置';
ALTER TABLE monitor_task COMMENT = '监控任务表 - 用户创建的监控任务配置';
ALTER TABLE push_log COMMENT = '推送历史记录表 - 存储所有推送通知的历史记录';
ALTER TABLE barrage_data COMMENT = '弹幕数据表 - 存储抓取的弹幕数据，用于AI分析和离线计算';
ALTER TABLE live_status_log COMMENT = '直播状态记录表 - 记录主播的直播状态变化';
ALTER TABLE product_monitor_log COMMENT = '商品监控记录表 - 记录检测到的商品上架信息';
ALTER TABLE system_config COMMENT = '系统配置表 - 存储系统级别的配置参数';

-- 创建分区表（用于大数据量场景）
-- 注意：这里创建的是示例，实际使用时需要根据数据量评估是否需要分区
-- CREATE TABLE push_log_partitioned (
--     id BIGINT PRIMARY KEY AUTO_INCREMENT,
--     task_id BIGINT NOT NULL,
--     user_id BIGINT NOT NULL,
--     streamer_config_id BIGINT NOT NULL,
--     trigger_type VARCHAR(50) NOT NULL,
--     trigger_content TEXT,
--     notification_method VARCHAR(20) NOT NULL,
--     message_title VARCHAR(200),
--     message_content TEXT,
--     ai_confidence FLOAT,
--     status TINYINT DEFAULT 1,
--     error_message TEXT,
--     sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     read_at TIMESTAMP NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
-- PARTITION BY RANGE (YEAR(sent_at)) (
--     PARTITION p2024 VALUES LESS THAN (2025),
--     PARTITION p2025 VALUES LESS THAN (2026),
--     PARTITION p2026 VALUES LESS THAN (2027),
--     PARTITION p_future VALUES LESS THAN MAXVALUE
-- );

SELECT '数据库初始化完成' as message;