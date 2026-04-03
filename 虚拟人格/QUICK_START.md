# 🚀 快速开始指南

## 🎯 30分钟快速体验

### 环境准备

确保你已安装以下软件：
- Java 17+
- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- Redis 6.0+

### 步骤1：启动后端服务 (5分钟)

```bash
# 进入后端目录
cd digital-person-backend

# 编译项目
mvn clean package -DskipTests

# 启动服务（使用默认配置）
java -jar target/digital-person-backend-1.0.0.jar

# 服务启动后访问：http://localhost:8080/actuator/health
```

### 步骤2：启动Python服务 (10分钟)

#### RAG引擎

```bash
# 进入RAG引擎目录
cd rag-engine

# 安装依赖
pip install -r requirements.txt

# 生成示例数据
python ../data-pipeline/sample_data_generator.py

# 启动RAG服务
python rag_server.py
```

#### Agent工具服务

```bash
# 新开一个终端
cd agent-tools

# 安装依赖
pip install -r requirements.txt

# 启动Agent服务
python agent_server.py
```

### 步骤3：启动前端 (5分钟)

```bash
# 进入前端目录
cd digital-person-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev:h5

# 访问前端：http://localhost:8080 (H5模式)
```

### 步骤4：测试功能 (10分钟)

1. **打开浏览器**访问前端界面
2. **发送消息**测试基础聊天功能
3. **测试工具调用**：
   - 发送："现在几点了？"
   - 发送："帮我搜索Vue项目"
   - 发送："北京天气怎么样？"
   - 发送："计算2+3*4"

## 🐳 使用Docker快速部署

### 一键启动

```bash
# 克隆项目
git clone https://github.com/yourusername/digital-person-chat.git
cd digital-person-chat

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 访问服务

- **前端界面**: http://localhost
- **后端API**: http://localhost/api
- **RAG服务**: http://localhost:5000
- **Agent服务**: http://localhost:5001

## 📊 验证安装

### 检查服务状态

```bash
# 检查后端服务
curl http://localhost:8080/actuator/health

# 检查RAG服务
curl http://localhost:5000/health

# 检查Agent服务
curl http://localhost:5001/health
```

### 测试API接口

```bash
# 测试聊天接口
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，你是谁？"}'

# 测试RAG查询
curl -X POST http://localhost:5000/rag-query \
  -H "Content-Type: application/json" \
  -d '{"query": "你会做什么项目？", "target_persona": "李四"}'

# 测试Agent工具
curl -X POST http://localhost:5001/agent-chat \
  -H "Content-Type: application/json" \
  -d '{"message": "现在几点了？"}'
```

## 🎮 使用示例

### 基础聊天
```
用户: 你好，你是谁？
AI: 你好！我是李四，很高兴认识你！我平时喜欢做项目，对技术很感兴趣。

用户: 你会做什么项目？
AI: 说到项目，我最近在做一个小商城系统，用Vue和Spring Boot写的，还挺有意思的！
```

### 工具调用
```
用户: 现在几点了？
AI: 现在是：2024-01-15 14:30:25

用户: 帮我搜索Vue相关的项目
AI: 我为你找到了几个相关的项目：
1. vuejs/vue
   描述：The Progressive JavaScript Framework
   ⭐ 206k stars | 🔗 https://github.com/vuejs/vue

用户: 北京天气怎么样？
AI: 北京的天气情况：
🌡️ 温度：15°C
☁️ 天气：晴
💧 湿度：45%

用户: 计算2+3*4
AI: 计算结果：2+3*4 = 14
```

## ⚙️ 配置说明

### 快速配置

#### 修改大模型API

编辑 `digital-person-backend/src/main/resources/application.properties`：

```properties
# 替换为你的API密钥
llm.api.key=your_api_key_here
llm.api.url=https://api.deepseek.com/v1/chat/completions
```

#### 修改数据库配置

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/digital_person
spring.datasource.username=your_username
spring.datasource.password=your_password
```

#### 修改Redis配置

```properties
spring.redis.host=localhost
spring.redis.port=6379
```

### 环境变量配置

创建 `.env` 文件：

```bash
# 后端配置
SPRING_PROFILES_ACTIVE=dev
SPRING_DATASOURCE_URL=jdbc:mysql://localhost:3306/digital_person
SPRING_DATASOURCE_USERNAME=root
SPRING_DATASOURCE_PASSWORD=root
SPRING_REDIS_HOST=localhost

# AI配置
LLM_API_KEY=your_api_key
LLM_API_URL=https://api.deepseek.com/v1/chat/completions
```

## 🔧 常见问题

### 服务启动失败

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -ano | findstr :8080
   
   # 修改端口
   server.port=8081
   ```

2. **数据库连接失败**
   ```bash
   # 检查MySQL服务
   mysql -u root -p
   
   # 创建数据库
   CREATE DATABASE digital_person CHARACTER SET utf8mb4;
   ```

3. **Python依赖问题**
   ```bash
   # 使用虚拟环境
   python -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### 功能异常

1. **RAG检索无结果**
   - 检查数据文件是否存在：`data/cleaned_conversations.jsonl`
   - 重新生成示例数据：`python data-pipeline/sample_data_generator.py`

2. **工具调用失败**
   - 检查Agent服务是否正常运行
   - 查看详细日志：`docker-compose logs agent-tools`

3. **前端无法连接**
   - 检查CORS配置
   - 确认后端服务地址配置

## 📚 下一步学习

### 深入学习

1. **数据准备**
   - 学习如何清洗自己的微信聊天记录
   - 了解数据格式要求

2. **模型训练**
   - 了解如何微调模型
   - 学习向量数据库的使用

3. **工具开发**
   - 学习如何开发自定义工具
   - 了解工具调用机制

### 进阶配置

1. **生产部署**
   - 学习Docker生产部署
   - 了解性能优化策略

2. **安全配置**
   - 学习用户认证
   - 了解数据加密

3. **监控运维**
   - 学习系统监控
   - 了解日志分析

## 🎯 快速参考

### 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 清理数据
docker-compose down -v
```

### 文件结构

```
digital-person-chat/
├── digital-person-backend/     # Spring Boot后端
├── digital-person-frontend/    # Uni-app前端
├── data-pipeline/             # 数据清洗
├── rag-engine/               # RAG引擎
├── agent-tools/              # AI工具
├── data/                     # 数据文件
├── docs/                     # 文档
└── docker-compose.yml        # Docker编排
```

### 端口映射

- **8080**: 后端API服务
- **5000**: RAG引擎服务
- **5001**: Agent工具服务
- **3306**: MySQL数据库
- **6379**: Redis缓存
- **80/443**: Nginx前端服务

## 🚨 紧急处理

### 服务崩溃

1. **查看日志**
   ```bash
   docker-compose logs --tail=50 service_name
   ```

2. **重启服务**
   ```bash
   docker-compose restart service_name
   ```

3. **检查资源**
   ```bash
   docker stats
   ```

### 数据丢失

1. **恢复备份**
   ```bash
   # 恢复MySQL
   mysql -u root -p digital_person < backup.sql
   
   # 恢复Redis
   docker cp dump.rdb redis:/data/
   ```

2. **重新训练**
   ```bash
   python rag-engine/rag_engine.py
   ```

## 📞 获取帮助

### 在线资源

- **项目文档**: [README.md](README.md)
- **部署指南**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **路线图**: [ROADMAP.md](ROADMAP.md)
- **API文档**: 见项目文档

### 社区支持

- **GitHub Issues**: 报告问题
- **Discussions**: 功能讨论
- **Wiki**: 详细文档
- **Discord**: 实时交流


---

**恭喜！你已经成功启动了数字人聊天系统。现在可以开始体验AI对话的乐趣了！** 🎉

**遇到问题？查看常见问题或联系我们的支持团队。** 💪
