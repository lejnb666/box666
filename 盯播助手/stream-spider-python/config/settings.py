# -*- coding: utf-8 -*-

"""
配置文件

@author: exbox0403-cmd
@since: 2026/4/8
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class DatabaseSettings:
    """数据库配置"""
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', 3306))
    database: str = os.getenv('DB_NAME', 'stream_monitor')
    username: str = os.getenv('DB_USERNAME', 'root')
    password: str = os.getenv('DB_PASSWORD', 'root123')
    pool_size: int = int(os.getenv('DB_POOL_SIZE', 10))
    pool_recycle: int = int(os.getenv('DB_POOL_RECYCLE', 3600))
    echo: bool = os.getenv('DB_ECHO', 'False').lower() == 'true'

    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisSettings:
    """Redis配置"""
    host: str = os.getenv('REDIS_HOST', 'localhost')
    port: int = int(os.getenv('REDIS_PORT', 6379))
    password: str = os.getenv('REDIS_PASSWORD', '')
    db: int = int(os.getenv('REDIS_DB', 0))
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


@dataclass
class RabbitMQSettings:
    """RabbitMQ配置"""
    host: str = os.getenv('RABBITMQ_HOST', 'localhost')
    port: int = int(os.getenv('RABBITMQ_PORT', 5672))
    username: str = os.getenv('RABBITMQ_USERNAME', 'guest')
    password: str = os.getenv('RABBITMQ_PASSWORD', 'guest')
    virtual_host: str = os.getenv('RABBITMQ_VHOST', '/')
    heartbeat: int = 60
    blocked_connection_timeout: int = 300

    @property
    def url(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.virtual_host}"


@dataclass
class AISettings:
    """AI服务配置"""
    api_base_url: str = os.getenv('AI_API_BASE_URL', 'https://api.deepseek.com')
    api_key: str = os.getenv('AI_API_KEY', '')
    model_name: str = os.getenv('AI_MODEL_NAME', 'deepseek-chat')
    timeout: int = int(os.getenv('AI_TIMEOUT', 30))
    max_tokens: int = int(os.getenv('AI_MAX_TOKENS', 1000))
    temperature: float = float(os.getenv('AI_TEMPERATURE', 0.7))
    retry_count: int = int(os.getenv('AI_RETRY_COUNT', 3))
    retry_delay: int = int(os.getenv('AI_RETRY_DELAY', 1))


@dataclass
class CrawlerSettings:
    """爬虫配置"""
    interval: int = int(os.getenv('CRAWLER_INTERVAL', 30))  # 秒
    max_concurrent_tasks: int = int(os.getenv('MAX_CONCURRENT_TASKS', 1000))
    barrage_buffer_size: int = int(os.getenv('BARRAGE_BUFFER_SIZE', 50))
    request_timeout: int = int(os.getenv('CRAWLER_REQUEST_TIMEOUT', 10))
    retry_count: int = int(os.getenv('CRAWLER_RETRY_COUNT', 3))
    retry_delay: int = int(os.getenv('CRAWLER_RETRY_DELAY', 1))

    # 平台特定配置
    platforms: Dict[str, Dict] = field(default_factory=lambda: {
        'bilibili': {
            'base_url': 'https://api.live.bilibili.com',
            'websocket_url': 'wss://broadcastlv.chat.bilibili.com/sub',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        },
        'douyu': {
            'base_url': 'https://www.douyu.com',
            'websocket_url': 'wss://danmuproxy.douyu.com:8504',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        },
        'huya': {
            'base_url': 'https://www.huya.com',
            'websocket_url': 'wss://cdnws.api.huya.com',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
    })


@dataclass
class WebSocketSettings:
    """WebSocket配置"""
    ping_interval: int = int(os.getenv('WS_PING_INTERVAL', 30))
    ping_timeout: int = int(os.getenv('WS_PING_TIMEOUT', 10))
    max_reconnect_attempts: int = int(os.getenv('WS_MAX_RECONNECT', 5))
    reconnect_delay: int = int(os.getenv('WS_RECONNECT_DELAY', 5))


@dataclass
class NotificationSettings:
    """通知配置"""
    rate_limit: int = int(os.getenv('NOTIFICATION_RATE_LIMIT', 10))  # 每分钟
    retry_count: int = int(os.getenv('NOTIFICATION_RETRY_COUNT', 3))
    retry_interval: int = int(os.getenv('NOTIFICATION_RETRY_INTERVAL', 5000))  # 毫秒

    # 微信配置
    wechat_app_id: str = os.getenv('WECHAT_APP_ID', '')
    wechat_app_secret: str = os.getenv('WECHAT_APP_SECRET', '')
    wechat_template_ids: Dict[str, str] = field(default_factory=lambda: {
        'live_start': os.getenv('WECHAT_TEMPLATE_ID_LIVE_START', ''),
        'product_launch': os.getenv('WECHAT_TEMPLATE_ID_PRODUCT_LAUNCH', ''),
        'keyword_match': os.getenv('WECHAT_TEMPLATE_ID_KEYWORD_MATCH', '')
    })


@dataclass
class LoggingSettings:
    """日志配置"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: str = os.getenv('LOG_FILE_PATH', 'logs/stream-monitor.log')
    max_file_size: int = int(os.getenv('LOG_MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
    backup_count: int = int(os.getenv('LOG_BACKUP_COUNT', 5))


@dataclass
class Settings:
    """全局配置"""
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    environment: str = os.getenv('ENVIRONMENT', 'development')
    version: str = '1.0.0'

    # 服务配置
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    rabbitmq: RabbitMQSettings = field(default_factory=RabbitMQSettings)
    ai: AISettings = field(default_factory=AISettings)
    crawler: CrawlerSettings = field(default_factory=CrawlerSettings)
    websocket: WebSocketSettings = field(default_factory=WebSocketSettings)
    notification: NotificationSettings = field(default_factory=NotificationSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    # 队列名称
    queue_names: Dict[str, str] = field(default_factory=lambda: {
        'live_events': 'live_events_queue',
        'barrage_events': 'barrage_events_queue',
        'notification_events': 'notification_events_queue',
        'ai_analysis': 'ai_analysis_queue'
    })

    # 缓存键前缀
    cache_keys: Dict[str, str] = field(default_factory=lambda: {
        'live_status': 'live_status:',
        'user_subscriptions': 'user_subscriptions:',
        'streamer_info': 'streamer_info:',
        'ai_cache': 'ai_cache:'
    })

    def __post_init__(self):
        """初始化后处理"""
        # 确保日志目录存在
        log_dir = os.path.dirname(self.logging.file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)


# 全局配置实例
settings = Settings()


if __name__ == '__main__':
    # 测试配置加载
    print("配置加载测试:")
    print(f"数据库: {settings.database.url}")
    print(f"Redis: {settings.redis.host}:{settings.redis.port}")
    print(f"RabbitMQ: {settings.rabbitmq.url}")
    print(f"AI服务: {settings.ai.api_base_url}")
    print(f"爬虫间隔: {settings.crawler.interval}秒")