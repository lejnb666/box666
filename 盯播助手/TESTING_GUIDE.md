# 盯播助手全链路测试指南

本文档详细说明了如何测试盯播助手的完整生命周期数据流。

## 系统架构概述

盯播助手的完整数据流包括以下组件：

1. **前端 (Uni-app)** - 用户配置监控任务
2. **Java 后端** - 处理业务逻辑，管理任务，与数据库和消息队列交互
3. **RabbitMQ** - 消息中间件，传递任务消息
4. **Python 爬虫服务** - 消费消息，执行监控任务，抓取直播数据
5. **微信订阅消息** - 向用户推送通知

## 测试环境准备

### 1. 启动服务

#### Java 后端服务
```bash
cd stream-backend-java
mvn spring-boot:run
```

#### Python 爬虫服务
```bash
cd stream-spider-python
python main.py
```

#### RabbitMQ 服务
```bash
# 如果使用Docker
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management

# 或者使用docker-compose
docker-compose -f docker/docker-compose.yml up -d
```

#### 前端小程序
```bash
cd stream-mini-app
# 使用HBuilderX或微信开发者工具启动
```

### 2. 验证服务状态

- Java 后端: http://localhost:8080/health
- Python 服务: http://localhost:5000/health
- RabbitMQ 管理界面: http://localhost:15672 (用户名: guest, 密码: guest)

## 完整生命周期测试流程

### 测试场景：创建开播提醒任务

#### 步骤 1: 前端创建任务

1. **打开小程序**，进入