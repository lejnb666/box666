# 大数据架构演进与离线分析设计方案

## 1. 架构概述

### 1.1 当前架构分析
现有系统已经构建了良好的基础架构：
- **MySQL**: 存储结构化数据（用户信息、监控任务配置等）
- **MongoDB**: 存储实时弹幕数据（已具备）
- **Redis**: 缓存和会话管理
- **RabbitMQ**: 消息队列处理
- **Java后端**: Spring Boot + MyBatis-Plus
- **Python服务**: 爬虫和AI分析

### 1.2 目标架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   实时采集层     │    │   实时处理层     │    │   批处理层       │
│                 │    │                 │    │                 │
│  直播弹幕采集   │───▶│  MongoDB实时    │───▶│   HDFS存储      │
│  Python爬虫     │    │  存储(TTL)      │    │   (历史数据)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                      ┌─────────────────┐    ┌─────────────────┐
                      │   实时聚合层     │    │   离线计算层     │
                      │                 │    │                 │
                      │ MySQL聚合摘要   │    │   Hive/Spark    │
                      │ (每分钟统计)    │    │   (T+1分析)     │
                      └─────────────────┘    └─────────────────┘
                              │                        │
                              └───────────┬────────────┘
                                          ▼
                                 ┌─────────────────┐
                                 │   应用服务层     │
                                 │                 │
                                 │   API服务       │
                                 │   实时+离线数据  │
                                 └─────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │   前端展示层     │
                                 │                 │
                                 │   实时仪表板     │
                                 │   离线分析报告   │
                                 └─────────────────┘
```

## 2. 数据存储架构演进

### 2.1 MongoDB TTL策略设计

```javascript
// barrage-collection TTL索引设置
// 原始弹幕数据保留7天
db.barrage.createIndex({"timestamp": 1}, {expireAfterSeconds: 604800})

// barrage-hourly-aggregation 聚合数据永久保留
db.barrage_hourly.createIndex({"_id": 1})

// barrage-daily-aggregation 日聚合数据保留1年
db.barrage_daily.createIndex({"date": 1}, {expireAfterSeconds: 31536000})
```

### 2.2 数据分层存储策略

| 数据类型 | 存储位置 | 保留策略 | 用途 |
|---------|---------|---------|------|
| 原始弹幕 | MongoDB | 7天TTL | 实时监控、短期分析 |
| 分钟聚合 | MySQL | 永久 | 实时仪表板、趋势分析 |
| 小时聚合 | MongoDB | 永久 | 中期分析、报表 |
| 日聚合 | MongoDB | 1年 | 长期趋势分析 |
| 历史明细 | HDFS | 永久 | 离线深度分析 |

## 3. 离线分析流水线设计

### 3.1 数据抽取流程

```python
# data_extractor.py - 从MongoDB抽取数据到HDFS
def extract_daily_data():
    """
    每日凌晨执行，抽取前一天的弹幕数据
    """
    yesterday = datetime.now() - timedelta(days=1)
    start_time = yesterday.replace(hour=0, minute=0, second=0)
    end_time = yesterday.replace(hour=23, minute=59, second=59)
    
    # 从MongoDB查询数据
    barrage_data = mongo_db.barrage.find({
        "timestamp": {
            "$gte": start_time,
            "$lte": end_time
        }
    })
    
    # 转换为Parquet格式（列式存储，适合分析）
    df = pd.DataFrame(list(barrage_data))
    df.to_parquet(f"hdfs://namenode:9000/barrage_data/{yesterday.strftime('%Y/%m/%d')}/barrage.parquet")
```

### 3.2 Hive数据仓库设计

```sql
-- 创建弹幕数据外部表
CREATE EXTERNAL TABLE barrage_data (
    _id STRING,
    streamer_id STRING,
    streamer_name STRING,
    user_id STRING,
    user_name STRING,
    content STRING,
    timestamp TIMESTAMP,
    barrage_type STRING,
    gift_value DOUBLE,
    platform STRING
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 'hdfs://namenode:9000/barrage_data/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY'
);

-- 创建分区（每日自动执行）
ALTER TABLE barrage_data ADD PARTITION (year=2024, month=1, day=15)
LOCATION 'hdfs://namenode:9000/barrage_data/2024/01/15/';
```

## 4. 离线分析任务设计

### 4.1 热词分析

```sql
-- 主播全天热词统计
CREATE OR REPLACE VIEW hot_words_daily AS
SELECT 
    streamer_id,
    streamer_name,
    year, month, day,
    word,
    COUNT(*) as word_count,
    ROW_NUMBER() OVER (PARTITION BY streamer_id, year, month, day ORDER BY COUNT(*) DESC) as rank
FROM (
    SELECT 
        streamer_id,
        streamer_name,
        year, month, day,
        EXPLODE(SPLIT(LOWER(content), ' ')) as word
    FROM barrage_data
    WHERE year = YEAR(CURRENT_DATE - 1)
      AND month = MONTH(CURRENT_DATE - 1)
      AND day = DAY(CURRENT_DATE - 1)
      AND LENGTH(TRIM(content)) > 0
) words
WHERE LENGTH(word) > 1
  AND word NOT IN ('的', '了', '是', '我', '你', '在', '有', '不', '这', '就', '都', '也', '和', '要', '会', '能', '可以', '很', '好', '太', '真', '啊', '哦', '嗯')
GROUP BY streamer_id, streamer_name, year, month, day, word;

-- 获取TOP10热词
SELECT * FROM hot_words_daily WHERE rank <= 10;
```

### 4.2 观众活跃度分析

```sql
-- 观众活跃度热力图（按小时统计）
CREATE OR REPLACE VIEW viewer_activity_heatmap AS
SELECT 
    streamer_id,
    streamer_name,
    year, month, day,
    HOUR(timestamp) as hour,
    COUNT(*) as barrage_count,
    COUNT(DISTINCT user_id) as active_users,
    AVG(CHAR_LENGTH(content)) as avg_content_length,
    SUM(CASE WHEN gift_value > 0 THEN 1 ELSE 0 END) as gift_count
FROM barrage_data
WHERE year = YEAR(CURRENT_DATE - 1)
  AND month = MONTH(CURRENT_DATE - 1)
  AND day = DAY(CURRENT_DATE - 1)
GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp)
ORDER BY hour;
```

### 4.3 弹幕情感分析

```sql
-- 情感走势分析（需要结合AI服务的情感分析结果）
CREATE OR REPLACE VIEW sentiment_trend AS
SELECT 
    streamer_id,
    streamer_name,
    year, month, day,
    HOUR(timestamp) as hour,
    sentiment_type,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY streamer_id, year, month, day, HOUR(timestamp)) as percentage
FROM (
    SELECT 
        *,
        CASE 
            WHEN content LIKE '%好%' OR content LIKE '%棒%' OR content LIKE '%赞%' OR content LIKE '%666%' OR content LIKE '%厉害%' THEN 'positive'
            WHEN content LIKE '%差%' OR content LIKE '%烂%' OR content LIKE '%垃圾%' OR content LIKE '%无语%' OR content LIKE '%失望%' THEN 'negative'
            ELSE 'neutral'
        END as sentiment_type
    FROM barrage_data
    WHERE year = YEAR(CURRENT_DATE - 1)
      AND month = MONTH(CURRENT_DATE - 1)
      AND day = DAY(CURRENT_DATE - 1)
) with_sentiment
GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp), sentiment_type
ORDER BY hour, sentiment_type;
```

## 5. 技术栈选型

### 5.1 Hadoop生态系统

| 组件 | 版本 | 用途 | 配置建议 |
|------|------|------|----------|
| Hadoop HDFS | 3.3.6 | 分布式存储 | 3节点集群，每个节点16GB内存 |
| Hive | 3.1.3 | 数据仓库 | 元数据存储使用MySQL |
| Spark | 3.4.1 | 离线计算 | 与Hive集成，用于复杂分析 |
| ZooKeeper | 3.8.2 | 协调服务 | 3节点集群 |
| Airflow | 2.7.2 | 任务调度 | 管理ETL任务依赖 |

### 5.2 实时聚合服务

```java
// BarrageAggregationService.java
@Service
@Slf4j
public class BarrageAggregationService {
    
    @Autowired
    private MongoTemplate mongoTemplate;
    
    @Autowired
    private JdbcTemplate jdbcTemplate;
    
    /**
     * 每分钟执行一次聚合
     */
    @Scheduled(cron = "0 * * * * ?")
    public void aggregateMinuteData() {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime minuteStart = now.withSecond(0).withNano(0);
        LocalDateTime minuteEnd = minuteStart.plusMinutes(1);
        
        // 聚合MongoDB中的原始数据
        Aggregation aggregation = Aggregation.newAggregation(
            Aggregation.match(Criteria.where("timestamp").
                gte(Date.from(minuteStart.atZone(ZoneId.systemDefault()).toInstant())).
                lt(Date.from(minuteEnd.atZone(ZoneId.systemDefault()).toInstant()))),
            Aggregation.group("streamerId", "streamerName")
                .count().as("barrageCount")
                .sum("giftValue").as("totalGiftValue")
                .addToSet("userId").as("uniqueUsers")
                .avg("contentLength").as("avgContentLength"),
            Aggregation.project()
                .andExpression("_id.streamerId").as("streamerId")
                .andExpression("_id.streamerName").as("streamerName")
                .and("barrageCount").as("barrageCount")
                .and("totalGiftValue").as("totalGiftValue")
                .andArraySize("uniqueUsers").as("uniqueUserCount")
                .and("avgContentLength").as("avgContentLength")
                .and(minuteStart.toString()).as("minuteTime")
        );
        
        AggregationResults<BarrageMinuteSummary> results = 
            mongoTemplate.aggregate(aggregation, "barrage", BarrageMinuteSummary.class);
        
        // 保存到MySQL
        for (BarrageMinuteSummary summary : results.getMappedResults()) {
            saveToMySQL(summary);
        }
    }
    
    private void saveToMySQL(BarrageMinuteSummary summary) {
        String sql = """
            INSERT INTO barrage_summary 
            (streamer_id, streamer_name, minute_time, barrage_count, 
             unique_user_count, total_gift_value, avg_content_length, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
            ON DUPLICATE KEY UPDATE
            barrage_count = VALUES(barrage_count),
            unique_user_count = VALUES(unique_user_count),
            total_gift_value = VALUES(total_gift_value),
            avg_content_length = VALUES(avg_content_length)
            """;
        
        jdbcTemplate.update(sql,
            summary.getStreamerId(),
            summary.getStreamerName(),
            summary.getMinuteTime(),
            summary.getBarrageCount(),
            summary.getUniqueUserCount(),
            summary.getTotalGiftValue(),
            summary.getAvgContentLength()
        );
    }
}
```

## 6. 部署架构

### 6.1 Docker化部署配置

```yaml
# hadoop-cluster.yml
version: '3.8'

services:
  # Hadoop NameNode
  namenode:
    image: bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8
    container_name: namenode
    restart: always
    ports:
      - "9870:9870"  # Web UI
      - "9000:9000"  # HDFS
    environment:
      - CLUSTER_NAME=stream-analysis
    volumes:
      - namenode_data:/hadoop/dfs/name
    networks:
      - bigdata_network

  # Hadoop DataNodes
  datanode1:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    container_name: datanode1
    restart: always
    environment:
      - CORE_CONF_fs_defaultFS=hdfs://namenode:9000
    volumes:
      - datanode1_data:/hadoop/dfs/data
    depends_on:
      - namenode
    networks:
      - bigdata_network

  datanode2:
    image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
    container_name: datanode2
    restart: always
    environment:
      - CORE_CONF_fs_defaultFS=hdfs://namenode:9000
    volumes:
      - datanode2_data:/hadoop/dfs/data
    depends_on:
      - namenode
    networks:
      - bigdata_network

  # Hive Server
  hive-server:
    image: bde2020/hive:2.3.9
    container_name: hive-server
    restart: always
    environment:
      - HIVE_CORE_CONF_javax_jdo_option_ConnectionURL=jdbc:mysql://hive-metastore:3306/metastore
      - HIVE_CORE_CONF_javax_jdo_option_ConnectionDriverName=com.mysql.cj.jdbc.Driver
      - HIVE_CORE_CONF_javax_jdo_option_ConnectionUserName=hive
      - HIVE_CORE_CONF_javax_jdo_option_ConnectionPassword=hive123
    depends_on:
      - hive-metastore
      - namenode
    ports:
      - "10000:10000"  # HiveServer2
    networks:
      - bigdata_network

  # Hive Metastore
  hive-metastore:
    image: mysql:8.0
    container_name: hive-metastore
    restart: always
    environment:
      - MYSQL_ROOT_PASSWORD=root123
      - MYSQL_DATABASE=metastore
      - MYSQL_USER=hive
      - MYSQL_PASSWORD=hive123
    volumes:
      - hive_metastore_data:/var/lib/mysql
    ports:
      - "3307:3306"
    networks:
      - bigdata_network

  # Apache Airflow
  airflow-webserver:
    image: apache/airflow:2.7.2
    container_name: airflow-webserver
    restart: always
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres/airflow
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
    depends_on:
      - airflow-postgres
    ports:
      - "8080:8080"
    networks:
      - bigdata_network

  airflow-postgres:
    image: postgres:13
    container_name: airflow-postgres
    restart: always
    environment:
      - POSTGRES_DB=airflow
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
    volumes:
      - airflow_postgres_data:/var/lib/postgresql/data
    networks:
      - bigdata_network

volumes:
  namenode_data:
  datanode1_data:
  datanode2_data:
  hive_metastore_data:
  airflow_postgres_data:

networks:
  bigdata_network:
    driver: bridge
```

## 7. 实施计划

### 第一阶段（1-2周）：基础架构搭建
1. 搭建Hadoop集群（开发环境）
2. 配置Hive数据仓库
3. 实现MongoDB TTL策略
4. 创建数据抽取脚本

### 第二阶段（2-3周）：核心功能开发
1. 实现实时聚合服务
2. 开发离线分析SQL脚本
3. 构建数据质量监控
4. 创建基础分析报表

### 第三阶段（2-3周）：系统集成
1. 集成Airflow任务调度
2. 开发API接口
3. 构建前端分析界面
4. 性能优化和压力测试

### 第四阶段（1-2周）：生产部署
1. 生产环境部署
2. 数据迁移
3. 监控告警配置
4. 文档完善

## 8. 预期效果

1. **性能提升**：MySQL压力降低80%，查询响应时间提升50%
2. **分析能力**：支持T+1的离线深度分析，包括热词、活跃度、情感分析
3. **扩展性**：支持PB级数据存储，横向扩展能力强
4. **实时性**：保持分钟级实时聚合能力
5. **成本优化**：通过TTL策略，存储成本降低60%

此架构设计将大大提升项目的技术深度，形成完整的大数据处理流水线，为后续更复杂的AI分析提供坚实基础。