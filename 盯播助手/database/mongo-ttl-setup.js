// MongoDB TTL索引配置脚本
// 执行方式: mongo "mongodb://mongo_admin:mongo_password@localhost:27017/stream_monitor" mongo-ttl-setup.js

// 切换到stream_monitor数据库
use stream_monitor;

// 1. 创建弹幕数据TTL索引（7天过期）
db.barrage.createIndex(
    { "timestamp": 1 },
    {
        expireAfterSeconds: 604800,  // 7天 = 7 * 24 * 60 * 60 = 604800秒
        name: "barrage_ttl_index",
        background: true
    }
);

// 2. 创建小时聚合数据集合（永久保存）
db.createCollection("barrage_hourly_aggregation", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["streamer_id", "streamer_name", "hour_time", "barrage_count"],
            properties: {
                streamer_id: {
                    bsonType: "string",
                    description: "主播ID"
                },
                streamer_name: {
                    bsonType: "string",
                    description: "主播名称"
                },
                hour_time: {
                    bsonType: "date",
                    description: "小时时间戳"
                },
                barrage_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "弹幕数量"
                },
                unique_user_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "独立用户数"
                },
                total_gift_value: {
                    bsonType: "double",
                    minimum: 0,
                    description: "礼物总价值"
                },
                avg_content_length: {
                    bsonType: "double",
                    minimum: 0,
                    description: "平均弹幕长度"
                }
            }
        }
    }
});

// 3. 创建日聚合数据TTL索引（1年过期）
db.createCollection("barrage_daily_aggregation", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["streamer_id", "streamer_name", "date", "total_barrage_count"],
            properties: {
                streamer_id: {
                    bsonType: "string",
                    description: "主播ID"
                },
                streamer_name: {
                    bsonType: "string",
                    description: "主播名称"
                },
                date: {
                    bsonType: "date",
                    description: "日期"
                },
                total_barrage_count: {
                    bsonType: "int",
                    minimum: 0,
                    description: "总弹幕数量"
                },
                total_unique_users: {
                    bsonType: "int",
                    minimum: 0,
                    description: "总独立用户数"
                },
                total_gift_value: {
                    bsonType: "double",
                    minimum: 0,
                    description: "总礼物价值"
                }
            }
        }
    }
});

db.barrage_daily_aggregation.createIndex(
    { "date": 1 },
    {
        expireAfterSeconds: 31536000,  // 1年 = 365 * 24 * 60 * 60 = 31536000秒
        name: "daily_aggregation_ttl_index",
        background: true
    }
);

// 4. 创建热词统计数据集合（永久保存）
db.createCollection("hot_words_statistics", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["streamer_id", "streamer_name", "date", "words"],
            properties: {
                streamer_id: {
                    bsonType: "string",
                    description: "主播ID"
                },
                streamer_name: {
                    bsonType: "string",
                    description: "主播名称"
                },
                date: {
                    bsonType: "date",
                    description: "统计日期"
                },
                words: {
                    bsonType: "array",
                    description: "热词列表",
                    items: {
                        bsonType: "object",
                        required: ["word", "count", "rank"],
                        properties: {
                            word: {
                                bsonType: "string",
                                description: "词语"
                            },
                            count: {
                                bsonType: "int",
                                minimum: 1,
                                description: "出现次数"
                            },
                            rank: {
                                bsonType: "int",
                                minimum: 1,
                                description: "排名"
                            }
                        }
                    }
                }
            }
        }
    }
});

// 5. 创建活跃度热力图数据集合（永久保存）
db.createCollection("viewer_activity_heatmap", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["streamer_id", "streamer_name", "date", "hourly_data"],
            properties: {
                streamer_id: {
                    bsonType: "string",
                    description: "主播ID"
                },
                streamer_name: {
                    bsonType: "string",
                    description: "主播名称"
                },
                date: {
                    bsonType: "date",
                    description: "统计日期"
                },
                hourly_data: {
                    bsonType: "array",
                    description: "每小时活跃度数据",
                    items: {
                        bsonType: "object",
                        required: ["hour", "barrage_count", "active_users"],
                        properties: {
                            hour: {
                                bsonType: "int",
                                minimum: 0,
                                maximum: 23,
                                description: "小时(0-23)"
                            },
                            barrage_count: {
                                bsonType: "int",
                                minimum: 0,
                                description: "弹幕数量"
                            },
                            active_users: {
                                bsonType: "int",
                                minimum: 0,
                                description: "活跃用户数"
                            },
                            avg_content_length: {
                                bsonType: "double",
                                minimum: 0,
                                description: "平均内容长度"
                            },
                            gift_count: {
                                bsonType: "int",
                                minimum: 0,
                                description: "礼物数量"
                            }
                        }
                    }
                }
            }
        }
    }
});

// 6. 创建情感分析数据集合（永久保存）
db.createCollection("sentiment_analysis", {
    validator: {
        $jsonSchema: {
            bsonType: "object",
            required: ["streamer_id", "streamer_name", "date", "sentiment_data"],
            properties: {
                streamer_id: {
                    bsonType: "string",
                    description: "主播ID"
                },
                streamer_name: {
                    bsonType: "string",
                    description: "主播名称"
                },
                date: {
                    bsonType: "date",
                    description: "统计日期"
                },
                sentiment_data: {
                    bsonType: "array",
                    description: "情感分析数据",
                    items: {
                        bsonType: "object",
                        required: ["hour", "positive", "negative", "neutral"],
                        properties: {
                            hour: {
                                bsonType: "int",
                                minimum: 0,
                                maximum: 23,
                                description: "小时(0-23)"
                            },
                            positive: {
                                bsonType: "int",
                                minimum: 0,
                                description: "正面情感数量"
                            },
                            negative: {
                                bsonType: "int",
                                minimum: 0,
                                description: "负面情感数量"
                            },
                            neutral: {
                                bsonType: "int",
                                minimum: 0,
                                description: "中性情感数量"
                            }
                        }
                    }
                }
            }
        }
    }
});

// 7. 创建索引以提高查询性能
db.barrage.createIndex({ "streamer_id": 1, "timestamp": -1 });
db.barrage.createIndex({ "user_id": 1, "timestamp": -1 });
db.barrage.createIndex({ "platform": 1, "timestamp": -1 });

db.barrage_hourly_aggregation.createIndex({ "streamer_id": 1, "hour_time": -1 });
db.barrage_daily_aggregation.createIndex({ "streamer_id": 1, "date": -1 });
db.hot_words_statistics.createIndex({ "streamer_id": 1, "date": -1 });
db.viewer_activity_heatmap.createIndex({ "streamer_id": 1, "date": -1 });
db.sentiment_analysis.createIndex({ "streamer_id": 1, "date": -1 });

print("MongoDB TTL索引和集合创建完成！");

// 8. 验证TTL索引创建
var indexes = db.barrage.getIndexes();
print("\n=== barrage集合索引 ===");
indexes.forEach(function(index) {
    printjson(index);
});

var dailyIndexes = db.barrage_daily_aggregation.getIndexes();
print("\n=== barrage_daily_aggregation集合索引 ===");
dailyIndexes.forEach(function(index) {
    printjson(index);
});

print("\nTTL配置完成。原始弹幕数据将自动7天后删除，日聚合数据将自动1年后删除。");