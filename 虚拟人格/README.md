# 数字人聊天系统

一个基于AI的数字人聊天系统，能够模拟特定人物的说话风格和记忆，支持工具调用和个性化对话。

## 🌟 项目特色

- **真正的AI Agent**：基于Function Calling的智能工具调用，告别规则匹配
- **流式交互体验**：类似ChatGPT的实时打字机效果，提供极致用户体验
- **个性化数字人**：基于真实聊天记录训练，模拟特定人物的说话风格
- **记忆增强**：使用RAG技术让AI能够"回忆"过去的对话内容
- **智能工具调用**：支持GitHub搜索、天气查询、时间获取等实用功能
- **富文本支持**：完整Markdown渲染，支持代码块、链接等格式
- **多端支持**：提供Web前端界面，支持移动端访问
- **工程化设计**：完整的前后端分离架构，支持扩展和部署

## 🏗️ 系统架构

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   前端界面      │    │    后端服务      │    │   Python引擎    │
│  (Uni-app/Vue)  │◄──►│ (Spring Boot)    │◄──►│  (RAG + Agent)  │
│  Markdown渲染   │    │  流式SSE输出     │    │Function Calling │
│  打字机效果     │    │  配置优化        │    │问题专用索引     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐    ┌─────────────────┐
         │              │   大模型API       │    │   向量数据库    │
         │              │ 流式支持          │    │ 问题专用        │
         │              │ (DeepSeek/Kimi)  │    │   (FAISS)       │
         │              └──────────────────┘    └─────────────────┘
         │
┌─────────────────┐
│     用户        │
└─────────────────┘
```

## 📦 技术栈

### 后端
- **Spring Boot 3.2.0** - 主框架
- **WebFlux** - 响应式编程
- **Java 17** - 编程语言

### 前端
- **Uni-app** - 跨平台框架
- **Vue 3** - 前端框架
- **uView** - UI组件库

### AI引擎
- **Python** - 数据处理和AI逻辑
- **Sentence Transformers** - 文本向量化
- **FAISS** - 向量数据库
- **Flask** - Python Web服务

### 工具和服务
- **Redis** - 缓存和会话管理
- **MySQL** - 用户数据持久化
- **Docker** - 容器化部署

## 🚀 快速开始

### 环境要求

- Java 17+
- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- Redis 6.0+

### 安装和运行

#### 1. 后端服务

```bash
# 进入后端目录
cd digital-person-backend

# 编译项目
mvn clean package

# 运行服务
java -jar target/digital-person-backend-1.0.0.jar
```

#### 2. Python RAG引擎

```bash
# 进入RAG引擎目录
cd rag-engine

# 安装依赖
pip install -r requirements.txt

# 启动RAG服务
python rag_server.py
```

#### 3. AI Agent工具服务

```bash
# 进入Agent工具目录
cd agent-tools

# 安装依赖
pip install -r requirements.txt

# 启动Agent服务
python agent_server.py
```

#### 4. 前端界面

```bash
# 进入前端目录
cd digital-person-frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev:%PLATFORM%
```

### 配置说明

#### 后端配置
编辑 `digital-person-backend/src/main/resources/application.properties`：

```properties
server.port=8080
spring.datasource.url=jdbc:mysql://localhost:3306/digital_person
spring.datasource.username=your_username
spring.datasource.password=your_password
spring.redis.host=localhost
spring.redis.port=6379

# 大模型API配置
llm.api.key=your_api_key
llm.api.url=https://api.deepseek.com/v1/chat/completions
```

#### Python服务配置
编辑环境变量或配置文件：

```bash
# RAG服务配置
export RAG_DATA_PATH=./data/cleaned_conversations.jsonl
export RAG_INDEX_PATH=./data/vector_index.faiss

# Agent服务配置
export AGENT_TOOLS_CONFIG=./config/tools.json
```

## 📊 API接口文档

### 后端API

#### 聊天接口
```
POST /api/chat
Content-Type: application/json

{
  "message": "你好，最近怎么样？"
}

Response:
{
  "response": "哈哈，还不错！最近在忙一个新项目...",
  "success": true
}
```

#### 用户认证
```
POST /api/auth/login
Content-Type: application/json

{
  "username": "user123",
  "password": "password"
}

Response:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "user123",
    "persona": "李四"
  },
  "success": true
}
```

### Python服务API

#### RAG查询
```
POST /rag-query
Content-Type: application/json

{
  "query": "你会做什么项目？",
  "target_persona": "李四"
}

Response:
{
  "query": "你会做什么项目？",
  "enhanced_prompt": "你现在是李四...根据你的记忆片段：[去年12月我做了一个模拟小米商城的全栈项目]...",
  "success": true
}
```

#### Agent工具调用
```
POST /agent-chat
Content-Type: application/json

{
  "message": "帮我搜索一下Vue相关的项目",
  "system_prompt": "你现在是李四，对前端技术很感兴趣"
}

Response:
{
  "response": "我为你找到了几个相关的项目：\n1. vuejs/vue\n   描述：The Progressive JavaScript Framework...",
  "tool_used": "search_github",
  "success": true
}
```

## 🔧 数据准备和训练

### 1. 数据清洗

```bash
# 准备原始微信聊天记录
data/raw_chat.txt

# 运行数据清洗脚本
python data-pipeline/data_cleaner.py

# 输出清洗后的数据
data/cleaned_conversations.jsonl
```

### 2. 构建向量数据库

```bash
# 使用RAG引擎构建向量索引
python rag-engine/rag_engine.py

# 生成的文件
data/vector_index.faiss
data/metadata.json
```

### 3. 数据格式说明

清洗后的对话数据格式（JSONL）：
```json
{"prompt": "今天中午吃什么？", "completion": "随便吧，我都行，点个外卖？"}
{"prompt": "昨天那个项目怎么样了？", "completion": "还行吧，就是有点累，加班到很晚"}
```

## 🛠️ 工具扩展

### 添加新工具

1. 在 `agent-tools/tools.py` 中注册新工具：

```python
def register_custom_tool(self):
    self.register_tool(
        name="my_tool",
        description="我的自定义工具",
        parameters={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"}
            },
            "required": ["param1"]
        },
        function=self._my_tool_function
    )
```

2. 实现工具函数：

```python
def _my_tool_function(self, param1: str) -> Dict:
    # 工具逻辑实现
    return {"success": True, "result": "工具执行结果"}
```

## 🚀 部署指南

### Docker部署

```bash
# 构建Docker镜像
docker build -t digital-person-backend ./digital-person-backend
docker build -t digital-person-rag ./rag-engine
docker build -t digital-person-agent ./agent-tools

# 运行服务
docker-compose up -d
```

### Docker Compose配置

```yaml
version: '3.8'
services:
  backend:
    image: digital-person-backend
    ports:
      - "8080:8080"
    depends_on:
      - mysql
      - redis

  rag-engine:
    image: digital-person-rag
    ports:
      - "5000:5000"

  agent-tools:
    image: digital-person-agent
    ports:
      - "5001:5001"

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: digital_person

  redis:
    image: redis:6.0
```

## 📈 性能优化建议

### 1. 缓存策略
- 使用Redis缓存常用对话和工具调用结果
- 实现对话历史的滑动窗口机制
- 缓存向量数据库查询结果

### 2. 数据库优化
- 为常用查询字段建立索引
- 定期清理过期的对话历史
- 使用数据库连接池

### 3. 前端优化
- 实现消息的虚拟滚动
- 使用Web Worker处理复杂计算
- 实现离线消息缓存

## 🔒 安全考虑

### 1. API安全
- 使用JWT进行用户认证
- 实现API限流和防刷机制
- 对敏感数据进行加密存储

### 2. 数据安全
- 用户数据隔离
- 聊天记录加密存储
- 定期数据备份

### 3. 工具安全
- 对工具调用进行权限控制
- 验证和清理用户输入
- 限制外部API调用频率

## 🤝 贡献指南

1. Fork项目到你的GitHub账户
2. 创建新的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交你的修改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情



## 🙏 致谢

感谢以下开源项目和技术社区：

- [Spring Boot](https://spring.io/projects/spring-boot)
- [Vue.js](https://vuejs.org/)
- [Sentence Transformers](https://www.sbert.net/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Flask](https://flask.palletsprojects.com/)

---

**Made with ❤️ by the Digital Person Team**
