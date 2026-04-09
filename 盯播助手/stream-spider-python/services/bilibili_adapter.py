#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
B站直播平台适配器 - 实现真实的WebSocket连接和Protobuf解析

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import struct
import gzip
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import aiohttp
import websockets
from loguru import logger

# 使用 bilibili_api 库处理B站协议
from bilibili_api import live, sync, exceptions
from bilibili_api.live import LiveDanmaku
from bilibili_api.utils.network_helpers import get_session


class BilibiliAdapter:
    """
    B站直播平台适配器，处理WebSocket连接和Protobuf解析
    """

    def __init__(self):
        self.platform = 'bilibili'
        self.base_url = 'https://api.live.bilibili.com'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = None
        self.websocket = None
        self.room_id = None
        self.room_real_id = None
        self.connected = False
        self.heartbeat_task = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1

    async def initialize(self, session: aiohttp.ClientSession):
        """初始化适配器"""
        self.session = session
        logger.info("B站适配器初始化完成")

    async def get_room_info(self, room_id: str) -> Dict[str, Any]:
        """获取B站房间信息"""
        try:
            # 使用bilibili_api-python库获取房间信息
            def fetch_room_info():
                try:
                    room = live.LiveRoom(room_id=int(room_id))
                    return room.get_room_info()
                except Exception as e:
                    logger.error(f"获取房间信息失败: {e}")
                    return None

            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            room_info = await loop.run_in_executor(None, fetch_room_info)

            if room_info and 'room_info' in room_info:
                info = room_info['room_info']
                return {
                    'platform': self.platform,
                    'room_id': room_id,
                    'real_room_id': info.get('room_id', room_id),
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
                    'tags': info.get('tags', '').split(',') if info.get('tags') else []
                }
            return {}
        except Exception as e:
            logger.error(f"B站房间信息获取失败 {room_id}: {e}")
            return {}

    async def get_live_status(self, room_id: str) -> bool:
        """获取B站直播状态"""
        try:
            room_info = await self.get_room_info(room_id)
            return room_info.get('is_live', False)
        except Exception as e:
            logger.error(f"B站直播状态获取失败 {room_id}: {e}")
            return False

    async def get_danmaku_server_info(self, room_id: str) -> Dict[str, Any]:
        """获取B站弹幕服务器信息"""
        try:
            def fetch_danmaku_info():
                try:
                    room = live.LiveRoom(room_id=int(room_id))
                    return room.get_danmu_info()
                except Exception as e:
                    logger.error(f"获取弹幕服务器信息失败: {e}")
                    return None

            loop = asyncio.get_event_loop()
            danmaku_info = await loop.run_in_executor(None, fetch_danmaku_info)

            if danmaku_info:
                return {
                    'host_list': danmaku_info.get('host_list', []),
                    'token': danmaku_info.get('token', ''),
                    'refresh_row_factor': danmaku_info.get('refresh_row_factor', 0.75),
                    'refresh_rate': danmaku_info.get('refresh_rate', 30),
                    'max_delay': danmaku_info.get('max_delay', 5),
                    'port': danmaku_info.get('port', 443),
                    'protocol': danmaku_info.get('protocol', 1)
                }
            return {}
        except Exception as e:
            logger.error(f"B站弹幕服务器信息获取失败 {room_id}: {e}")
            return {}

    async def connect_to_danmaku(self, room_id: str, message_handler) -> bool:
        """连接到B站弹幕服务器"""
        try:
            self.room_id = room_id

            # 获取房间真实ID
            room_info = await self.get_room_info(room_id)
            if not room_info:
                logger.error(f"无法获取房间信息: {room_id}")
                return False

            self.room_real_id = room_info.get('real_room_id', room_id)

            # 获取弹幕服务器信息
            danmaku_info = await self.get_danmaku_server_info(self.room_real_id)
            if not danmaku_info:
                logger.error(f"无法获取弹幕服务器信息: {room_id}")
                return False

            # 选择最佳服务器
            host_list = danmaku_info.get('host_list', [])
            if not host_list:
                logger.error(f"无可用弹幕服务器: {room_id}")
                return False

            # 选择第一个支持WSS的服务器
            best_server = None
            for host in host_list:
                if host.get('wss_port') or 'wss' in host.get('host', ''):
                    best_server = host
                    break

            if not best_server:
                best_server = host_list[0]  # 使用第一个服务器

            # 构建WebSocket URL
            host = best_server['host']
            port = best_server.get('wss_port', 443)
            websocket_url = f"wss://{host}:{port}/sub"

            logger.info(f"连接到B站弹幕服务器: {websocket_url}")

            # 建立WebSocket连接
            self.websocket = await websockets.connect(
                websocket_url,
                extra_headers=self.headers
            )

            # 发送认证包
            auth_data = {
                'uid': 0,  # 游客UID
                'roomid': self.room_real_id,
                'protover': 3,
                'platform': 'web',
                'type': 2,
                'key': danmaku_info.get('token', '')
            }

            await self._send_packet(1, 7, auth_data)
            logger.info(f"发送认证包到B站弹幕服务器: {self.room_real_id}")

            # 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            # 启动消息接收循环
            asyncio.create_task(self._message_loop(message_handler))

            self.connected = True
            self.reconnect_attempts = 0
            self.reconnect_delay = 1

            logger.info(f"成功连接到B站弹幕服务器: {room_id}")
            return True

        except Exception as e:
            logger.error(f"连接到B站弹幕服务器失败 {room_id}: {e}")
            await self._handle_connection_error()
            return False

    async def _send_packet(self, packet_len: int, operation: int, data: Any) -> None:
        """发送B站协议数据包"""
        try:
            # B站协议格式：
            # 4字节长度 + 4字节长度重复 + 2字节协议版本 + 2字节操作码 + 4字节头部长度 + 数据

            if isinstance(data, dict):
                data_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
            elif isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = bytes(data)

            # 计算包长度
            header_len = 16  # 固定头部长度
            total_len = header_len + len(data_bytes)

            # 构建头部
            header = struct.pack(
                '>IHHII',
                total_len,  # 包长度
                total_len,  # 包长度重复
                1,          # 协议版本
                operation,  # 操作码
                header_len  # 头部长度
            )

            # 发送数据
            packet = header + data_bytes
            await self.websocket.send(packet)

        except Exception as e:
            logger.error(f"发送数据包失败: {e}")

    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self.connected and self.websocket:
                try:
                    # 发送心跳包
                    heartbeat_data = {
                        'roomid': self.room_real_id
                    }
                    await self._send_packet(1, 2, heartbeat_data)

                    # 等待30秒
                    await asyncio.sleep(30)

                except websockets.ConnectionClosed:
                    logger.warning("心跳包发送时连接已关闭")
                    break
                except Exception as e:
                    logger.error(f"心跳包发送失败: {e}")
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            logger.info("心跳任务被取消")
        except Exception as e:
            logger.error(f"心跳循环异常: {e}")

    async def _message_loop(self, message_handler):
        """消息接收循环"""
        try:
            while self.connected and self.websocket:
                try:
                    # 接收数据
                    raw_data = await self.websocket.recv()

                    # 解析数据包
                    messages = self._parse_packet(raw_data)

                    # 处理消息
                    for message in messages:
                        await message_handler(message)

                except websockets.ConnectionClosed as e:
                    logger.warning(f"WebSocket连接关闭: {e}")
                    await self._handle_connection_error()
                    break
                except Exception as e:
                    logger.error(f"消息接收错误: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("消息循环任务被取消")
        except Exception as e:
            logger.error(f"消息循环异常: {e}")
            await self._handle_connection_error()

    def _parse_packet(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """解析B站协议数据包"""
        messages = []

        try:
            offset = 0
            while offset < len(raw_data):
                # 解析头部
                if offset + 16 > len(raw_data):
                    break

                header_data = raw_data[offset:offset + 16]
                packet_len, _, proto_ver, operation, header_len = struct.unpack('>IHHII', header_data)

                # 检查数据完整性
                if offset + packet_len > len(raw_data):
                    break

                # 提取数据部分
                data_start = offset + header_len
                data_end = offset + packet_len
                data_bytes = raw_data[data_start:data_end]

                # 根据操作码处理数据
                if operation == 5:  # 命令消息
                    if proto_ver == 0:  # JSON格式
                        try:
                            message = json.loads(data_bytes.decode('utf-8'))
                            messages.append(message)
                        except:
                            pass
                    elif proto_ver == 2:  # Gzip压缩
                        try:
                            decompressed = gzip.decompress(data_bytes)
                            message = json.loads(decompressed.decode('utf-8'))
                            messages.append(message)
                        except:
                            pass

                # 移动到下一个数据包
                offset += packet_len

        except Exception as e:
            logger.error(f"数据包解析失败: {e}")

        return messages

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
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
            delay = min(delay, 60)  # 最大延迟60秒

            logger.info(f"将在 {delay} 秒后尝试重连 (尝试 {self.reconnect_attempts}/{self.max_reconnect_attempts})")

            await asyncio.sleep(delay)

            # 重新连接
            if self.room_id:
                success = await self.connect_to_danmaku(self.room_id, None)
                if success:
                    logger.info(f"重连成功: {self.room_id}")
                    return

        logger.error(f"重连失败，已达到最大重连次数: {self.room_id}")

    async def disconnect(self):
        """断开连接"""
        try:
            self.connected = False

            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                self.heartbeat_task = None

            logger.info(f"已断开B站弹幕连接: {self.room_id}")

        except Exception as e:
            logger.error(f"断开连接失败: {e}")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.websocket is not None

    async def parse_danmaku_message(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析弹幕消息"""
        barrages = []

        try:
            cmd = message.get('cmd', '')

            if cmd == 'DANMU_MSG':
                # 弹幕消息
                if len(message.get('info', [])) >= 3:
                    barrage = {
                        'platform': self.platform,
                        'type': 'danmu',
                        'content': message['info'][1],
                        'user_id': str(message['info'][2][0]) if message['info'][2] else 'unknown',
                        'username': message['info'][2][1] if message['info'][2] else 'unknown',
                        'timestamp': datetime.now().isoformat(),
                        'medal_level': message['info'][3][0] if len(message['info']) > 3 and message['info'][3] else None,
                        'medal_name': message['info'][3][1] if len(message['info']) > 3 and message['info'][3] else None,
                        'medal_room': message['info'][3][3] if len(message['info']) > 3 and message['info'][3] else None,
                        'user_level': message['info'][4][0] if len(message['info']) > 4 and message['info'][4] else None,
                        'is_admin': message['info'][2][2] if message['info'][2] else 0,
                        'is_vip': message['info'][2][3] if len(message['info'][2]) > 3 else 0,
                        'raw_data': message
                    }
                    barrages.append(barrage)

            elif cmd == 'SEND_GIFT':
                # 礼物消息
                gift_data = message.get('data', {})
                barrage = {
                    'platform': self.platform,
                    'type': 'gift',
                    'content': f"{gift_data.get('uname', 'unknown')} 赠送了 {gift_data.get('giftName', 'unknown')}",
                    'user_id': str(gift_data.get('uid', 'unknown')),
                    'username': gift_data.get('uname', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'gift_name': gift_data.get('giftName'),
                    'gift_count': gift_data.get('num'),
                    'gift_price': gift_data.get('price'),
                    'total_coin': gift_data.get('total_coin'),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif cmd == 'WELCOME':
                # 欢迎消息
                welcome_data = message.get('data', {})
                barrage = {
                    'platform': self.platform,
                    'type': 'welcome',
                    'content': f"欢迎 {welcome_data.get('uname', 'unknown')} 进入直播间",
                    'user_id': str(welcome_data.get('uid', 'unknown')),
                    'username': welcome_data.get('uname', 'unknown'),
                    'timestamp': datetime.now().isoformat(),
                    'is_admin': welcome_data.get('is_admin', False),
                    'is_vip': welcome_data.get('is_vip', False),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif cmd == 'LIVE':
                # 直播开始
                barrage = {
                    'platform': self.platform,
                    'type': 'live_start',
                    'content': '直播已开始',
                    'user_id': 'system',
                    'username': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif cmd == 'PREPARING':
                # 直播准备中（直播结束）
                barrage = {
                    'platform': self.platform,
                    'type': 'live_end',
                    'content': '直播已结束',
                    'user_id': 'system',
                    'username': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'raw_data': message
                }
                barrages.append(barrage)

            elif cmd == 'ROOM_REAL_TIME_MESSAGE_UPDATE':
                # 房间信息更新
                update_data = message.get('data', {})
                barrage = {
                    'platform': self.platform,
                    'type': 'room_update',
                    'content': f"房间粉丝数更新: {update_data.get('fans', 0)}",
                    'user_id': 'system',
                    'username': 'system',
                    'timestamp': datetime.now().isoformat(),
                    'fans_count': update_data.get('fans', 0),
                    'raw_data': message
                }
                barrages.append(barrage)

        except Exception as e:
            logger.error(f"弹幕消息解析错误: {e}")

        return barrages


# 使用示例
async def main():
    """测试B站适配器"""
    adapter = BilibiliAdapter()

    async def message_handler(message):
        """消息处理器"""
        barrages = await adapter.parse_danmaku_message(message)
        for barrage in barrages:
            logger.info(f"收到弹幕: {barrage['username']}: {barrage['content']}")

    # 连接到测试房间
    success = await adapter.connect_to_danmaku('123456', message_handler)
    if success:
        logger.info("连接成功，开始监听弹幕...")

        # 运行10分钟
        await asyncio.sleep(600)

        await adapter.disconnect()
    else:
        logger.error("连接失败")


if __name__ == '__main__':
    asyncio.run(main())