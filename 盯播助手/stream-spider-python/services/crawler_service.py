# -*- coding: utf-8 -*-

"""
爬虫服务 - 负责多平台直播数据抓取

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import logging
import re
import time
import urllib.parse
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import aiohttp
import requests
from loguru import logger

# B站API相关导入
from bilibili_api import live, sync, exceptions
from bilibili_api.live import LiveDanmaku
from bilibili_api.utils.network_helpers import get_session

# 自定义适配器导入
from services.bilibili_adapter import BilibiliAdapter
from services.douyu_adapter import DouyuAdapter

# AI相关导入
from services.local_filter import LocalFilterService
from services.ai_orchestrator import AIOrchestrator, EventType

from config.settings import settings
from utils.logger import LoggerMixin


class PlatformAdapter(ABC):
    """平台适配器基类"""

    def __init__(self, platform: str):
        self.platform = platform
        self.session = None

    @abstractmethod
    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取房间信息"""
        pass

    @abstractmethod
    async def get_live_status(self, room_id: str) -> bool:
        """获取直播状态"""
        pass

    @abstractmethod
    async def get_barrage_url(self, room_id: str) -> str:
        """获取弹幕服务器地址"""
        pass

    @abstractmethod
    async def parse_barrage_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析弹幕数据"""
        pass


class BilibiliAdapter(PlatformAdapter):
    """B站平台适配器"""

    def __init__(self):
        super().__init__('bilibili')
        self.base_url = 'https://api.live.bilibili.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.live_room = None
        self.danmaku_client = None

    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取B站房间信息 - 使用bilibili-api-python库"""
        try:
            # 使用sync包装器将同步调用转换为异步
            def fetch_room_info():
                room = live.LiveRoom(room_id=int(room_id))
                return room.get_room_info()

            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            room_info = await loop.run_in_executor(None, fetch_room_info)

            if room_info:
                info = room_info['room_info']
                return {
                    'platform': self.platform,
                    'room_id': room_id,
                    'streamer_name': info.get('uname', ''),
                    'title': info.get('title', ''),
                    'category': info.get('area_name', ''),
                    'is_live': info.get('live_status') == 1,
                    'viewer_count': info.get('online', 0),
                    'start_time': info.get('live_time', ''),
                    'avatar_url': info.get('face', ''),
                    'room_area': info.get('area_name', ''),
                    'parent_area': info.get('parent_area_name', ''),
                    'keyframe': info.get('keyframe', ''),
                    'tags': info.get('tags', [])
                }
            return {}
        except exceptions.ResponseCodeException as e:
            logger.error(f'B站API响应错误: {e}')
            return {}
        except Exception as e:
            logger.error(f'B站房间信息获取失败: {e}')
            return {}

    async def get_live_status(self, room_id: str) -> bool:
        """获取B站直播状态 - 使用bilibili-api-python库"""
        try:
            def fetch_live_status():
                room = live.LiveRoom(room_id=int(room_id))
                return room.get_room_info()

            loop = asyncio.get_event_loop()
            status_info = await loop.run_in_executor(None, fetch_live_status)

            if status_info:
                return status_info['room_info'].get('live_status') == 1
            return False
        except Exception as e:
            logger.error(f'B站直播状态获取失败: {e}')
            return False

    async def get_barrage_url(self, room_id: str) -> str:
        """获取B站弹幕服务器地址 - 使用bilibili-api-python库"""
        try:
            def fetch_danmaku_info():
                room = live.LiveRoom(room_id=int(room_id))
                return room.get_danmu_info()

            loop = asyncio.get_event_loop()
            danmaku_info = await loop.run_in_executor(None, fetch_danmaku_info)

            if danmaku_info and danmaku_info.get('host_list'):
                # 返回第一个支持WSS的服务器地址
                for host in danmaku_info['host_list']:
                    if 'wss' in host.get('host', '') or host.get('wss_port'):
                        return f"wss://{host['host']}:{host.get('wss_port', 443)}/sub"
            return ''
        except Exception as e:
            logger.error(f'B站弹幕服务器获取失败: {e}')
            return ''

    async def parse_barrage_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析B站弹幕数据 - 使用bilibili-api-python库进行协议解析"""
        barrages = []

        try:
            # 使用bilibili-api-python的协议解析
            from bilibili_api.live import parse_websocket_message

            # 解析WebSocket消息
            messages = parse_websocket_message(raw_data)

            for message in messages:
                try:
                    if isinstance(message, dict) and 'cmd' in message:
                        if message['cmd'] == 'DANMU_MSG':
                            # 解析弹幕消息
                            # info[1] = 弹幕内容, info[2][0] = 用户ID, info[2][1] = 用户名
                            if len(message['info']) >= 3:
                                barrage = {
                                    'platform': self.platform,
                                    'content': message['info'][1],
                                    'user_id': str(message['info'][2][0]) if message['info'][2] else 'unknown',
                                    'username': message['info'][2][1] if message['info'][2] else 'unknown',
                                    'timestamp': datetime.now().isoformat(),
                                    'type': 'danmu',
                                    'medal_level': message['info'][3][0] if len(message['info']) > 3 and message['info'][3] else None,
                                    'medal_name': message['info'][3][1] if len(message['info']) > 3 and message['info'][3] else None,
                                    'medal_room': message['info'][3][3] if len(message['info']) > 3 and message['info'][3] else None,
                                    'user_level': message['info'][4][0] if len(message['info']) > 4 and message['info'][4] else None,
                                    'is_admin': message['info'][2][2] if message['info'][2] else 0,
                                    'is_vip': message['info'][2][3] if len(message['info'][2]) > 3 else 0
                                }
                                barrages.append(barrage)

                        elif message['cmd'] == 'SEND_GIFT':
                            # 解析礼物消息
                            gift_data = message.get('data', {})
                            barrage = {
                                'platform': self.platform,
                                'content': f"{gift_data.get('uname', 'unknown')} 赠送了 {gift_data.get('giftName', 'unknown')}",
                                'user_id': str(gift_data.get('uid', 'unknown')),
                                'username': gift_data.get('uname', 'unknown'),
                                'timestamp': datetime.now().isoformat(),
                                'type': 'gift',
                                'gift_name': gift_data.get('giftName'),
                                'gift_count': gift_data.get('num'),
                                'gift_price': gift_data.get('price'),
                                'total_coin': gift_data.get('total_coin')
                            }
                            barrages.append(barrage)

                        elif message['cmd'] == 'WELCOME':
                            # 解析欢迎消息
                            welcome_data = message.get('data', {})
                            barrage = {
                                'platform': self.platform,
                                'content': f"欢迎 {welcome_data.get('uname', 'unknown')} 进入直播间",
                                'user_id': str(welcome_data.get('uid', 'unknown')),
                                'username': welcome_data.get('uname', 'unknown'),
                                'timestamp': datetime.now().isoformat(),
                                'type': 'welcome',
                                'is_admin': welcome_data.get('is_admin', False),
                                'is_vip': welcome_data.get('is_vip', False)
                            }
                            barrages.append(barrage)

                        elif message['cmd'] == 'LIVE':
                            # 直播开始
                            barrage = {
                                'platform': self.platform,
                                'content': '直播已开始',
                                'user_id': 'system',
                                'username': 'system',
                                'timestamp': datetime.now().isoformat(),
                                'type': 'live_start'
                            }
                            barrages.append(barrage)

                        elif message['cmd'] == 'PREPARING':
                            # 直播准备中
                            barrage = {
                                'platform': self.platform,
                                'content': '直播准备中',
                                'user_id': 'system',
                                'username': 'system',
                                'timestamp': datetime.now().isoformat(),
                                'type': 'live_end'
                            }
                            barrages.append(barrage)

                except Exception as e:
                    logger.error(f'B站弹幕消息解析错误: {e}')
                    continue

        except Exception as e:
            logger.error(f'B站弹幕数据解析失败: {e}')
            return []

        return barrages


class DouyuAdapter(PlatformAdapter):
    """斗鱼平台适配器"""

    def __init__(self):
        super().__init__('douyu')
        self.base_url = 'https://www.douyu.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取斗鱼房间信息"""
        try:
            url = f'{self.base_url}/swf_api/homeH5Enc'
            params = {'rids': room_id}

            async with self.session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['error'] == 0 and room_id in data['data']['room']:
                        room_data = data['data']['room'][room_id]
                        return {
                            'platform': self.platform,
                            'room_id': room_id,
                            'streamer_name': room_data.get('nickname', ''),
                            'title': room_data.get('room_name', ''),
                            'category': room_data.get('cate_name', ''),
                            'is_live': room_data.get('show_status') == 1,
                            'viewer_count': room_data.get('online', 0),
                            'start_time': room_data.get('start_time', ''),
                            'avatar_url': room_data.get('avatar', '')
                        }
            return {}
        except Exception as e:
            logger.error(f'斗鱼房间信息获取失败: {e}')
            return {}

    async def get_live_status(self, room_id: str) -> bool:
        """获取斗鱼直播状态"""
        room_info = await self.get_room_info(room_id)
        return room_info.get('is_live', False)

    async def get_barrage_url(self, room_id: str) -> str:
        """获取斗鱼弹幕服务器地址 - 通过API获取真实的弹幕服务器"""
        try:
            # 斗鱼弹幕服务器地址获取
            url = f'https://www.douyu.com/lapi/live/gateway/web/{room_id}'
            params = {
                'rid': room_id,
                'tt': int(time.time()),
                'did': '12345678901234567890123456789012'
            }

            async with self.session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error') == 0 and data.get('data'):
                        # 解析服务器列表
                        servers = data['data'].get('servers', [])
                        if servers:
                            # 选择延迟最低的服务器
                            best_server = min(servers, key=lambda x: x.get('delay', 999))
                            return f"wss://{best_server['ip']}:{best_server['port']}"

            # 如果API获取失败，返回默认服务器
            return f"wss://danmuproxy.douyu.com:8520/"
        except Exception as e:
            logger.error(f'斗鱼弹幕服务器获取失败: {e}')
            return f"wss://danmuproxy.douyu.com:8520/"

    async def parse_barrage_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析斗鱼弹幕数据 - 实现完整的STT协议解析"""
        barrages = []

        try:
            # 斗鱼弹幕协议解析（STT协议）
            if len(raw_data) < 12:
                return barrages

            # 斗鱼协议头部：4字节长度 + 4字节长度重复 + 2字节类型 + 2字节版本 + 4字节操作码
            packet_len = int.from_bytes(raw_data[0:4], 'little')
            op = int.from_bytes(raw_data[8:12], 'little')

            if packet_len < len(raw_data):
                # 截取有效数据
                data = raw_data[12:packet_len]
            else:
                data = raw_data[12:]

            # 尝试解析文本消息
            try:
                message_str = data.decode('utf-8', errors='ignore')

                # 斗鱼消息格式：type@=chatmsg/rid@=xxx/uid@=xxx/nn@=用户名/txt@=内容/
                if 'type@=' in message_str:
                    # 解析消息类型
                    if 'type@=chatmsg' in message_str:
                        # 弹幕消息
                        barrage = self._parse_douyu_chat_message(message_str)
                        if barrage:
                            barrage['platform'] = self.platform
                            barrage['timestamp'] = datetime.now().isoformat()
                            barrage['type'] = 'danmu'
                            barrages.append(barrage)

                    elif 'type@=dgb' in message_str:
                        # 礼物消息
                        barrage = self._parse_douyu_gift_message(message_str)
                        if barrage:
                            barrage['platform'] = self.platform
                            barrage['timestamp'] = datetime.now().isoformat()
                            barrage['type'] = 'gift'
                            barrages.append(barrage)

                    elif 'type@=uenter' in message_str:
                        # 用户进入直播间
                        barrage = self._parse_douyu_enter_message(message_str)
                        if barrage:
                            barrage['platform'] = self.platform
                            barrage['timestamp'] = datetime.now().isoformat()
                            barrage['type'] = 'welcome'
                            barrages.append(barrage)

                    elif 'type@=online' in message_str or 'type@=loginres' in message_str:
                        # 在线人数更新
                        barrage = {
                            'platform': self.platform,
                            'content': '在线人数更新',
                            'user_id': 'system',
                            'username': 'system',
                            'timestamp': datetime.now().isoformat(),
                            'type': 'online_update'
                        }
                        barrages.append(barrage)

            except Exception as e:
                logger.error(f'斗鱼弹幕解析错误: {e}')

        except Exception as e:
            logger.error(f'斗鱼弹幕数据解析失败: {e}')

        return barrages

    def _parse_douyu_chat_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """解析斗鱼聊天消息"""
        try:
            import urllib.parse

            # 提取关键信息
            uid_match = re.search(r'uid@=([^/]+)', message_str)
            nn_match = re.search(r'nn@=([^/]+)', message_str)
            txt_match = re.search(r'txt@=([^/]+)', message_str)
            level_match = re.search(r'level@=([^/]+)', message_str)
            rg_match = re.search(r'rg@=([^/]+)', message_str)  # 房间等级

            uid = urllib.parse.unquote(uid_match.group(1)) if uid_match else 'unknown'
            username = urllib.parse.unquote(nn_match.group(1)) if nn_match else 'unknown'
            content = urllib.parse.unquote(txt_match.group(1)) if txt_match else ''
            level = urllib.parse.unquote(level_match.group(1)) if level_match else '1'
            room_grade = urllib.parse.unquote(rg_match.group(1)) if rg_match else '1'

            return {
                'user_id': uid,
                'username': username,
                'content': content,
                'level': level,
                'room_grade': room_grade
            }
        except Exception as e:
            logger.error(f'斗鱼聊天消息解析错误: {e}')
            return None

    def _parse_douyu_gift_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """解析斗鱼礼物消息"""
        try:
            import urllib.parse

            # 提取礼物信息
            uid_match = re.search(r'uid@=([^/]+)', message_str)
            nn_match = re.search(r'nn@=([^/]+)', message_str)
            gfid_match = re.search(r'gfid@=([^/]+)', message_str)  # 礼物ID
            gfcnt_match = re.search(r'gfcnt@=([^/]+)', message_str)  # 礼物数量
            hits_match = re.search(r'hits@=([^/]+)', message_str)  # 连击数

            uid = urllib.parse.unquote(uid_match.group(1)) if uid_match else 'unknown'
            username = urllib.parse.unquote(nn_match.group(1)) if nn_match else 'unknown'
            gift_id = urllib.parse.unquote(gfid_match.group(1)) if gfid_match else 'unknown'
            gift_count = urllib.parse.unquote(gfcnt_match.group(1)) if gfcnt_match else '1'
            hits = urllib.parse.unquote(hits_match.group(1)) if hits_match else '1'

            # 常见礼物ID映射
            gift_names = {
                '268': '火箭',
                '200000': '超级火箭',
                '201': '飞机',
                '520': '爱心',
                '1': '鱼丸',
                '2': '鱼翅'
            }

            return {
                'user_id': uid,
                'username': username,
                'content': f"{username} 赠送了 {gift_names.get(gift_id, f'礼物({gift_id})')}",
                'gift_id': gift_id,
                'gift_count': gift_count,
                'hits': hits
            }
        except Exception as e:
            logger.error(f'斗鱼礼物消息解析错误: {e}')
            return None

    def _parse_douyu_enter_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """解析斗鱼用户进入消息"""
        try:
            import urllib.parse

            uid_match = re.search(r'uid@=([^/]+)', message_str)
            nn_match = re.search(r'nn@=([^/]+)', message_str)
            level_match = re.search(r'level@=([^/]+)', message_str)

            uid = urllib.parse.unquote(uid_match.group(1)) if uid_match else 'unknown'
            username = urllib.parse.unquote(nn_match.group(1)) if nn_match else 'unknown'
            level = urllib.parse.unquote(level_match.group(1)) if level_match else '1'

            return {
                'user_id': uid,
                'username': username,
                'content': f"欢迎 {username} 进入直播间",
                'level': level
            }
        except Exception as e:
            logger.error(f'斗鱼进入消息解析错误: {e}')
            return None


class HuyaAdapter(PlatformAdapter):
    """虎牙平台适配器"""

    def __init__(self):
        super().__init__('huya')
        self.base_url = 'https://www.huya.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取虎牙房间信息 - 增强版数据提取"""
        try:
            url = f'{self.base_url}/{room_id}'

            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()

                    # 从HTML中提取房间信息
                    room_info = {}

                    # 提取主播名称
                    uname_match = re.search(r'"nick":"([^"]+)"', html)
                    room_info['streamer_name'] = uname_match.group(1) if uname_match else ''

                    # 提取房间标题
                    title_match = re.search(r'"introduction":"([^"]+)"', html)
                    room_info['title'] = title_match.group(1) if title_match else ''

                    # 提取分类
                    category_match = re.search(r'"gameFullName":"([^"]+)"', html)
                    room_info['category'] = category_match.group(1) if category_match else ''

                    # 提取观看人数
                    viewers_match = re.search(r'"totalCount":"([^"]+)"', html)
                    room_info['viewer_count'] = int(viewers_match.group(1)) if viewers_match else 0

                    # 提取头像URL
                    avatar_match = re.search(r'"avatar180":"([^"]+)"', html)
                    room_info['avatar_url'] = avatar_match.group(1).replace('\\/', '/') if avatar_match else ''

                    # 提取直播状态
                    live_status_match = re.search(r'"isOn":(\d+)', html)
                    room_info['is_live'] = live_status_match.group(1) == '1' if live_status_match else False

                    # 提取开播时间
                    start_time_match = re.search(r'"startTime":"([^"]+)"', html)
                    room_info['start_time'] = start_time_match.group(1) if start_time_match else ''

                    # 提取房间描述
                    desc_match = re.search(r'"description":"([^"]+)"', html)
                    room_info['description'] = desc_match.group(1) if desc_match else ''

                    # 提取粉丝数量
                    fans_match = re.search(r'"fanNum":"([^"]+)"', html)
                    room_info['fans_count'] = int(fans_match.group(1)) if fans_match else 0

                    return {
                        'platform': self.platform,
                        'room_id': room_id,
                        'streamer_name': room_info['streamer_name'],
                        'title': room_info['title'],
                        'category': room_info['category'],
                        'is_live': room_info['is_live'],
                        'viewer_count': room_info['viewer_count'],
                        'start_time': room_info['start_time'],
                        'avatar_url': room_info['avatar_url'],
                        'description': room_info['description'],
                        'fans_count': room_info['fans_count']
                    }
            return {}
        except Exception as e:
            logger.error(f'虎牙房间信息获取失败: {e}')
            return {}

    async def get_live_status(self, room_id: str) -> bool:
        """获取虎牙直播状态"""
        room_info = await self.get_room_info(room_id)
        return room_info.get('is_live', False)

    async def get_barrage_url(self, room_id: str) -> str:
        """获取虎牙弹幕服务器地址 - 通过API获取真实的弹幕服务器"""
        try:
            # 虎牙弹幕服务器地址获取
            url = f'https://www.huya.com/{room_id}'

            async with self.session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    html = await response.text()

                    # 从HTML中提取WebSocket服务器地址
                    ws_match = re.search(r'ws://([^/]+)', html)
                    wss_match = re.search(r'wss://([^/]+)', html)

                    if wss_match:
                        return f"wss://{wss_match.group(1)}"
                    elif ws_match:
                        return f"wss://{ws_match.group(1)}"  # 升级为WSS

            # 如果提取失败，返回默认服务器
            return f"wss://cdnws.api.huya.com/"
        except Exception as e:
            logger.error(f'虎牙弹幕服务器获取失败: {e}')
            return f"wss://cdnws.api.huya.com/"

    async def parse_barrage_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析虎牙弹幕数据 - 实现完整的虎牙协议解析"""
        barrages = []

        try:
            # 尝试解析JSON格式的消息
            message_str = raw_data.decode('utf-8', errors='ignore')

            # 虎牙消息格式分析
            if 'chatMsg' in message_str or 'type' in message_str:
                try:
                    # 尝试解析为JSON
                    import json
                    messages = json.loads(message_str)

                    # 虎牙消息可能是数组或单个对象
                    if isinstance(messages, list):
                        message_list = messages
                    else:
                        message_list = [messages]

                    for message in message_list:
                        barrage = self._parse_huya_message(message)
                        if barrage:
                            barrage['platform'] = self.platform
                            barrage['timestamp'] = datetime.now().isoformat()
                            barrages.append(barrage)

                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试解析文本格式
                    barrage = self._parse_huya_text_message(message_str)
                    if barrage:
                        barrage['platform'] = self.platform
                        barrage['timestamp'] = datetime.now().isoformat()
                        barrages.append(barrage)

            elif message_str.strip():
                # 处理纯文本消息
                barrage = self._parse_huya_text_message(message_str)
                if barrage:
                    barrage['platform'] = self.platform
                    barrage['timestamp'] = datetime.now().isoformat()
                    barrages.append(barrage)

        except Exception as e:
            logger.error(f'虎牙弹幕数据解析失败: {e}')

        return barrages

    def _parse_huya_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析虎牙JSON消息"""
        try:
            msg_type = message.get('type')

            if msg_type == 'chatMsg':
                # 弹幕消息
                return {
                    'user_id': str(message.get('uid', 'unknown')),
                    'username': message.get('senderName', 'unknown'),
                    'content': message.get('content', ''),
                    'level': message.get('senderLevel', '1'),
                    'type': 'danmu'
                }

            elif msg_type == 'giftMsg':
                # 礼物消息
                return {
                    'user_id': str(message.get('uid', 'unknown')),
                    'username': message.get('senderName', 'unknown'),
                    'content': f"{message.get('senderName', 'unknown')} 赠送了 {message.get('giftName', '礼物')}",
                    'gift_name': message.get('giftName'),
                    'gift_count': message.get('giftCount', 1),
                    'type': 'gift'
                }

            elif msg_type == 'enterRoom':
                # 进入房间消息
                return {
                    'user_id': str(message.get('uid', 'unknown')),
                    'username': message.get('senderName', 'unknown'),
                    'content': f"欢迎 {message.get('senderName', 'unknown')} 进入直播间",
                    'type': 'welcome'
                }

            elif msg_type == 'liveStart':
                # 直播开始
                return {
                    'user_id': 'system',
                    'username': 'system',
                    'content': '直播已开始',
                    'type': 'live_start'
                }

            elif msg_type == 'liveEnd':
                # 直播结束
                return {
                    'user_id': 'system',
                    'username': 'system',
                    'content': '直播已结束',
                    'type': 'live_end'
                }

        except Exception as e:
            logger.error(f'虎牙JSON消息解析错误: {e}')

        return None

    def _parse_huya_text_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """解析虎牙文本消息"""
        try:
            # 虎牙文本消息格式可能包含特定标识
            if '发送弹幕' in message_str or '聊天' in message_str:
                # 简单提取内容
                content_match = re.search(r'content[:：]\s*([^,，]+)', message_str)
                user_match = re.search(r'user[:：]\s*([^,，]+)', message_str)

                return {
                    'user_id': 'unknown',
                    'username': user_match.group(1) if user_match else 'unknown',
                    'content': content_match.group(1) if content_match else message_str[:50],
                    'type': 'danmu'
                }

            elif '礼物' in message_str:
                return {
                    'user_id': 'unknown',
                    'username': 'unknown',
                    'content': message_str[:50],
                    'type': 'gift'
                }

            elif '进入' in message_str:
                return {
                    'user_id': 'unknown',
                    'username': 'unknown',
                    'content': message_str[:50],
                    'type': 'welcome'
                }

        except Exception as e:
            logger.error(f'虎牙文本消息解析错误: {e}')

        return None


class CrawlerService(LoggerMixin):
    """
    爬虫服务类，负责多平台直播数据抓取
    """

    def __init__(self, app_settings, rabbitmq_service):
        self.settings = app_settings
        self.rabbitmq_service = rabbitmq_service
        self.session = None
        self.is_running_flag = False
        self.monitoring_tasks = {}
        self.platform_adapters = {
            'bilibili': BilibiliAdapter(),
            'douyu': DouyuAdapter(),
            'huya': HuyaAdapter()
        }

        # AI Agent工作流
        self.local_filter = LocalFilterService()
        self.ai_orchestrator = None  # 将在initialize中初始化

    async def initialize(self):
        """初始化爬虫服务"""
        try:
            # 创建HTTP会话
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

            # 初始化所有平台适配器
            for adapter in self.platform_adapters.values():
                if hasattr(adapter, 'initialize'):
                    await adapter.initialize(self.session)
                else:
                    adapter.session = self.session

            # 初始化AI Agent工作流
            from services.ai_service import AIService
            ai_service = AIService(self.settings)
            ai_service.initialize()

            # 从环境变量获取DeepSeek API密钥
            import os
            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')

            self.ai_orchestrator = AIOrchestrator(ai_service, deepseek_api_key)

            # 启动AI请求处理任务
            asyncio.create_task(self._ai_request_processor())

            self.logger.info("爬虫服务初始化完成")

        except Exception as e:
            self.logger.error(f"爬虫服务初始化失败: {e}")
            raise

    async def close(self):
        """关闭爬虫服务"""
        try:
            if self.session:
                await self.session.close()

            # 停止所有监控任务
            for task_id, task in self.monitoring_tasks.items():
                if not task.done():
                    task.cancel()

            self.monitoring_tasks.clear()
            self.is_running_flag = False

            self.logger.info("爬虫服务已关闭")

        except Exception as e:
            self.logger.error(f"爬虫服务关闭失败: {e}")

    def is_running(self) -> bool:
        """检查爬虫服务是否运行"""
        return self.is_running_flag

    async def start_crawling(self, platform: str, room_id: str) -> bool:
        """启动爬虫监控"""
        try:
            task_key = f"{platform}:{room_id}"

            if task_key in self.monitoring_tasks:
                self.logger.warning(f"任务已存在: {task_key}")
                return False

            # 验证平台支持
            if platform not in self.platform_adapters:
                self.logger.error(f"不支持的平台: {platform}")
                return False

            # 创建监控任务
            task = asyncio.create_task(
                self._monitor_room(platform, room_id)
            )

            self.monitoring_tasks[task_key] = task
            self.is_running_flag = True

            self.logger.info(f"开始监控 {platform} 房间 {room_id}")
            return True

        except Exception as e:
            self.logger.error(f"启动爬虫失败: {e}")
            return False

    async def stop_crawling(self, platform: str, room_id: str) -> bool:
        """停止爬虫监控"""
        try:
            task_key = f"{platform}:{room_id}"

            if task_key in self.monitoring_tasks:
                task = self.monitoring_tasks[task_key]
                if not task.done():
                    task.cancel()

                del self.monitoring_tasks[task_key]
                self.logger.info(f"停止监控 {platform} 房间 {room_id}")

                # 如果没有活跃任务，停止服务
                if not self.monitoring_tasks:
                    self.is_running_flag = False

                return True

            return False

        except Exception as e:
            self.logger.error(f"停止爬虫失败: {e}")
            return False

    async def _monitor_room(self, platform: str, room_id: str):
        """监控指定房间"""
        adapter = self.platform_adapters[platform]

        while True:
            try:
                # 检查直播状态
                is_live = await adapter.get_live_status(room_id)

                if is_live:
                    # 获取房间信息
                    room_info = await adapter.get_room_info(room_id)

                    if room_info:
                        # 发送房间信息到消息队列
                        await self.rabbitmq_service.publish(
                            'room_info',
                            {
                                'type': 'room_info',
                                'platform': platform,
                                'room_id': room_id,
                                'data': room_info,
                                'timestamp': datetime.now().isoformat()
                            }
                        )

                    # 对于B站和斗鱼，使用专门的弹幕适配器
                    if platform in ['bilibili', 'douyu']:
                        # 连接到弹幕服务器
                        success = await adapter.connect_to_danmaku(
                            room_id,
                            lambda msg: self._handle_platform_message(adapter, platform, room_id, msg)
                        )
                        if success:
                            self.logger.info(f"{platform}弹幕连接建立成功: {room_id}")
                            # 保持连接
                            while adapter.is_connected():
                                await asyncio.sleep(10)
                        else:
                            self.logger.error(f"{platform}弹幕连接失败: {room_id}")
                    else:
                        # 其他平台使用原有的弹幕监听方式
                        barrage_url = await adapter.get_barrage_url(room_id)
                        if barrage_url:
                            await self._listen_barrage(adapter, barrage_url, room_id)

                # 等待下一次检查
                await asyncio.sleep(self.settings.crawler_interval)

            except asyncio.CancelledError:
                self.logger.info(f"监控任务被取消: {platform}:{room_id}")
                break
            except Exception as e:
                self.logger.error(f"监控房间异常: {e}")
                await asyncio.sleep(5)  # 错误后等待

    async def _listen_barrage(self, adapter: PlatformAdapter, barrage_url: str, room_id: str):
        """监听弹幕数据"""
        try:
            import websockets

            async with websockets.connect(barrage_url) as websocket:
                self.logger.info(f"已连接到弹幕服务器: {barrage_url}")

                while True:
                    try:
                        # 接收弹幕数据
                        raw_data = await websocket.recv()

                        # 解析弹幕
                        barrages = await adapter.parse_barrage_data(raw_data)

                        # 发送弹幕数据到消息队列
                        for barrage in barrages:
                            await self.rabbitmq_service.publish(
                                'barrage_data',
                                {
                                    'type': 'barrage',
                                    'platform': adapter.platform,
                                    'room_id': room_id,
                                    'data': barrage,
                                    'timestamp': datetime.now().isoformat()
                                }
                            )

                    except websockets.ConnectionClosed:
                        self.logger.warning("弹幕连接断开，尝试重连...")
                        break
                    except Exception as e:
                        self.logger.error(f"弹幕接收错误: {e}")
                        await asyncio.sleep(1)

        except Exception as e:
            self.logger.error(f"弹幕监听失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        """获取爬虫状态"""
        return {
            'is_running': self.is_running_flag,
            'active_tasks': len(self.monitoring_tasks),
            'tasks': list(self.monitoring_tasks.keys()),
            'platforms': list(self.platform_adapters.keys())
        }

    async def check_live_status(self):
        """检查所有监控房间的直播状态"""
        try:
            for task_key in list(self.monitoring_tasks.keys()):
                platform, room_id = task_key.split(':', 1)

                try:
                    adapter = self.platform_adapters[platform]
                    is_live = await adapter.get_live_status(room_id)

                    # 发送直播状态更新
                    await self.rabbitmq_service.publish(
                        'live_status',
                        {
                            'type': 'live_status',
                            'platform': platform,
                            'room_id': room_id,
                            'is_live': is_live,
                            'timestamp': datetime.now().isoformat()
                        }
                    )

                except Exception as e:
                    self.logger.error(f"检查直播状态失败 {task_key}: {e}")

        except Exception as e:
            self.logger.error(f"批量检查直播状态失败: {e}")

    async def start_monitoring(self):
        """启动监控服务"""
        self.logger.info("启动爬虫监控服务")
        # 这里可以添加定时任务等

    async def _handle_platform_message(self, adapter, platform: str, room_id: str, message: Dict[str, Any]):
        """处理平台消息（B站、斗鱼等）"""
        try:
            # 解析弹幕消息
            barrages = await adapter.parse_danmaku_message(message)

            # 发送弹幕数据到消息队列
            for barrage in barrages:
                await self.rabbitmq_service.publish(
                    'barrage_data',
                    {
                        'type': 'barrage',
                        'platform': platform,
                        'room_id': room_id,
                        'data': barrage,
                        'timestamp': datetime.now().isoformat()
                    }
                )

                self.logger.debug(f"{platform}弹幕: {barrage['username']}: {barrage['content']}")

        except Exception as e:
            self.logger.error(f"处理{platform}消息失败: {e}")

    def reinitialize(self):
        """重新初始化服务"""
        self.logger.info("重新初始化爬虫服务")
        asyncio.create_task(self.close())
        time.sleep(2)
        asyncio.create_task(self.initialize())