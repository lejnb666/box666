# 大数据架构部署指南

## 项目概述

本项目已完成大数据架构的完整设计与实现，包括：

1. **数据存储架构演进**：MongoDB TTL策略 + MySQL聚合摘要 + HDFS历史存储
2. **离线分析流水线**：Hive数据仓库 + 热词分析 + 活跃度分析 + 情感分析
3. **实时聚合服务**：Java服务实现分钟级、小时级、日级数据聚合
4. **前端分析仪表板**：Vue.js实现的完整数据分析界面
5. **自动化任务调度**：Airflow管理的ETL流水线
6. **Docker化部署**：完整的容器化部署配置

## 部署环境要求

### 硬件要求
- **最低配置**：16GB内存，4核CPU，100GB存储
- **推荐配置**：32GB内存，8核CPU，500GB存储
- **生产环境**：64GB+内存，16核+CPU，1TB+存储

### 软件要求
- Docker 20.10+
- Docker Compose 1.29+
- 推荐操作系统：Ubuntu 20.04+ 或 CentOS 8+

## 部署步骤

### 第一阶段：基础环境准备

#### 1. 安装Docker和Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 将当前用户添加到docker组
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. 克隆项目代码

```bash
git clone <repository-url>
cd 盯播助手
```

#### 3. 配置环境变量

创建环境变量文件：

```bash
# .env文件
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret
AI_API_KEY=your_ai_api_key
JWT_SECRET=your_jwt_secret
AI_API_BASE_URL=https://api.example.com
```

### 第二阶段：启动现有服务

#### 1. 启动基础监控服务

```bash
# 进入docker目录
cd docker

# 启动基础服务（MySQL, MongoDB, Redis, RabbitMQ等）
docker-compose up -d

# 等待服务启动完成（约2-3分钟）
sleep 180

# 检查服务状态
docker-compose ps
```

#### 2. 配置MongoDB TTL索引

```bash
# 执行MongoDB TTL配置脚本
docker exec -i stream_monitor_mongodb mongo "mongodb://mongo_admin:mongo_password@localhost:27017/stream_monitor" < ../database/mongo-ttl-setup.js
```

#### 3. 创建MySQL聚合表

```bash
# 执行MySQL表创建脚本
docker exec -i stream_monitor_mysql mysql -ustream_user -pstream_password stream_monitor < ../database/create-barrage-summary-table.sql
```

### 第三阶段：启动大数据集群

#### 1. 启动Hadoop集群

```bash
# 启动大数据集群
docker-compose -f hadoop-cluster.yml up -d

# 等待集群启动（约5-10分钟）
sleep 600

# 检查集群状态
docker-compose -f hadoop-cluster.yml ps
```

#### 2. 验证HDFS状态

```bash
# 访问HDFS Web UI: http://localhost:9870
# 或在命令行检查
docker exec -it stream_namenode hdfs dfsadmin -report
```

#### 3. 初始化Hive元数据

```bash
# 创建Hive元数据数据库
docker exec -i stream_hive_metastore mysql -uroot -phive_root_password << EOF
CREATE DATABASE IF NOT EXISTS hive_metastore;
USE hive_metastore;
SOURCE /hive-schema-2.3.9.mysql.sql;
EOF
```

#### 4. 启动Airflow服务

```bash
# 初始化Airflow数据库
docker exec -it stream_airflow_webserver airflow db init

# 创建Airflow用户
docker exec -it stream_airflow_webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin123

# 启动Airflow服务
docker-compose -f hadoop-cluster.yml up -d airflow-webserver airflow-scheduler airflow-worker
```

### 第四阶段：配置和验证

#### 1. 配置Airflow连接

访问Airflow Web UI (http://localhost:8083)，配置以下连接：

- **MongoDB连接**：
  - Conn Id: `mongo_default`
  - Conn Type: `MongoDB`
  - Host: `mongodb`
  - Port: `27017`
  - Schema: `stream_monitor`
  - Login: `mongo_admin`
  - Password: `mongo_password`

- **HDFS连接**：
  - Conn Id: `hdfs_default`
  - Conn Type: `HDFS`
  - Host: `namenode`
  - Port: `9000`

- **Hive连接**：
  - Conn Id: `hive_default`
  - Conn Type: `Hive Server 2 Thrift`
  - Host: `hive-server`
  - Port: `10000`
  - Schema: `default`

#### 2. 部署DAG文件

```bash
# 复制DAG文件到Airflow
docker cp docker/airflow/dags/stream_analytics_pipeline.py stream_airflow_webserver:/opt/airflow/dags/

# 刷新Airflow DAG列表
docker exec -it stream_airflow_webserver airflow dags list
```

#### 3. 测试数据迁移服务

```bash
# 手动运行数据迁移测试
docker exec -it stream_data_migration python3 data-migration-service.py \
    --action range \
    --start-date 2024-01-01 \
    --end-date 2024-01-02
```

#### 4. 验证Hive表结构

```bash
# 连接到Hive
docker exec -it stream_hive_server beeline -u jdbc:hive2://localhost:10000

# 执行Hive DDL
source /scripts/hive-analysis-pipeline.sql;

# 验证表创建
SHOW TABLES;
DESCRIBE barrage_data;
```

### 第五阶段：启动应用服务

#### 1. 启动Java后端服务

```bash
# 构建并启动后端服务
cd stream-backend-java
./mvnw clean package -DskipTests
docker build -t stream-backend-java .

cd ../docker
docker-compose up -d backend
```

#### 2. 启动Python服务

```bash
cd ../stream-spider-python
docker build -t stream-spider-python .

cd ../docker
docker-compose up -d python-service
```

#### 3. 启动前端应用

```bash
cd ../stream-mini-app
# 根据前端框架文档进行构建和部署
npm install
npm run build
```

## 验证部署

### 1. 服务健康检查

```bash
# 检查所有服务状态
docker-compose ps
docker-compose -f hadoop-cluster.yml ps

# 检查日志
docker-compose logs --tail=50 backend
docker-compose -f hadoop-cluster.yml logs --tail=50 hive-server
```

### 2. 功能验证

#### 实时聚合验证
```bash
# 检查MySQL中的聚合数据
docker exec -it stream_monitor_mysql mysql -ustream_user -pstream_password stream_monitor -e "SELECT COUNT(*) FROM barrage_summary;"
```

#### 离线分析验证
```bash
# 手动触发Airflow DAG
docker exec -it stream_airflow_webserver airflow dags trigger stream_analytics_pipeline

# 检查DAG运行状态
docker exec -it stream_airflow_webserver airflow dags list-runs stream_analytics_pipeline
```

#### 前端验证
```
访问前端分析界面：
- 实时仪表板：http://localhost/analytics
- 检查数据概览、排行榜、热力图等功能
```

## 监控和维护

### 1. 监控界面

| 服务 | URL | 默认凭据 |
|------|-----|----------|
| HDFS NameNode | http://localhost:9870 | 无 |
| Hive Web UI | http://localhost:10002 | 无 |
| Spark Master | http://localhost:8080 | 无 |
| Airflow | http://localhost:8083 | admin/admin123 |
| Superset | http://localhost:8088 | admin/admin |
| Grafana | http://localhost:3000 | admin/admin123 |

### 2. 日志查看

```bash
# 查看特定服务日志
docker-compose logs -f backend
docker-compose -f hadoop-cluster.yml logs -f hive-server

# 查看数据迁移日志
docker exec -it stream_data_migration tail -f /app/logs/data_migration.log
```

### 3. 日常维护任务

#### 数据清理
```bash
# 手动执行数据清理存储过程
docker exec -it stream_monitor_mysql mysql -ustream_user -pstream_password stream_monitor -e "CALL cleanup_expired_data();"
```

#### 备份策略
```bash
# 备份MySQL数据
docker exec stream_monitor_mysql mysqldump -uroot -proot123 stream_monitor > backup_$(date +%Y%m%d).sql

# 备份MongoDB数据
docker exec stream_monitor_mongodb mongodump --uri="mongodb://mongo_admin:mongo_password@localhost:27017/stream_monitor" --out=/backup/$(date +%Y%m%d)
```

## 故障排除

### 常见问题

1. **Hadoop集群启动失败**
   - 检查内存是否充足（至少16GB）
   - 检查端口冲突
   - 查看NameNode日志：`docker logs stream_namenode`

2. **Airflow DAG不执行**
   - 检查Airflow Scheduler是否运行
   - 检查DAG文件语法：`docker exec -it stream_airflow_webserver python3 -m py_compile /opt/airflow/dags/stream_analytics_pipeline.py`
   - 检查连接配置

3. **Hive查询失败**
   - 检查Hive Metastore连接
   - 检查HDFS权限
   - 验证分区是否存在

4. **数据迁移失败**
   - 检查MongoDB连接
   - 检查HDFS空间
   - 查看迁移日志

### 性能优化

1. **HDFS配置优化**
   ```xml
   <!-- hadoop-config/hdfs-site.xml -->
   <property>
     <name>dfs.replication</name>
     <value>2</value>
   </property>
   <property>
     <name>dfs.blocksize</name>
     <value>134217728</value> <!-- 128MB -->
   </property>
   ```

2. **Hive性能优化**
   ```sql
   -- 启用向量化查询
   SET hive.vectorized.execution.enabled=true;
   SET hive.vectorized.execution.reduce.enabled=true;

   -- 启用并行执行
   SET hive.exec.parallel=true;
   SET hive.exec.parallel.thread.number=8;
   ```

3. **Airflow配置优化**
   ```python
   # airflow.cfg
   [core]
   parallelism = 32
   dag_concurrency = 16
   max_active_runs_per_dag = 16

   [scheduler]
   scheduler_heartbeat_sec = 5
   scheduler_health_check_threshold = 30
   ```

## 扩展和升级

### 水平扩展

1. **添加更多DataNode**
   ```yaml
   # hadoop-cluster.yml
   datanode4:
     image: bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8
     # ... 配置类似datanode1
   ```

2. **添加Spark Worker**
   ```yaml
   spark-worker3:
     image: bde2020/spark-worker:3.0.0-hadoop3.2
     # ... 配置类似worker1
   ```

### 功能扩展

1. **添加实时流处理**
   - 集成Apache Kafka
   - 添加Apache Flink
   - 实现实时分析功能

2. **增强AI分析**
   - 集成机器学习模型
   - 添加预测性分析
   - 实现智能推荐

3. **数据可视化增强**
   - 集成Apache Superset
   - 添加自定义图表
   - 实现交互式分析

## 安全配置

### 1. 网络安全
```bash
# 配置防火墙
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH
# 仅允许内网访问大数据端口
sudo ufw allow from 192.168.1.0/24 to any port 9000
```

### 2. 数据安全
```bash
# 启用MongoDB认证
# 在mongo-init.js中配置用户权限

# 启用HDFS权限
# 在hdfs-site.xml中配置
<property>
  <name>dfs.permissions.enabled</name>
  <value>true</value>
</property>
```

### 3. 应用安全
```bash
# 更新默认密码
# 修改所有默认凭据
# 启用HTTPS
# 配置JWT密钥
```

## 总结

本部署指南提供了从基础环境准备到生产部署的完整流程。系统采用微服务架构，支持水平扩展，具备完善的监控和维护机制。通过Docker容器化部署，确保了环境一致性和部署便利性。

系统已成功实现了：
- ✅ 海量弹幕数据的TTL存储策略
- ✅ 实时聚合分析（分钟级、小时级、日级）
- ✅ 离线大数据分析流水线
- ✅ 热词、活跃度、情感分析
- ✅ 自动化任务调度
- ✅ 可视化分析界面
- ✅ 完整的监控和维护体系

该系统为直播弹幕分析提供了强大的技术支撑，具备良好的扩展性和维护性。