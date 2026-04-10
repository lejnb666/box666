# 部署指南

## 🚀 快速部署

### 使用Docker Compose（推荐）

```bash
# 克隆项目
git clone https://github.com/yourusername/digital-person-chat.git
cd digital-person-chat

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置必要的配置

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 手动部署

#### 1. 数据库准备

```sql
-- 创建数据库
CREATE DATABASE digital_person CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户表
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    persona_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建对话历史表
CREATE TABLE conversation_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    message_type ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### 2. 后端服务部署

```bash
# 编译项目
cd digital-person-backend
mvn clean package -DskipTests

# 配置application-prod.properties
server.port=8080

# 数据源配置
spring.datasource.url=jdbc:mysql://localhost:3306/digital_person?useSSL=false&serverTimezone=UTC
spring.datasource.username=your_username
spring.datasource.password=your_password

# Redis配置
spring.redis.host=localhost
spring.redis.port=6379

# JWT配置
jwt.secret=your_jwt_secret_key
jwt.expiration=86400000

# 启动服务
java -jar target/digital-person-backend-1.0.0.jar \
  --spring.profiles.active=prod \
  --spring.config.location=classpath:/application-prod.properties
```

#### 3. Python服务部署

##### RAG引擎

```bash
# 进入RAG引擎目录
cd rag-engine

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 准备数据
mkdir -p data
# 将清洗后的对话数据放入 data/cleaned_conversations.jsonl

# 启动服务
python rag_server.py
```

##### Agent工具服务

```bash
# 进入Agent工具目录
cd agent-tools

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python agent_server.py
```

#### 4. 前端部署

```bash
# 进入前端目录
cd digital-person-frontend

# 安装依赖
npm install

# 构建生产版本
npm run build:h5

# 部署到Web服务器（如Nginx）
# 将 dist/build/h5 目录内容复制到Web服务器
```

## 🐳 Docker部署

### 构建Docker镜像

#### 后端镜像

```dockerfile
# Dockerfile.backend
FROM openjdk:17-jdk-slim

WORKDIR /app

# 复制JAR文件
COPY target/digital-person-backend-1.0.0.jar app.jar

# 暴露端口
EXPOSE 8080

# 启动应用
ENTRYPOINT ["java", "-jar", "app.jar"]
```

构建命令：
```bash
docker build -f Dockerfile.backend -t digital-person-backend:latest .
```

#### Python服务镜像

```dockerfile
# Dockerfile.rag
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y gcc

# 复制代码
COPY rag-engine/ .

# 安装Python依赖
RUN pip install -r requirements.txt

# 暴露端口
EXPOSE 5000

# 启动服务
CMD ["python", "rag_server.py"]
```

构建命令：
```bash
docker build -f Dockerfile.rag -t digital-person-rag:latest .
```

### Docker Compose配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 后端服务
  backend:
    image: digital-person-backend:latest
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/digital_person
      - SPRING_DATASOURCE_USERNAME=root
      - SPRING_DATASOURCE_PASSWORD=root
      - SPRING_REDIS_HOST=redis
    depends_on:
      - mysql
      - redis
    networks:
      - digital-person-network

  # RAG引擎
  rag-engine:
    image: digital-person-rag:latest
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    networks:
      - digital-person-network

  # Agent工具服务
  agent-tools:
    image: digital-person-agent:latest
    ports:
      - "5001:5001"
    networks:
      - digital-person-network

  # MySQL数据库
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: digital_person
      MYSQL_USER: digital_person
      MYSQL_PASSWORD: digital_person
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - digital-person-network

  # Redis缓存
  redis:
    image: redis:6.0-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - digital-person-network

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend:/usr/share/nginx/html
    depends_on:
      - backend
    networks:
      - digital-person-network

volumes:
  mysql_data:
  redis_data:

networks:
  digital-person-network:
    driver: bridge
```

### Nginx配置

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8080;
    }

    upstream rag {
        server rag-engine:5000;
    }

    upstream agent {
        server agent-tools:5001;
    }

    server {
        listen 80;
        server_name localhost;

        # 前端静态文件
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        # 后端API
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # RAG服务
        location /rag/ {
            proxy_pass http://rag/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Agent服务
        location /agent/ {
            proxy_pass http://agent/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## 🔧 环境变量配置

### 后端环境变量

```bash
# .env.backend
SPRING_PROFILES_ACTIVE=prod
SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/digital_person
SPRING_DATASOURCE_USERNAME=digital_person
SPRING_DATASOURCE_PASSWORD=digital_person
SPRING_REDIS_HOST=redis
SPRING_REDIS_PORT=6379
JWT_SECRET=your_jwt_secret_key_here
JWT_EXPIRATION=86400000
LLM_API_KEY=your_deepseek_api_key
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
```

### Python服务环境变量

```bash
# .env.rag
RAG_DATA_PATH=/app/data/cleaned_conversations.jsonl
RAG_INDEX_PATH=/app/data/vector_index.faiss
MODEL_NAME=paraphrase-multilingual-MiniLM-L12-v2
```

```bash
# .env.agent
AGENT_TOOLS_CONFIG=/app/config/tools.json
LOG_LEVEL=INFO
```

## 📊 监控和日志

### 健康检查

```bash
# 后端健康检查
curl http://localhost:8080/actuator/health

# RAG服务健康检查
curl http://localhost:5000/health

# Agent服务健康检查
curl http://localhost:5001/health
```

### 日志管理

```bash
# 查看Docker容器日志
docker-compose logs -f backend
docker-compose logs -f rag-engine
docker-compose logs -f agent-tools

# 后端日志配置 (logback-spring.xml)
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/application.log</file>
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>logs/application.%d{yyyy-MM-dd}.log</fileNamePattern>
            <maxHistory>30</maxHistory>
        </rollingPolicy>
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="FILE" />
    </root>
</configuration>
```

## 🔒 安全配置

### SSL证书配置

```bash
# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx.key -out nginx.crt

# 在Nginx中启用HTTPS
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    # 其他配置...
}
```

### 防火墙配置

```bash
# 开放必要的端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 5000/tcp
sudo ufw allow 5001/tcp

# 启用防火墙
sudo ufw enable
```

## 🚨 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查MySQL服务状态
docker-compose logs mysql

   # 手动测试连接
   mysql -h localhost -u digital_person -p digital_person
   ```

2. **Redis连接问题**
   ```bash
   # 检查Redis服务
   docker-compose exec redis redis-cli ping

   # 查看Redis日志
   docker-compose logs redis
   ```

3. **Python依赖安装失败**
   ```bash
   # 确保系统依赖已安装
   apt-get update && apt-get install -y gcc python3-dev

   # 重新安装依赖
   pip install --no-cache-dir -r requirements.txt
   ```

4. **内存不足**
   ```bash
   # 增加Docker内存限制
   # 在docker-compose.yml中添加
   services:
     rag-engine:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

## 📈 性能优化

### 后端优化

```properties
# application-prod.properties
# JVM参数
JAVA_OPTS=-Xms512m -Xmx1024m -XX:+UseG1GC

# 数据库连接池
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5

# Redis连接池
spring.redis.lettuce.pool.max-active=20
spring.redis.lettuce.pool.max-idle=10
```

### 前端优化

```javascript
// vue.config.js
module.exports = {
  productionSourceMap: false,
  configureWebpack: {
    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            name: 'chunk-vendors',
            test: /[\\/]node_modules[\\/]/,
            priority: 10,
            chunks: 'initial'
          }
        }
      }
    }
  }
}
```

## 🔄 更新和维护

### 滚动更新

```bash
# 更新单个服务
docker-compose pull backend
docker-compose up -d --no-deps backend

# 更新所有服务
docker-compose pull
docker-compose up -d
```

### 数据备份

```bash
# 备份MySQL数据
docker-compose exec mysql mysqldump -u root -proot digital_person > backup.sql

# 备份Redis数据
docker-compose exec redis redis-cli SAVE
# 备份文件位于 /var/lib/redis/dump.rdb

# 备份向量数据库
cp -r data/vector_index.faiss data/metadata.json /backup/
```

### 监控脚本

```bash
#!/bin/bash
# monitor.sh

echo "=== 系统监控 ==="
date
echo ""

echo "=== Docker容器状态 ==="
docker-compose ps
echo ""

echo "=== 资源使用情况 ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

echo "=== 最新日志 ==="
docker-compose logs --tail=10 backend
```

## 🎯 扩展建议

1. **水平扩展**：使用Kubernetes部署多个后端实例
2. **负载均衡**：在前端添加负载均衡器
3. **CDN加速**：为前端静态资源配置CDN
4. **监控告警**：集成Prometheus + Grafana监控
5. **日志分析**：使用ELK栈进行日志分析

---

**部署完成后，访问 http://your-domain.com 开始使用数字人聊天系统！**