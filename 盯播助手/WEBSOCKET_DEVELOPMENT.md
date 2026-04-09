# WebSocket 真实数据接入开发文档

## 📋 项目概述

本文档详细描述了盯播助手项目中WebSocket真实数据接入的实现方案，重点实现了B站和斗鱼平台的弹幕数据抓取功能。

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   平台适配器    │    │   WebSocket服务 │    │   消息处理服务  │
│                 │◄──►│                 │◄──►│                 │
│  - B站适配器    │    │  - 连接管理    │    │  - 弹幕解析    │
│  - 斗鱼适配器  │    │  - 心跳维护    │    │  - 商品监控    │
│  - 虎牙适配器  │    │  - 重连机制    │    │  - AI分析      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        ▼                        │
         │             ┌─────────────────┐               │
         │             │   消息队列      │               │
         │             │   RabbitMQ      │◄──────────────┘
         │             └─────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│   直播平台      │    │   Java后端      │
│                 │    │                 │
│  - B站WebSocket │    │  - 任务管理    │
│  - 斗鱼STT协议 │    │  - 用户通知    │
└─────────────────┘    └─────────────────┘
```

## 🎯 核心功能实现

### 1. B站WebSocket连接实现

#### 协议分析
B站使用自定义的二进制协议，主要包含以下消息类型：
- **操作码 1**: 心跳回复
- **操作码 2**: 心跳请求
- **操作码 5**: 命令消息（弹幕、礼物等）
- **操作码 7**: 认证请求

#### 数据包格式
```
4字节长度 + 4字节长度重复 + 2字节协议版本 + 2字节操作码 + 4字节头部长度 + 数据
```

#### 核心实现代码

**连接建立**:
```python
async def connect_to_danmaku(self, room_id: str, message_handler) -> bool:
    # 获取房间真实ID
    # 获取弹幕服务器信息
    # 建立WebSocket连接
    # 发送认证包
    # 启动心跳和消息循环
```

**消息解析**:
```python
def _parse_packet(self, raw_data: bytes) -> List[Dict[str, Any]]:
    # 解析头部信息
    # 根据协议版本处理数据
    # 解压Gzip数据（如果需要）
    # 解析JSON消息
```

### 2. 斗鱼WebSocket连接实现

#### 协议分析
斗鱼使用STT（Simple Text Transfer）协议，基于自定义二进制格式：
- **消息类型**: loginreq, joingroup, chatmsg, dgb, uenter等
- **编码方式**: 键值对格式，使用`@=`分隔，`/`结束

#### 核心实现代码

**STT消息构建**:
```python
def _build_stt_message(self, data: Dict[str, Any]) -> bytes:
    # 构建键值对字符串
    # 添加协议头部
    # 返回二进制数据
```

**消息解析**:
```python
def _parse_stt_packet(self, raw_data: bytes) -> List[Dict[str, Any]]:
    # 解析二进制头部
    # 提取消息数据
    # 解析键值对
```

### 3. 心跳机制实现

#### 心跳策略
- **B站**: 30秒发送一次心跳包
- **斗鱼**: 45秒发送一次心跳包
- **通用**: Ping/Pong机制检测连接状态

#### 实现代码
```python
async def _heartbeat_loop(self):
    while self.connected and self.websocket:
        try:
            # 发送心跳包
            await self.websocket.ping()
            # 等待指定间隔
            await asyncio.sleep(heartbeat_interval)
        except websockets.ConnectionClosed:
            break
```

### 4. 断线重连机制

#### 指数退避算法
```python
delay = min(base_delay * (2 ** attempt), max_delay)
jitter = 0.1 * delay  # 添加随机抖动
actual_delay = delay + (jitter * (2 * random.random() - 1))
```

#### 重连策略
- 最大重连次数：5次
- 基础延迟：1秒
- 最大延迟：60秒
- 添加10%随机抖动避免同时重连

#### 实现代码
```python
async def _handle_connection_error(self):
    if self.reconnect_attempts < self.max_reconnect_attempts:
        delay = self.calculate_backoff_delay()
        await asyncio.sleep(delay)
        success = await self.connect_to_danmaku(self.room_id, None)
```

## 📁 文件结构

```
stream-spider-python/
├── services/
│   ├── bilibili_adapter.py      # B站平台适配器
│   ├── douyu_adapter.py         # 斗鱼平台适配器
│   ├── crawler_service.py       # 爬虫服务（集成适配器）
│   └── websocket_service.py     # WebSocket服务（增强重连）
├── test_adapters.py             # 适配器测试脚本
└── config/
    └── settings.py              # 配置文件
```

## 🔧 配置说明

### B站配置
```python
# B站API配置
BILIBILI_API_BASE = "https://api.live.bilibili.com"
BILIBILI_WS_BASE = "wss://broadcastlv.chat.bilibili.com/sub"

# 心跳间隔（秒）
BILIBILI_HEARTBEAT_INTERVAL = 30

# 重连配置
BILIBILI_MAX_RECONNECT_ATTEMPTS = 5
BILIBILI_BASE_RECONNECT_DELAY = 1
```

### 斗鱼配置
```python
# 斗鱼API配置
DOUYU_API_BASE = "https://www.douyu.com/lapi"
DOUYU_WS_BASE = "wss://danmuproxy.douyu.com:8520/"

# 心跳间隔（秒）
DOUYU_HEARTBEAT_INTERVAL = 45

# 重连配置
DOUYU_MAX_RECONNECT_ATTEMPTS = 5
DOUYU_BASE_RECONNECT_DELAY = 1
```

## 🚀 部署和运行

### 依赖安装
```bash
# 安装Python依赖
pip install -r requirements.txt

# B站API库
pip install bilibili-api-python

# WebSocket库
pip install websockets aiohttp

# 日志库
pip install loguru
```

### 启动服务
```bash
# 启动爬虫服务
python main.py

# 运行适配器测试
python test_adapters.py
```

### 环境要求
- Python 3.8+
- 网络连接正常
- 目标直播平台可访问

## 🧪 测试方案

### 单元测试

**API接口测试**:
```python
async def test_bilibili_api():
    adapter = BilibiliAdapter()
    room_info = await adapter.get_room_info('123456')
    assert room_info['platform'] == 'bilibili'
```

**消息解析测试**:
```python
def test_bilibili_message_parsing():
    adapter = BilibiliAdapter()
    test_message = {
        'cmd': 'DANMU_MSG',
        'info': [[], [], [12345, '用户名'], [], []]
    }
    barrages = adapter.parse_danmaku_message(test_message)
    assert len(barrages) == 1
    assert barrages[0]['type'] == 'danmu'
```

### 集成测试

**WebSocket连接测试**:
```python
async def test_websocket_connection():
    adapter = BilibiliAdapter()
    success = await adapter.connect_to_danmaku('123456', handler)
    assert success == True
    
    # 等待一段时间接收消息
    await asyncio.sleep(30)
    
    await adapter.disconnect()
```

### 性能测试

**连接稳定性测试**:
- 持续连接24小时
- 记录断开次数和重连成功率
- 监控内存使用情况

**消息处理能力测试**:
- 统计消息接收速率
- 测试高并发情况下的处理能力
- 验证消息丢失率

## 📊 监控指标

### 连接状态监控
```python
def get_connection_status(self) -> Dict[str, Any]:
    return {
        'is_connected': self.connected,
        'room_id': self.room_id,
        'reconnect_attempts': self.reconnect_attempts,
        'last_heartbeat': self.last_heartbeat,
        'message_count': self.message_count
    }
```

### 性能指标
- 连接建立时间
- 消息接收延迟
- 重连成功率
- CPU和内存使用率

## 🛡️ 错误处理

### 网络错误
- 连接超时
- 网络中断
- DNS解析失败

### 协议错误
- 数据格式错误
- 协议版本不匹配
- 认证失败

### 平台限制
- 频率限制
- IP封禁
- 验证码

## 🔄 扩展计划

### 待实现功能
1. **虎牙平台支持** - 实现虎牙WebSocket协议
2. **抖音平台支持** - 实现抖音直播协议
3. **协议自动识别** - 动态识别平台协议版本
4. **连接池管理** - 支持多个房间同时监控
5. **负载均衡** - 分布式部署支持

### 性能优化
1. **连接复用** - 减少重复连接开销
2. **消息压缩** - 减少网络传输量
3. **异步批处理** - 提高消息处理效率
4. **缓存机制** - 减少重复API调用

## 📝 开发规范

### 代码规范
- 遵循PEP 8规范
- 添加详细的文档字符串
- 使用类型注解
- 异常处理要具体

### 测试规范
- 单元测试覆盖率 > 80%
- 集成测试覆盖主要功能
- 性能测试定期执行

### 文档规范
- API文档完整
- 配置说明详细
- 部署文档清晰

## 🔗 参考资料

### B站相关
- [bilibili-api-python](https://github.com/Passkou/bilibili-api-python)
- [B站直播协议分析](https://github.com/lovelyyoshino/Bilibili-Live-API)

### 斗鱼相关
- [斗鱼协议分析](https://github.com/wbt5/real-url)
- [斗鱼STT协议](https://github.com/Baiyuetribe/bilibili_danmaku)

### WebSocket相关
- [websockets库文档](https://websockets.readthedocs.io/)
- [WebSocket协议RFC](https://tools.ietf.org/html/rfc6455)

## 📞 问题反馈

如遇问题，请提供以下信息：
1. 平台类型（B站/斗鱼）
2. 房间ID
3. 错误日志
4. 网络环境
5. Python版本

---

*文档版本: v1.0.0*
*最后更新: 2026/4/8*
*作者: exbox0403-cmd*