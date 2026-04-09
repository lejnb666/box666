# -*- coding: utf-8 -*-

"""
WebSocket服务 - 负责实时数据流处理和商品监控

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import random
import re
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

import websockets
from loguru import logger

from config.settings import settings
from services.ai_service import AIService
from services.rabbitmq_service import RabbitMQService
from utils.logger import LoggerMixin


class WebSocketService(LoggerMixin):
    """
    WebSocket服务类，负责实时数据流处理和商品监控
    """

    def __init__(self, app_settings, ai_service: AIService, rabbitmq_service: RabbitMQService):
        self.settings = app_settings
        self.ai_service = ai_service
        self.rabbitmq_service = rabbitmq_service

        # WebSocket连接管理
        self.websocket_connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.connected_rooms: Set[str] = set()

        # 商品监控相关
        self.product_keywords = [
            '上车', '链接', '购买', '下单', '现货', '发货', '包邮', '售后',
            '价格', '优惠', '折扣', '特价', '秒杀', '降价', '促销',
            '库存', '限量', '抢购', '团购', '拼团'
        ]

        self.price_patterns = [
            r'(\d+(?:\.\d{1,2})?)元',
            r'(\d+(?:\.\d{1,2})?)块',
            r'原价(\d+(?:\.\d{1,2})?)',
            r'现价(\d+(?:\.\d{1,2})?)',
            r'￥(\d+(?:\.\d{1,2})?)'
        ]

        # 任务管理
        self.is_connected_flag = False
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

        # 事件循环（用于独立线程）
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def initialize(self):
        """初始化WebSocket服务"""
        try:
            self.logger.info("WebSocket服务初始化完成")
        except Exception as e:
            self.logger.error(f"WebSocket服务初始化失败: {e}")
            raise

    async def close(self):
        """关闭WebSocket服务"""
        try:
            # 关闭所有WebSocket连接
            for room_key, websocket in self.websocket_connections.items():
                try:
                    await websocket.close()
                except Exception as e:
                    self.logger.error(f"关闭WebSocket连接失败 {room_key}: {e}")

            self.websocket_connections.clear()
            self.connected_rooms.clear()

            # 取消所有监控任务
            for task_id, task in self.monitoring_tasks.items():
                if not task.done():
                    task.cancel()

            self.monitoring_tasks.clear()
            self.is_connected_flag = False

            self.logger.info("WebSocket服务已关闭")

        except Exception as e:
            self.logger.error(f"WebSocket服务关闭失败: {e}")

    def is_connected(self) -> bool:
        """检查WebSocket服务是否连接"""
        return self.is_connected_flag

    async def connect_to_room(self, platform: str, room_id: str) -> bool:
        """连接到指定房间"""
        try:
            room_key = f"{platform}:{room_id}"

            if room_key in self.connected_rooms:
                self.logger.warning(f"已连接到房间: {room_key}")
                return True

            # 获取平台对应的WebSocket URL
            websocket_url = await self._get_websocket_url(platform, room_id)
            if not websocket_url:
                self.logger.error(f"无法获取WebSocket URL: {room_key}")
                return False

            # 建立WebSocket连接
            websocket = await websockets.connect(websocket_url)
            self.websocket_connections[room_key] = websocket
            self.connected_rooms.add(room_key)

            # 启动消息监听任务
            task = asyncio.create_task(
                self._listen_messages(platform, room_id, websocket)
            )
            self.monitoring_tasks[room_key] = task

            self.is_connected_flag = True
            self.logger.info(f"成功连接到 {platform} 房间 {room_id}")
            return True

        except Exception as e:
            self.logger.error(f"连接房间失败 {platform}:{room_id}: {e}")
            return False

    async def disconnect_from_room(self, platform: str, room_id: str) -> bool:
        """断开指定房间的连接"""
        try:
            room_key = f"{platform}:{room_id}"

            if room_key in self.websocket_connections:
                websocket = self.websocket_connections[room_key]
                await websocket.close()
                del self.websocket_connections[room_key]

            if room_key in self.connected_rooms:
                self.connected_rooms.remove(room_key)

            if room_key in self.monitoring_tasks:
                task = self.monitoring_tasks[room_key]
                if not task.done():
                    task.cancel()
                del self.monitoring_tasks[room_key]

            self.logger.info(f"已断开与 {platform} 房间 {room_id} 的连接")
            return True

        except Exception as e:
            self.logger.error(f"断开房间连接失败 {platform}:{room_id}: {e}")
            return False

    async def _get_websocket_url(self, platform: str, room_id: str) -> str:
        """获取平台WebSocket URL"""
        # 这里应该根据不同平台获取对应的WebSocket URL
        # 暂时使用模拟URL
        platform_urls = {
            'bilibili': f"wss://broadcastlv.chat.bilibili.com/sub",
            'douyu': f"wss://danmuproxy.douyu.com:8520/",
            'huya': f"wss://cdnws.api.huya.com/",
            'douyin': f"wss://webcast5-ws-web-lq.douyin.com/webcast/im/push/pull/"
        }

        return platform_urls.get(platform, "")

    async def _listen_messages(self, platform: str, room_id: str, websocket: websockets.WebSocketClientProtocol):
        """监听WebSocket消息（带心跳检测）"""
        try:
            room_key = f"{platform}:{room_id}"
            last_heartbeat = time.time()
            heartbeat_timeout = 60  # 60秒无消息判定为超时

            # 启动心跳检测任务
            heartbeat_task = asyncio.create_task(
                self._heartbeat_check(platform, room_id, websocket, last_heartbeat)
            )

            while True:
                try:
                    # 使用带超时的接收
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=heartbeat_timeout
                    )

                    # 更新最后接收时间
                    last_heartbeat = time.time()

                    # 解析消息
                    barrage_data = await self._parse_platform_message(platform, message)

                    if barrage_data:
                        # 处理弹幕数据
                        await self._process_barrage_data(platform, room_id, barrage_data)

                        # 商品监控分析
                        await self._analyze_product_launch(platform, room_id, barrage_data)

                        # 发送到消息队列
                        await self.rabbitmq_service.publish(
                            'websocket_barrage',
                            {
                                'type': 'barrage',
                                'platform': platform,
                                'room_id': room_id,
                                'data': barrage_data,
                                'timestamp': datetime.now().isoformat()
                            }
                        )

                except asyncio.TimeoutError:
                    # 心跳超时
                    self.logger.warning(f"WebSocket心跳超时: {room_key}")
                    await self._reconnect(platform, room_id)
                    break
                except websockets.ConnectionClosed:
                    self.logger.warning(f"WebSocket连接断开: {room_key}")
                    # 尝试重连
                    await self._reconnect(platform, room_id)
                    break
                except Exception as e:
                    self.logger.error(f"消息处理错误 {room_key}: {e}")
                    await asyncio.sleep(1)

            # 取消心跳检测任务
            heartbeat_task.cancel()

        except asyncio.CancelledError:
            self.logger.info(f"消息监听任务被取消: {platform}:{room_id}")
        except Exception as e:
            self.logger.error(f"消息监听异常: {e}")

    async def _parse_platform_message(self, platform: str, raw_message: str) -> Optional[Dict[str, Any]]:
        """解析平台消息"""
        try:
            if platform == 'bilibili':
                return self._parse_bilibili_message(raw_message)
            elif platform == 'douyu':
                return self._parse_douyu_message(raw_message)
            elif platform == 'huya':
                return self._parse_huya_message(raw_message)
            elif platform == 'douyin':
                return self._parse_douyin_message(raw_message)
            else:
                # 通用JSON解析
                try:
                    return json.loads(raw_message)
                except:
                    return {'content': raw_message, 'type': 'unknown'}

        except Exception as e:
            self.logger.error(f"消息解析失败: {e}")
            return None

    def _parse_bilibili_message(self, raw_message: str) -> Dict[str, Any]:
        """解析B站消息"""
        try:
            # B站消息格式较复杂，这里简化处理
            message_data = json.loads(raw_message)

            if message_data.get('cmd') == 'DANMU_MSG':
                return {
                    'type': 'danmu',
                    'content': message_data['info'][1],
                    'user_id': str(message_data['info'][2][0]),
                    'username': message_data['info'][2][1],
                    'timestamp': datetime.now().isoformat()
                }
            elif message_data.get('cmd') == 'SEND_GIFT':
                return {
                    'type': 'gift',
                    'content': f"{message_data['data']['uname']} 赠送了 {message_data['data']['giftName']}",
                    'user_id': str(message_data['data']['uid']),
                    'username': message_data['data']['uname'],
                    'gift_name': message_data['data']['giftName'],
                    'gift_count': message_data['data']['num'],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return message_data

        except Exception as e:
            self.logger.error(f"B站消息解析失败: {e}")
            return {'content': raw_message, 'type': 'unknown'}

    def _parse_douyu_message(self, raw_message: str) -> Dict[str, Any]:
        """解析斗鱼消息"""
        try:
            # 斗鱼使用自定义协议，这里简化处理
            if 'type@=chatmsg' in raw_message:
                # 提取弹幕内容
                content_match = re.search(r'content@=([^&|]+)', raw_message)
                user_match = re.search(r'nn@=([^&|]+)', raw_message)
                uid_match = re.search(r'uid@=([^&|]+)', raw_message)

                content = content_match.group(1) if content_match else ''
                username = user_match.group(1) if user_match else '未知用户'
                user_id = uid_match.group(1) if uid_match else '0'

                return {
                    'type': 'danmu',
                    'content': content.replace('\\/', '/'),
                    'user_id': user_id,
                    'username': username,
                    'timestamp': datetime.now().isoformat()
                }

            return {'content': raw_message, 'type': 'unknown'}

        except Exception as e:
            self.logger.error(f"斗鱼消息解析失败: {e}")
            return {'content': raw_message, 'type': 'unknown'}

    def _parse_huya_message(self, raw_message: str) -> Dict[str, Any]:
        """解析虎牙消息"""
        try:
            # 虎牙消息格式，这里简化处理
            if 'chatMsg' in raw_message:
                try:
                    message_data = json.loads(raw_message)
                    return {
                        'type': 'danmu',
                        'content': message_data.get('content', ''),
                        'user_id': str(message_data.get('uid', '0')),
                        'username': message_data.get('uname', '未知用户'),
                        'timestamp': datetime.now().isoformat()
                    }
                except:
                    pass

            return {'content': raw_message, 'type': 'unknown'}

        except Exception as e:
            self.logger.error(f"虎牙消息解析失败: {e}")
            return {'content': raw_message, 'type': 'unknown'}

    def _parse_douyin_message(self, raw_message: str) -> Dict[str, Any]:
        """解析抖音消息"""
        try:
            message_data = json.loads(raw_message)

            # 抖音消息结构较复杂，提取关键信息
            if 'messages' in message_data:
                for msg in message_data['messages']:
                    if msg.get('type') == 'chat':
                        return {
                            'type': 'danmu',
                            'content': msg.get('content', ''),
                            'user_id': str(msg.get('user_id', '0')),
                            'username': msg.get('user_name', '未知用户'),
                            'timestamp': datetime.now().isoformat()
                        }

            return message_data

        except Exception as e:
            self.logger.error(f"抖音消息解析失败: {e}")
            return {'content': raw_message, 'type': 'unknown'}

    async def _process_barrage_data(self, platform: str, room_id: str, barrage_data: Dict[str, Any]):
        """处理弹幕数据"""
        try:
            # 基础数据验证
            if not barrage_data.get('content'):
                return

            # 数据清洗和标准化
            cleaned_data = {
                'platform': platform,
                'room_id': room_id,
                'content': barrage_data['content'].strip(),
                'user_id': barrage_data.get('user_id', ''),
                'username': barrage_data.get('username', ''),
                'type': barrage_data.get('type', 'danmu'),
                'timestamp': barrage_data.get('timestamp', datetime.now().isoformat()),
                'raw_data': barrage_data
            }

            # 调用AI服务进行分析
            if self.ai_service and cleaned_data['type'] == 'danmu':
                try:
                    ai_result = await self.ai_service.analyze_barrages(
                        [cleaned_data],
                        'general'
                    )

                    if ai_result.get('is_triggered'):
                        # 发送AI分析结果
                        await self.rabbitmq_service.publish(
                            'ai_analysis_result',
                            {
                                'type': 'ai_trigger',
                                'platform': platform,
                                'room_id': room_id,
                                'barrage_data': cleaned_data,
                                'ai_result': ai_result,
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                except Exception as e:
                    self.logger.error(f"AI分析失败: {e}")

            return cleaned_data

        except Exception as e:
            self.logger.error(f"弹幕数据处理失败: {e}")

    async def _analyze_product_launch(self, platform: str, room_id: str, barrage_data: Dict[str, Any]):
        """分析商品上架信息"""
        try:
            content = barrage_data.get('content', '').lower()

            # 关键词匹配
            product_indicators = []
            for keyword in self.product_keywords:
                if keyword in content:
                    product_indicators.append(keyword)

            if not product_indicators:
                return

            # 价格提取
            prices = []
            for pattern in self.price_patterns:
                matches = re.findall(pattern, content)
                prices.extend(matches)

            # 构建商品信息
            product_info = {
                'platform': platform,
                'room_id': room_id,
                'trigger_content': content,
                'trigger_keywords': product_indicators,
                'detected_prices': prices,
                'user_id': barrage_data.get('user_id', ''),
                'username': barrage_data.get('username', ''),
                'confidence': min(0.9, 0.3 + len(product_indicators) * 0.2),
                'timestamp': datetime.now().isoformat()
            }

            # 发送商品监控结果
            await self.rabbitmq_service.publish(
                'product_monitor',
                {
                    'type': 'product_detected',
                    'platform': platform,
                    'room_id': room_id,
                    'product_info': product_info,
                    'timestamp': datetime.now().isoformat()
                }
            )

            self.logger.info(f"检测到商品上架: {platform}:{room_id} - {content}")

        except Exception as e:
            self.logger.error(f"商品分析失败: {e}")

    async def _reconnect(self, platform: str, room_id: str):
        """重新连接WebSocket（带指数退避）"""
        try:
            room_key = f"{platform}:{room_id}"
            self.logger.info(f"尝试重新连接: {room_key}")

            # 指数退避重连机制
            max_attempts = 5
            base_delay = 1
            max_delay = 60

            for attempt in range(max_attempts):
                try:
                    # 计算延迟时间（指数退避）
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = 0.1 * delay  # 添加10%的随机抖动
                    actual_delay = delay + (jitter * (2 * random.random() - 1))

                    self.logger.info(f"重连尝试 {attempt + 1}/{max_attempts}, {actual_delay:.1f}秒后重试")
                    await asyncio.sleep(actual_delay)

                    # 重新连接
                    success = await self.connect_to_room(platform, room_id)

                    if success:
                        self.logger.info(f"重新连接成功: {room_key}")
                        return True
                    else:
                        self.logger.warning(f"重连尝试 {attempt + 1} 失败")

                except Exception as e:
                    self.logger.error(f"重连尝试 {attempt + 1} 异常: {e}")

            # 所有重连尝试都失败
            self.logger.error(f"重连失败，已达到最大重连次数: {room_key}")
            return False

        except Exception as e:
            self.logger.error(f"重连失败 {platform}:{room_id}: {e}")
            return False

    def start_listening(self):
        """启动WebSocket监听（在新线程中运行）"""
        try:
            # 创建新的事件循环并设置为当前线程的事件循环
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            self.logger.info("启动WebSocket监听服务")

            # 运行事件循环
            try:
                self.loop.run_forever()
            except KeyboardInterrupt:
                self.logger.info("WebSocket监听服务被中断")
            finally:
                self.loop.close()

        except Exception as e:
            self.logger.error(f"WebSocket监听启动失败: {e}")

    async def _heartbeat_check(self, platform: str, room_id: str, websocket: websockets.WebSocketClientProtocol, last_heartbeat_ref):
        """心跳检测任务"""
        try:
            room_key = f"{platform}:{room_id}"
            heartbeat_interval = 30  # 30秒发送一次心跳

            while True:
                await asyncio.sleep(heartbeat_interval)

                try:
                    # 发送Ping
                    await websocket.ping()
                    self.logger.debug(f"发送心跳Ping: {room_key}")

                    # 检查最后接收时间（这里需要修改last_heartbeat_ref为可变对象）
                    # 由于Python的限制，这里简化处理

                except websockets.ConnectionClosed:
                    self.logger.warning(f"心跳检测发现连接关闭: {room_key}")
                    break
                except Exception as e:
                    self.logger.error(f"心跳检测失败 {room_key}: {e}")
                    break

        except asyncio.CancelledError:
            self.logger.info(f"心跳检测任务被取消: {platform}:{room_id}")
        except Exception as e:
            self.logger.error(f"心跳检测异常: {e}")

    async def send_message(self, platform: str, room_id: str, message: str) -> bool:
        """发送消息到指定房间"""
        try:
            room_key = f"{platform}:{room_id}"

            if room_key not in self.websocket_connections:
                self.logger.error(f"未连接到房间: {room_key}")
                return False

            websocket = self.websocket_connections[room_key]
            await websocket.send(message)

            self.logger.info(f"消息发送成功: {room_key}")
            return True

        except Exception as e:
            self.logger.error(f"消息发送失败 {platform}:{room_id}: {e}")
            return False

    def reconnect(self):
        """重新连接所有WebSocket"""
        try:
            self.logger.info("重新连接所有WebSocket")

            # 保存当前连接的房间
            current_rooms = list(self.connected_rooms)

            # 关闭所有连接
            asyncio.create_task(self.close())

            # 等待关闭完成
            time.sleep(2)

            # 重新连接
            for room_key in current_rooms:
                platform, room_id = room_key.split(':', 1)
                asyncio.create_task(self.connect_to_room(platform, room_id))

        except Exception as e:
            self.logger.error(f"重新连接失败: {e}")

    def get_connection_status(self) -> Dict[str, Any]:
        """获取连接状态"""
        return {
            'is_connected': self.is_connected_flag,
            'connected_rooms': list(self.connected_rooms),
            'active_connections': len(self.websocket_connections),
            'monitoring_tasks': len(self.monitoring_tasks)
        }