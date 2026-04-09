// MongoDB初始化脚本
// 创建时间: 2026/04/08

// 创建数据库用户
db = db.getSiblingDB('stream_monitor');

db.createUser({
  user: 'stream_user',
  pwd: 'stream_password',
  roles: [
    {
      role: 'readWrite',
      db: 'stream_monitor'
    }
  ]
});

// 创建弹幕数据集合
db.createCollection('barrage_data');

// 创建TTL索引，自动删除7天前的弹幕数据
db.barrage_data.createIndex({
  "timestamp": 1
}, {
  expireAfterSeconds: 604800, // 7天 = 7 * 24 * 60 * 60 = 604800秒
  name: "barrage_ttl_index"
});

// 创建复合索引以优化查询性能
db.barrage_data.createIndex({
  "platform": 1,
  "room_id": 1,
  "timestamp": -1
}, {
  name: "platform_room_timestamp_index"
});

db.barrage_data.createIndex({
  "user_id": 1,
  "timestamp": -1
}, {
  name: "user_timestamp_index"
});

db.barrage_data.createIndex({
  "content": "text"
}, {
  name: "content_text_index",
  weights: {
    "content": 10
  }
});

// 创建直播状态记录集合
db.createCollection('live_status_log');

db.live_status_log.createIndex({
  "platform": 1,
  "room_id": 1,
  "timestamp": -1
}, {
  name: "live_status_query_index"
});

db.live_status_log.createIndex({
  "timestamp": 1
}, {
  expireAfterSeconds: 2592000, // 30天过期
  name: "live_status_ttl_index"
});

// 创建商品监控记录集合
db.createCollection('product_monitor_log');

db.product_monitor_log.createIndex({
  "platform": 1,
  "room_id": 1,
  "detected_at": -1
}, {
  name: "product_monitor_query_index"
});

db.product_monitor_log.createIndex({
  "detected_at": 1
}, {
  expireAfterSeconds: 2592000, // 30天过期
  name: "product_monitor_ttl_index"
});

// 创建系统日志集合
db.createCollection('system_logs');

db.system_logs.createIndex({
  "timestamp": 1
}, {
  expireAfterSeconds: 7776000, // 90天过期
  name: "system_logs_ttl_index"
});

db.system_logs.createIndex({
  "level": 1,
  "timestamp": -1
}, {
  name: "log_level_timestamp_index"
});

// 创建性能监控数据集合
db.createCollection('performance_metrics');

db.performance_metrics.createIndex({
  "timestamp": 1
}, {
  expireAfterSeconds: 2592000, // 30天过期
  name: "metrics_ttl_index"
});

db.performance_metrics.createIndex({
  "service": 1,
  "metric_type": 1,
  "timestamp": -1
}, {
  name: "metrics_query_index"
});

print('MongoDB初始化完成');