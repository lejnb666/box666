# 盯播助手生产环境部署指南

## 🚀 部署概述

本指南详细介绍如何在生产环境中部署盯播助手系统，包括所有必要的配置、安全设置和性能优化。

## 📋 系统要求

### 硬件要求
- **CPU**: 至少4核，推荐8核或以上
- **内存**: 至少16GB，推荐32GB或以上
- **存储**: 至少500GB SSD，推荐1TB或以上
- **网络**: 至少100Mbps带宽

### 软件要求
- **操作系统**: Ubuntu 20.04 LTS 或 CentOS 8
- **Docker**: 20.10.0 或更高版本
- **Docker Compose**: 1.29.0 或更高版本
- **Java**: 17 或更高版本
- **Python**: 3.9 或更高版本

## 🔧 环境准备

### 1. 服务器初始化

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装必要工具
sudo apt install -y git curl wget vim htop net-tools

# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 2. 配置系统参数

```bash
# 优化内核参数
cat << EOF | sudo tee /etc/sysctl.d/99-stream-monitor.conf
# 网络优化
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 5000

# 内存优化
vm.swappiness = 10
vm.dirty_ratio = 60
vm.dirty_background_ratio = 2

# 文件描述符
fs.file-max = 2097152
EOF

sudo sysctl -p /etc/sysctl.d/99-stream-monitor.conf

# 配置用户限制
cat << EOF | sudo tee /etc/security/limits.d/99-stream-monitor.conf
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF
```

## 📦 应用部署

### 1. 获取代码

```bash
# 克隆项目
git clone <your-repository-url>
cd 盯播助手

# 切换到生产分支
git checkout production
```

### 2. 配置环境变量

创建生产环境配置文件：

```bash
# 创建环境变量文件
cat > .env.production << 'EOF'
# MySQL配置
MYSQL_ROOT_PASSWORD=your_strong_root_password
MYSQL_DATABASE=stream_monitor
MYSQL_USER=stream_user
MYSQL_PASSWORD=your_strong_user_password

# Redis配置
REDIS_PASSWORD=your_strong_redis_password

# MongoDB配置
MONGO_INITDB_ROOT_USERNAME=mongo_admin
MONGO_INITDB_ROOT_PASSWORD=your_strong_mongo_password
MONGO_INITDB_DATABASE=stream_monitor

# RabbitMQ配置
RABBITMQ_DEFAULT_USER=stream_user
RABBITMQ_DEFAULT_PASS=your_strong_rabbitmq_password

# 微信配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# AI API配置
AI_API_BASE_URL=https://api.deepseek.com
AI_API_KEY=your_ai_api_key

# JWT配置
JWT_SECRET=your_strong_jwt_secret_key_with_at_least_32_characters

# 域名配置
DOMAIN_NAME=your-domain.com
SSL_EMAIL=your-email@example.com
EOF
```

### 3. 配置SSL证书

```bash
# 创建SSL目录
mkdir -p docker/ssl

# 使用Let's Encrypt获取SSL证书（推荐）
sudo apt install -y certbot
sudo certbot certonly --standalone -d your-domain.com

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem docker/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem docker/ssl/
sudo chown $USER:$USER docker/ssl/*

# 设置证书自动续期
(crontab -l 2>/dev/null; echo "0 2 * * 1 certbot renew --quiet && docker-compose restart nginx") | crontab -
```

### 4. 配置Nginx

```nginx
# docker/nginx.conf
user nginx;
worker_processes auto;
worker_rlimit_nofile 65536;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # 基本配置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log;

    # 上游服务器
    upstream backend {
        server backend:8080;
        keepalive 32;
    }

    upstream python_service {
        server python-service:5000;
        keepalive 32;
    }

    # HTTP重定向到HTTPS
    server {
        listen 80;
        server_name your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL配置
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;

        # 安全头
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'self'; object-src 'none'" always;

        # 前端应用
        location / {
            root /usr/share/nginx/html;
            index index.html index.htm;
            try_files $uri $uri/ /index.html;
        }

        # Java后端API
        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # Python服务API
        location /python-api/ {
            proxy_pass http://python_service/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }

        # WebSocket支持
        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 监控和管理界面
        location /rabbitmq/ {
            proxy_pass http://rabbitmq:15672/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /grafana/ {
            proxy_pass http://grafana:3000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /prometheus/ {
            proxy_pass http://prometheus:9090/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 5. 启动服务

```bash
# 构建和启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 🔐 安全配置

### 1. 防火墙配置

```bash
# 安装并配置UFW
sudo apt install -y ufw

# 允许必要端口
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 3306/tcp    # MySQL (仅内网)
sudo ufw allow 6379/tcp    # Redis (仅内网)
sudo ufw allow 27017/tcp   # MongoDB (仅内网)
sudo ufw allow 5672/tcp    # RabbitMQ (仅内网)

# 启用防火墙
sudo ufw enable
sudo ufw status
```

### 2. 数据库安全

```sql
-- MySQL安全配置
-- 创建专用用户并限制权限
CREATE USER 'stream_monitor'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON stream_monitor.* TO 'stream_monitor'@'localhost';
FLUSH PRIVILEGES;

-- 定期备份
mysqldump -u stream_user -p stream_monitor > backup_$(date +%Y%m%d).sql
```

### 3. 应用安全

```yaml
# application-prod.yml 安全配置
spring:
  datasource:
    url: jdbc:mysql://mysql:3306/stream_monitor?useSSL=true&requireSSL=true&serverTimezone=UTC
    username: ${DB_USERNAME}
    password: ${DB_PASSWORD}

  redis:
    host: redis
    port: 6379
    password: ${REDIS_PASSWORD}
    ssl: true

  rabbitmq:
    host: rabbitmq
    port: 5672
    username: ${RABBITMQ_USERNAME}
    password: ${RABBITMQ_PASSWORD}
    ssl:
      enabled: true

jwt:
  secret: ${JWT_SECRET}
  expiration: 86400000  # 24小时
  refresh-expiration: 604800000  # 7天

security:
  cors:
    allowed-origins: https://your-domain.com
    allowed-methods: GET,POST,PUT,DELETE
    allowed-headers: '*'
    max-age: 3600
```

## 📊 监控和日志

### 1. 配置Prometheus监控

```yaml
# docker/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert.rules"

scrape_configs:
  - job_name: 'backend'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['backend:8080']

  - job_name: 'python-service'
    static_configs:
      - targets: ['python-service:5000']

  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['rabbitmq:15672']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 2. 配置日志轮转

```bash
# /etc/logrotate.d/stream-monitor
/var/log/stream-monitor/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root adm
    postrotate
        docker-compose restart backend python-service
    endscript
}
```

## 🔄 备份策略

### 1. 数据库备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/stream-monitor"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 创建备份目录
mkdir -p $BACKUP_DIR

# MySQL备份
docker exec stream_monitor_mysql mysqldump -u stream_user -p$MYSQL_PASSWORD stream_monitor > $BACKUP_DIR/mysql_$DATE.sql

# MongoDB备份
docker exec stream_monitor_mongodb mongodump --username mongo_admin --password $MONGO_PASSWORD --authenticationDatabase admin --db stream_monitor --out $BACKUP_DIR/mongo_$DATE

# 压缩备份
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/mysql_$DATE.sql $BACKUP_DIR/mongo_$DATE

# 清理旧备份
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# 上传到云存储（可选）
# aws s3 cp $BACKUP_DIR/backup_$DATE.tar.gz s3://your-bucket/backups/

echo "Backup completed: $BACKUP_DIR/backup_$DATE.tar.gz"
```

### 2. 设置定时备份

```bash
# 每天凌晨2点执行备份
(crontab -l 2>/dev/null; echo "0 2 * * * /path/to/backup.sh") | crontab -
```

## 🚨 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查Docker日志
docker-compose logs [service_name]

# 检查容器状态
docker-compose ps

# 重启特定服务
docker-compose restart [service_name]
```

#### 2. 数据库连接问题

```bash
# 检查MySQL连接
docker exec -it stream_monitor_mysql mysql -u stream_user -p

# 检查MongoDB连接
docker exec -it stream_monitor_mongodb mongo -u mongo_admin -p
```

#### 3. 性能问题

```bash
# 检查资源使用
docker stats

# 检查慢查询日志
docker exec -it stream_monitor_mysql tail -f /var/log/mysql/slow.log

# 检查应用性能
docker exec -it stream_monitor_backend jstat -gcutil [pid]
```

## 📈 性能优化

### 1. JVM优化

```dockerfile
# Java服务Docker优化
ENV JAVA_OPTS="-Xms2g -Xmx4g \
-XX:+UseG1GC \
-XX:MaxGCPauseMillis=200 \
-XX:+HeapDumpOnOutOfMemoryError \
-XX:HeapDumpPath=/app/logs \
-Djava.security.egd=file:/dev/./urandom"
```

### 2. 数据库优化

```sql
-- MySQL性能优化
SET GLOBAL innodb_buffer_pool_size = 8G;
SET GLOBAL innodb_log_file_size = 2G;
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
SET GLOBAL innodb_flush_method = O_DIRECT;

-- 添加索引
CREATE INDEX idx_barrage_timestamp ON barrage_data(timestamp);
CREATE INDEX idx_barrage_platform ON barrage_data(platform, room_id);
```

### 3. 缓存优化

```yaml
# Redis配置优化
redis:
  maxmemory: 4gb
  maxmemory-policy: allkeys-lru
  save: "900 1 300 10 60 10000"
  appendonly: yes
  appendfsync: everysec
```

## 🚀 部署检查清单

- [ ] 服务器硬件配置满足要求
- [ ] 操作系统和安全配置完成
- [ ] Docker和Docker Compose安装正确
- [ ] SSL证书配置正确
- [ ] 环境变量配置安全
- [ ] 防火墙规则设置正确
- [ ] 数据库用户权限配置正确
- [ ] 备份策略已实施
- [ ] 监控系统正常运行
- [ ] 日志轮转配置正确
- [ ] 性能测试通过
- [ ] 安全扫描无重大漏洞

## 📞 支持信息

**紧急联系**: [你的联系信息]
**监控面板**: https://your-domain.com/grafana
**文档**: https://your-domain.com/docs
**备份位置**: /backup/stream-monitor

---

**注意**: 请根据实际环境修改所有配置中的域名、密码和其他敏感信息。在生产环境部署前，建议先在测试环境进行充分测试。