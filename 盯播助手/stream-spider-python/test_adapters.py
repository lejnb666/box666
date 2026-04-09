#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
平台适配器测试脚本

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import sys
from loguru import logger

from services.bilibili_adapter import BilibiliAdapter
from services.douyu_adapter import DouyuAdapter


class AdapterTester:
    """适配器测试类"""

    def __init__(self):
        self.bilibili_adapter = BilibiliAdapter()
        self.douyu_adapter = DouyuAdapter()

    async def test_bilibili_adapter(self, room_id: str = '123456'):
        """测试B站适配器"""
        logger.info(f"开始测试B站适配器，房间ID: {room_id}")

        try:
            # 测试房间信息获取
            room_info = await self.bilibili_adapter.get_room_info(room_id)
            if room_info:
                logger.info(f"✅ B站房间信息获取成功: {room_info['streamer_name']} - {room_info['title']}")
                logger.info(f"   直播状态: {'直播中' if room_info['is_live'] else '未直播'}")
                logger.info(f"   观看人数: {room_info['viewer_count']}")
            else:
                logger.warning("⚠️ B站房间信息获取失败")

            # 测试直播状态获取
            is_live = await self.bilibili_adapter.get_live_status(room_id)
            logger.info(f"✅ B站直播状态: {'直播中' if is_live else '未直播'}")

            # 测试弹幕服务器信息获取
            danmaku_info = await self.bilibili_adapter.get_danmaku_server_info(room_id)
            if danmaku_info:
                logger.info(f"✅ B站弹幕服务器信息获取成功")
                logger.info(f"   服务器数量: {len(danmaku_info.get('host_list', []))}")
            else:
                logger.warning("⚠️ B站弹幕服务器信息获取失败")

            return True

        except Exception as e:
            logger.error(f"❌ B站适配器测试失败: {e}")
            return False

    async def test_douyu_adapter(self, room_id: str = '288016'):
        """测试斗鱼适配器"""
        logger.info(f"开始测试斗鱼适配器，房间ID: {room_id}")

        try:
            # 测试房间信息获取
            room_info = await self.douyu_adapter.get_room_info(room_id)
            if room_info:
                logger.info(f"✅ 斗鱼房间信息获取成功: {room_info['streamer_name']} - {room_info['title']}")
                logger.info(f"   直播状态: {'直播中' if room_info['is_live'] else '未直播'}")
                logger.info(f"   观看人数: {room_info['viewer_count']}")
            else:
                logger.warning("⚠️ 斗鱼房间信息获取失败")

            # 测试直播状态获取
            is_live = await self.douyu_adapter.get_live_status(room_id)
            logger.info(f"✅ 斗鱼直播状态: {'直播中' if is_live else '未直播'}")

            # 测试弹幕服务器信息获取
            danmaku_info = await self.douyu_adapter.get_danmaku_server_info(room_id)
            if danmaku_info:
                logger.info(f"✅ 斗鱼弹幕服务器信息获取成功")
                logger.info(f"   服务器数量: {len(danmaku_info.get('servers', []))}")
            else:
                logger.warning("⚠️ 斗鱼弹幕服务器信息获取失败")

            return True

        except Exception as e:
            logger.error(f"❌ 斗鱼适配器测试失败: {e}")
            return False

    async def test_bilibili_websocket(self, room_id: str = '123456', duration: int = 60):
        """测试B站WebSocket连接"""
        logger.info(f"开始测试B站WebSocket连接，房间ID: {room_id}，持续时间: {duration}秒")

        message_count = 0
        error_count = 0

        async def message_handler(message):
            nonlocal message_count, error_count
            try:
                barrages = await self.bilibili_adapter.parse_danmaku_message(message)
                for barrage in barrages:
                    message_count += 1
                    if message_count <= 5:  # 只显示前5条消息
                        logger.info(f"B站弹幕: {barrage['username']}: {barrage['content']}")
            except Exception as e:
                error_count += 1
                logger.error(f"B站消息处理错误: {e}")

        try:
            # 连接到弹幕服务器
            success = await self.bilibili_adapter.connect_to_danmaku(room_id, message_handler)
            if not success:
                logger.error("❌ B站WebSocket连接失败")
                return False

            logger.info("✅ B站WebSocket连接成功")

            # 运行指定时间
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < duration:
                if not self.bilibili_adapter.is_connected():
                    logger.warning("⚠️ B站连接已断开")
                    break
                await asyncio.sleep(1)

            # 断开连接
            await self.bilibili_adapter.disconnect()

            logger.info(f"✅ B站WebSocket测试完成")
            logger.info(f"   接收消息数: {message_count}")
            logger.info(f"   错误数: {error_count}")

            return True

        except Exception as e:
            logger.error(f"❌ B站WebSocket测试失败: {e}")
            return False

    async def test_douyu_websocket(self, room_id: str = '288016', duration: int = 60):
        """测试斗鱼WebSocket连接"""
        logger.info(f"开始测试斗鱼WebSocket连接，房间ID: {room_id}，持续时间: {duration}秒")

        message_count = 0
        error_count = 0

        async def message_handler(message):
            nonlocal message_count, error_count
            try:
                barrages = await self.douyu_adapter.parse_danmaku_message(message)
                for barrage in barrages:
                    message_count += 1
                    if message_count <= 5:  # 只显示前5条消息
                        logger.info(f"斗鱼弹幕: {barrage['username']}: {barrage['content']}")
            except Exception as e:
                error_count += 1
                logger.error(f"斗鱼消息处理错误: {e}")

        try:
            # 连接到弹幕服务器
            success = await self.douyu_adapter.connect_to_danmaku(room_id, message_handler)
            if not success:
                logger.error("❌ 斗鱼WebSocket连接失败")
                return False

            logger.info("✅ 斗鱼WebSocket连接成功")

            # 运行指定时间
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < duration:
                if not self.douyu_adapter.is_connected():
                    logger.warning("⚠️ 斗鱼连接已断开")
                    break
                await asyncio.sleep(1)

            # 断开连接
            await self.douyu_adapter.disconnect()

            logger.info(f"✅ 斗鱼WebSocket测试完成")
            logger.info(f"   接收消息数: {message_count}")
            logger.info(f"   错误数: {error_count}")

            return True

        except Exception as e:
            logger.error(f"❌ 斗鱼WebSocket测试失败: {e}")
            return False

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始运行平台适配器测试...")

        test_results = {
            'bilibili_api': False,
            'douyu_api': False,
            'bilibili_websocket': False,
            'douyu_websocket': False
        }

        # 测试API接口
        test_results['bilibili_api'] = await self.test_bilibili_adapter()
        test_results['douyu_api'] = await self.test_douyu_adapter()

        # 询问是否进行WebSocket测试
        logger.info("\n" + "="*50)
        logger.info("API测试完成，是否进行WebSocket连接测试?")
        logger.info("注意: WebSocket测试会建立真实连接并持续一段时间")
        logger.info("="*50)

        choice = input("是否继续WebSocket测试? (y/n): ").lower().strip()
        if choice == 'y':
            # 测试WebSocket连接
            test_results['bilibili_websocket'] = await self.test_bilibili_websocket(duration=30)
            test_results['douyu_websocket'] = await self.test_douyu_websocket(duration=30)

        # 输出测试结果汇总
        self.print_test_summary(test_results)

        return test_results

    def print_test_summary(self, results: dict):
        """打印测试结果汇总"""
        logger.info("\n" + "="*60)
        logger.info("📊 平台适配器测试结果汇总")
        logger.info("="*60)

        passed = 0
        total = len(results)

        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1

        logger.info("="*60)
        logger.info(f"测试通过率: {passed}/{total} ({passed/total*100:.1f}%)")

        if passed == total:
            logger.info("🎉 所有测试通过！")
        else:
            logger.warning("⚠️  部分测试失败，请检查相关配置")


def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    logger.add("adapter_test.log", rotation="10 MB", level="DEBUG")

    tester = AdapterTester()

    try:
        asyncio.run(tester.run_all_tests())
    except KeyboardInterrupt:
        logger.info("\n🛑 测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试运行异常: {e}")


if __name__ == "__main__":
    main()