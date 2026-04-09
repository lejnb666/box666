# 盯播助手部署文档

## 系统要求

### 硬件要求
- **CPU**: 至少4核
- **内存**: 至少8GB RAM
- **存储**: 至少20GB可用空间
- **网络**: 稳定的网络连接，能够访问外部API

### 软件要求
- **操作系统**: Linux/Windows/macOS
- **Docker**: 20.10+
- **Docker Compose**: 2.20+
- **Git**: 2.0+

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd 盯播助手
```

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

### 3. 启动服务
```bash
# 使用部署脚本（推荐）
./deploy.sh --all

# 或者手动启动
cd docker
docker-compose up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose -f docker/docker-compose.yml ps

# 访问服务
curl http://localhost:8080/api/health
curl http://localhost:5000/health
```

## 详细配置

### 环境变量配置

编辑 `.env` 文件，配置以下参数：

```env
# 微信配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# AI服务配置
AI_API_BASE_URL=https://api.deepseek.com
AI_API_KEY=your_ai_api_key

# JWT配置
JWT_SECRET=your_jwt_secret_key_change_this_in_production

# 数据库配置（通常不需要修改）
DB_HOST=mysql
DB_PORT=3306
DB_NAME=stream_monitor
DB_USERNAME=stream_user
DB_PASSWORD=stream_password

# Redis配置（通常不需要修改）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# RabbitMQ配置（通常不需要修改）
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=stream_user
RABBITMQ_PASSWORD=stream_password
```

### 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| MySQL | 3306 | 数据库服务 |
| Redis | 6379 | 缓存服务 |
| RabbitMQ | 5672 | 消息队列 |
| RabbitMQ管理 | 15672 | 消息队列管理界面 |
| Spring Boot后端 | 8080 | 主API服务 |
| Python服务 | 5000 | 爬虫和AI服务 |
| Nginx | 80 | 反向代理 |
| Prometheus | 9090 | 监控服务 |
| Grafana | 3000 | 监控面板 |

## 部署方式

### 1. 开发环境部署

```bash
# 启动基础服务
./deploy.sh --all

# 查看日志
./deploy.sh --logs

# 重新构建并启动
./deploy.sh --build
./deploy.sh --start
```

### 2. 生产环境部署

#### 准备工作
1. 准备云服务器（推荐4核8GB以上配置）
2. 安装Docker和Docker Compose
3. 配置域名和SSL证书

#### 部署步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd 盯播助手

# 2. 配置生产环境变量
nano .env

# 3. 构建和启动服务
./deploy.sh --all

# 4. 配置域名解析
# 将域名指向服务器IP

# 5. 配置SSL证书（可选）
# 在docker/ssl目录放置证书文件
```

#### 生产环境优化

1. **数据库优化**
   - 配置主从复制
   - 设置定期备份
   - 优化查询性能

2. **缓存优化**
   - 增加Redis内存
   - 配置持久化策略
   - 设置合适的过期时间

3. **消息队列优化**
   - 增加队列消费者数量
   - 配置消息持久化
   - 监控队列状态

4. **应用优化**
   - 配置连接池
   - 启用Gzip压缩
   - 设置合理的超时时间

### 3. 高可用部署（可选）

#### 负载均衡
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  backend-1:
    image: stream-monitor-backend
    deploy:
      replicas: 2

  backend-2:
    image: stream-monitor-backend
    deploy:
      replicas: 2

  python-1:
    image: stream-monitor-python
    deploy:
      replicas: 3

  python-2:
    image: stream-monitor-python
    deploy:
      replicas: 3
```

#### 数据库主从复制
```sql
-- 主库配置
server-id = 1
log_bin = mysql-bin
binlog_do_db = stream_monitor

-- 从库配置
server-id = 2
relay-log = relay-bin
read_only = 1
```

## 监控和维护

### 监控面板

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin123)
- **RabbitMQ管理**: http://localhost:15672 (stream_user/stream_password)

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f docker/docker-compose.yml logs -f

# 查看特定服务日志
docker-compose -f docker/docker-compose.yml logs -f backend
docker-compose -f docker/docker-compose.yml logs -f python-service

# 查看宿主机日志文件
tail -f logs/backend/app.log
tail -f logs/python/app.log
```

### 数据备份

#### MySQL备份
```bash
# 备份数据库
docker-compose -f docker/docker-compose.yml exec mysql \
  mysqldump -u root -proot123 stream_monitor > backup.sql

# 恢复数据库
docker-compose -f docker/docker-compose.yml exec -T mysql \
  mysql -u root -proot123 stream_monitor < backup.sql
```

#### Redis备份
```bash
# Redis会自动持久化到磁盘
# 备份数据文件
cp -r data/redis /backup/redis-$(date +%Y%m%d)
```

### 服务管理

```bash
# 启动服务
./deploy.sh --start

# 停止服务
./deploy.sh --cleanup

# 重启特定服务
docker-compose -f docker/docker-compose.yml restart backend

# 更新服务
git pull
./deploy.sh --build
./deploy.sh --start
```

## 故障排除

### 常见问题

#### 1. 端口冲突
```bash
# 检查端口占用
netstat -tlnp | grep :8080

# 修改端口映射
docker-compose -f docker/docker-compose.yml -p stream-monitor up -d
```

#### 2. 数据库连接失败
```bash
# 检查MySQL服务状态
docker-compose -f docker/docker-compose.yml exec mysql mysqladmin ping

# 检查数据库用户权限
docker-compose -f docker/docker-compose.yml exec mysql mysql -u root -proot123
```

#### 3. 内存不足
```bash
# 查看容器资源使用
docker stats

# 调整容器资源限制
docker-compose -f docker/docker-compose.yml up -d --scale backend=2
```

#### 4. 网络问题
```bash
# 检查容器网络
docker network inspect stream_monitor_network

# 重新创建网络
docker network rm stream_monitor_network
docker-compose -f docker/docker-compose.yml up -d
```

### 性能调优

#### JVM调优（Spring Boot）
```bash
# 在Dockerfile中添加JVM参数
CMD ["java", "-Xms512m", "-Xmx2g", "-XX:+UseG1GC", "-jar", "target/app.jar"]
```

#### Python服务调优
```bash
# 增加Gunicorn工作进程
CMD ["gunicorn", "--workers", "8", "--worker-class", "gevent", "--worker-connections", "2000"]
```

#### 数据库调优
```sql
-- 优化InnoDB配置
innodb_buffer_pool_size = 2G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
```

## 安全建议

### 1. 网络安全
- 使用防火墙限制端口访问
- 配置SSL/TLS加密
- 使用私有网络隔离服务

### 2. 应用安全
- 定期更新依赖包
- 使用环境变量管理敏感信息
- 启用API认证和授权

### 3. 数据安全
- 定期备份重要数据
- 加密存储敏感信息
- 限制数据库访问权限

## 扩展开发

### 添加新的直播平台支持

1. 在Python服务中添加平台配置
2. 实现平台特定的爬虫逻辑
3. 更新数据库schema（如需要）
4. 添加前端界面支持

### 自定义AI分析

1. 在AI服务中添加新的分析类型
2. 配置系统提示词
3. 训练和优化模型
4. 测试分析效果

## 参考资源

- [Docker官方文档](https://docs.docker.com/)
- [Spring Boot官方文档](https://docs.spring.io/spring-boot/docs/)
- [Python官方文档](https://docs.python.org/3/)
- [MySQL官方文档](https://dev.mysql.com/doc/)
- [Redis官方文档](https://redis.io/documentation)
- [RabbitMQ官方文档](https://www.rabbitmq.com/documentation.html)