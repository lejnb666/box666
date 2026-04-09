#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
斗鱼直播平台适配器 - 实现WebSocket连接和协议解析

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import struct
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any

import aiohttp
import websockets
from loguru import logger


class DouyuAdapter:
    """
    斗鱼直播平台适配器，处理WebSocket连接和STT协议解析
    """

    def __init__(self):
        self.platform = 'douyu'
        self.base_url = 'https://www.douyu.com'
        self.api_url = 'https://www.douyu.com/lapi'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = None
        self.websocket = None
        self.room_id = None
        self.connected = False
        self.heartbeat_task = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def initialize(self, session: aiohttp.ClientSession):
        """初始化适配器"""
        self.session = session
        logger.info("斗鱼适配器初始化完成")

    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取斗鱼房间信息"""
        try:
            url = f'{self.api_url}/live/getRoomInfo'
            params = {'rid': room_id}

            async with self.session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error') == 0 and data.get('data'):
                        room_data = data['data']
                        return {
                            'platform': self.platform,
                            'room_id': room_id,
                            'streamer_name': room_data.get('nickname', ''),
                            'title': room_data.get('room_name', ''),
                            'category': room_data.get('cate_name', ''),
                            'is_live': room_data.get('show_status') == 1,
                            'viewer_count': room_data.get('online', 0),
                            'start_time': room_data.get('start_time', ''),
                            'avatar_url': room_data.get('avatar', ''),
                            'room_notice': room_data.get('room_notice', ''),
                            'room_description': room_data.get('room_description', '')
                        }
            return {}
        except Exception as e:
            logger.error(f"斗鱼房间信息获取失败 {room_id}: {e}")
            return {}

    async def get_live_status(self, room_id: str) -> bool:
        """获取斗鱼直播状态"""
        try:
            room_info = await self.get_room_info(room_id)
            return room_info.get('is_live', False)
        except Exception as e:
            logger.error(f"斗鱼直播状态获取失败 {room_id}: {e}")
            return False

    async def get_danmaku_server_info(self, room_id: str) -> Dict[str, Any]:
        """获取斗鱼弹幕服务器信息"""
        try:
            url = f'{self.api_url}/live/gateway/web/{room_id}'
            params = {
                'rid': room_id,
                'tt': int(time.time()),
                'did': '12345678901234567890123456789012'
            }

            async with self.session.get(url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('error') == 0 and data.get('data'):
                        return {
                            'servers': data['data'].get('servers', []),
                            'auth': data['data'].get('auth', ''),
                            'group': data['data'].get('group', ''),
                            'rid': data['data'].get('rid', room_id)
                        }
            return {}
        except Exception as e:
            logger.error(f"斗鱼弹幕服务器信息获取失败 {room_id}: {e}")
            return {}

    async def connect_to_danmaku(self, room_id: str, message_handler) -> bool:
        """连接到斗鱼弹幕服务器"""
        try:
            self.room_id = room_id

            # 获取弹幕服务器信息
            server_info = await self.get_danmaku_server_info(room_id)
            if not server_info:
                logger.error(f"无法获取弹幕服务器信息: {room_id}")
                return False

            # 选择最佳服务器（延迟最低的）
            servers = server_info.get('servers', [])
            if not servers:
                logger.error(f"无可用弹幕服务器: {room_id}")
                return False

            # 按延迟排序选择最佳服务器
            best_server = min(servers, key=lambda x: x.get('delay', 999))
            server_url = f"wss://{best_server['ip']}:{best_server['port']}"

            logger.info(f"连接到斗鱼弹幕服务器: {server_url}")

            # 建立WebSocket连接
            self.websocket = await websockets.connect(
                server_url,
                extra_headers=self.headers
            )

            # 发送登录认证消息
            login_msg = self._build_stt_message({
                'type': 'loginreq',
                'roomid': int(room_id),
                'doid': '12345678901234567890123456789012'
            })
            await self.websocket.send(login_msg)

            # 发送加入房间组消息
            join_msg = self._build_stt_message({
                'type': 'joingroup',
                'rid': int(room_id),
                'gid': server_info.get('group', '9999')
            })
            await self.websocket.send(join_msg)

            # 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 启动消息接收循环
            asyncio.create_task(self._message_loop(message_handler))

            self.connected = True
            self.reconnect_attempts = 0

            logger.info(f"成功连接到斗鱼弹幕服务器: {room_id}")
            return True

        except Exception as e:
            logger.error(f"连接到斗鱼弹幕服务器失败 {room_id}: {e}")
            await self._handle_connection_error()
            return False

    def _build_stt_message(self, data: Dict[str, Any]) -> bytes:
        """构建斗鱼STT协议消息"""
        try:
            # STT协议格式：长度(4) + 长度重复(4) + 类型(2) + 版本(2) + 操作码(4) + 数据
            message_str = ''
            for key, value in data.items():
                if isinstance(value, str):
                    message_str += f"{key}@={value}/"
                else:
                    message_str += f"{key}@={str(value)}/"

            message_bytes = message_str.encode('utf-8')
            message_len = len(message_bytes) + 12  # 数据长度 + 头部12字节

            # 构建头部
            header = struct.pack('<IIHH', message_len, message_len, 689, 1)

            return header + message_bytes

        except Exception as e:
            logger.error(f"构建STT消息失败: {e}")
            return b''

    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.connected and self.websocket:
                try:
                    # 发送心跳消息
                    heartbeat_msg = self._build_stt_message({
                        'type': 'mrkl'
                    })
                    await self.websocket.send(heartbeat_msg)

                    # 等待45秒（斗鱼要求45秒一次心跳）
                    await asyncio.sleep(45)

                except websockets.ConnectionClosed:
                    logger.warning("斗鱼心跳包发送时连接已关闭")
                    break
                except Exception as e:
                    logger.error(f"斗鱼心跳包发送失败: {e}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("斗鱼心跳任务被取消")
        except Exception as e:
            logger.error(f"斗鱼心跳循环异常: {e}")

    async def _message_loop(self, message_handler):
        """消息接收循环"""
        try:
            while self.connected and self.websocket:
                try:
                    # 接收数据
                    raw_data = await self.websocket.recv()

                    # 解析STT协议
                    messages = self._parse_stt_packet(raw_data)

                    # 处理消息
                    for message in messages:
                        await message_handler(message)

                except websockets.ConnectionClosed as e:
                    logger.warning(f"斗鱼WebSocket连接关闭: {e}")
                    await self._handle_connection_error()
                    break
                except Exception as e:
                    logger.error(f"斗鱼消息接收错误: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("斗鱼消息循环任务被取消")
        except Exception as e:
            logger.error(f"斗鱼消息循环异常: {e}")
            await self._handle_connection_error()

    def _parse_stt_packet(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析斗鱼STT协议数据包"""
        messages = []

        try:
            offset = 0
            while offset < len(raw_data):
                # 检查数据完整性
                if offset + 12 > len(raw_data):
                    break

                # 解析头部
                header_data = raw_data[offset:offset + 12]
                packet_len, _, msg_type, _ = struct.unpack('<IIHH', header_data)

                # 检查数据完整性
                if offset + packet_len > len(raw_data):
                    break

                # 提取数据部分
                data_start = offset + 12
                data_end = offset + packet_len
                data_bytes = raw_data[data_start:data_end]

                # 解析消息内容
                if msg_type == 690:  # 普通消息
                    try:
                        message_str = data_bytes.decode('utf-8', errors='ignore')
                        message_dict = self._parse_douyu_message(message_str)
                        if message_dict:
                            messages.append(message_dict)
                    except Exception as e:
                        logger.error(f"斗鱼消息解析失败: {e}")

                # 移动到下一个数据包
                offset += packet_len

        except Exception as e:
            logger.error(f"斗鱼数据包解析失败: {e}")

        return messages

    def _parse_douyu_message(self, message_str: str) -> Optional[Dict[str, Any]]:
        """解析斗鱼消息字符串"""
        try:
            if '@=' not in message_str:
                return None

            # 解析键值对
            message_dict = {}
            parts = message_str.split('/')

            for part in parts:
                if '@=' in part:
                    key, value = part.split('@=', 1)
                    # 处理转义字符
                    value = value.replace('\\/', '/').replace('\\@', '@')
                    message_dict[key] = urllib.parse.unquote(value)

            return message_dict

        except Exception as e:
            logger.error(f"斗鱼消息字符串解析失败: {e}")
            return None

    async def _handle_connection_error(self):
        """处理连接错误"""
        self.connected = False

        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None

        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None

        # 指数退避重连
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = 1 * (2 ** (self.reconnect_attempts - 1))
            delay = min(delay, 60)  # 最大延迟60秒

            logger.info(f"斗鱼将在 {delay} 秒后尝试重连 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts})")

            await asyncio.sleep(delay)

            # 重新连接
            if self.room_id:
                success = await self.connect_to_danmaku(self.room_id, None)
                if success:
                    logger.info(f"斗鱼重连成功: {self.room_id}")
                    return

        logger.error(f"斗鱼重连失败，已达到最大重连次数: {self.room_id}")

    async def disconnect(self):
        """断开连接"""
        try:
            self.connected = False

            if self.websocket:
                # 发送登出消息
                logout_msg = self._build_stt_message({
                    'type': 'logout'
                })
                try:
                    await self.websocket.send(logout_msg)
                except:
                    pass

                await self.websocket.close()
                self.websocket = None

            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None

            logger.info(f"已断开斗鱼弹幕连接: {self.room_id}")

        except Exception as e:
            logger.error(f"斗鱼断开连接失败: {e}")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.websocket is not None

    async def parse_danmaku_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析斗鱼弹幕消息"""
        barrages = []

        try:
            msg_type = message.get('type')

            if msg_type == 'chatmsg':
                # 弹幕消息
                barrage = {
                    'platform': self.platform,
                    'type': 'danmu',
                    'content': message.get('txt', ''),
                    'user_id': message.get('uid', 'unknown'),
                    'username': message.get('nn', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'level': message.get('level', '1'),
                    'user_level': message.get('ul', '1'),
                    'is_vip': message.get('is_vip', '0') == '1',
                    'is_svip': message.get('is_svip', '0') == '1',
                    'is_admin': message.get('is_admin', '0') == '1',
                    'raw_data': message
                }
                barrages.append(barrage)

            elif msg_type == 'dgb':
                # 礼物消息
                barrage = {
                    'platform': self.platform,
                    'type': 'gift',
                    'content': f"{message.get('nn', 'unknown')} 赠送了 {message.get('gfid', 'unknown')}",
                    'user_id': message.get('uid', 'unknown'),
                    'username': message.get('nn', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'gift_id': message.get('gfid', 'unknown'),
                    'gift_name': message.get('gfn', 'unknown'),
                    'gift_count': message.get('gfcnt', '1'),
                    'hits': message.get('hits', '1'),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif msg_type == 'uenter':
                # 用户进入直播间
                barrage = {
                    'platform': self.platform,
                    'type': 'welcome',
                    'content': f"欢迎 {message.get('nn', 'unknown')} 进入直播间",
                    'user_id': message.get('uid', 'unknown'),
                    'username': message.get('nn', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'is_rich': message.get('is_rich', '0') == '1',
                    'is_admin': message.get('is_admin', '0') == '1',
                    'raw_data': message
                }
                barrages.append(barrage)

            elif msg_type == 'online':
                # 在线人数更新
                barrage = {
                    'platform': self.platform,
                    'type': 'online_update',
                    'content': f"当前在线: {message.get('ol', '0')}人",
                    'user_id': 'system',
                    'username': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'online_count': message.get('ol', '0'),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif msg_type == 'rss':
                # 直播状态更新
                is_live = message.get('ss', '0') == '1'
                barrage = {
                    'platform': self.platform,
                    'type': 'live_start' if is_live else 'live_end',
                    'content': '直播已开始' if is_live else '直播已结束',
                    'user_id': 'system',
                    'username': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'is_live': is_live,
                    'raw_data': message
                }
                barrages.append(barrage)

        except Exception as e:
            logger.error(f"斗鱼弹幕消息解析错误: {e}")

        return barrages


# 使用示例
async def main():
    """测试斗鱼适配器"""
    adapter = DouyuAdapter()

    async def message_handler(message):
        """消息处理器"""
        barrages = await adapter.parse_danmaku_message(message)
        for barrage in barrages:
            logger.info(f"收到斗鱼弹幕: {barrage['username']}: {barrage['content']}")

    # 连接到测试房间
    success = await adapter.connect_to_danmaku('288016', message_handler)
    if success:
        logger.info("斗鱼连接成功，开始监听弹幕...")

        # 运行10分钟
        await asyncio.sleep(600)

        await adapter.disconnect()
    else:
        logger.error("斗鱼连接失败")


if __name__ == '__main__':
    asyncio.run(main())