#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
盯播助手Python爬虫和AI服务主入口

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import logging
import sys
import threading
import time  # 添加time模块导入
from datetime import datetime
from typing import Dict, List, Optional

import schedule
from flask import Flask, jsonify, request
from flask_cors import CORS

from config.settings import Settings
from services.crawler_service import CrawlerService
from services.ai_service import AIService
from services.websocket_service import WebSocketService
from services.rabbitmq_service import RabbitMQService
from utils.logger import setup_logger
from utils.database import DatabaseManager

# 全局变量
app = Flask(__name__)
CORS(app)
crawler_service: Optional[CrawlerService] = None
ai_service: Optional[AIService] = None
websocket_service: Optional[WebSocketService] = None
rabbitmq_service: Optional[RabbitMQService] = None
db_manager: Optional[DatabaseManager] = None


def initialize_services():
    """初始化所有服务"""
    global crawler_service, ai_service, websocket_service, rabbitmq_service, db_manager

    try:
        # 初始化日志
        setup_logger()
        logger = logging.getLogger(__name__)
        logger.info("开始初始化盯播助手Python服务...")

        # 加载配置
        settings = Settings()
        logger.info("配置加载完成")

        # 初始化数据库
        db_manager = DatabaseManager(settings)
        db_manager.initialize()
        logger.info("数据库初始化完成")

        # 初始化RabbitMQ服务
        rabbitmq_service = RabbitMQService(settings)
        rabbitmq_service.connect()
        logger.info("RabbitMQ服务初始化完成")

        # 初始化AI服务
        ai_service = AIService(settings)
        ai_service.initialize()
        logger.info("AI服务初始化完成")

        # 初始化爬虫服务
        crawler_service = CrawlerService(settings, rabbitmq_service)
        logger.info("爬虫服务初始化完成")

        # 初始化WebSocket服务
        websocket_service = WebSocketService(settings, ai_service, rabbitmq_service)
        logger.info("WebSocket服务初始化完成")

        logger.info("所有服务初始化完成")

    except Exception as e:
        logging.error(f"服务初始化失败: {e}")
        sys.exit(1)


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'crawler': crawler_service is not None and crawler_service.is_running(),
                'ai': ai_service is not None and ai_service.is_available(),
                'websocket': websocket_service is not None and websocket_service.is_connected(),
                'rabbitmq': rabbitmq_service is not None and rabbitmq_service.is_connected(),
                'database': db_manager is not None and db_manager.is_connected()
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/v1/crawler/start', methods=['POST'])
def start_crawler():
    """启动爬虫"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        room_id = data.get('room_id')

        if not platform or not room_id:
            return jsonify({'error': '缺少必要参数'}), 400

        if crawler_service:
            success = crawler_service.start_crawling(platform, room_id)
            if success:
                return jsonify({'message': f'开始监控 {platform} 平台房间 {room_id}'}), 200
            else:
                return jsonify({'error': '启动爬虫失败'}), 500
        else:
            return jsonify({'error': '爬虫服务未初始化'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/crawler/stop', methods=['POST'])
def stop_crawler():
    """停止爬虫"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        room_id = data.get('room_id')

        if crawler_service:
            success = crawler_service.stop_crawling(platform, room_id)
            if success:
                return jsonify({'message': '停止爬虫成功'}), 200
            else:
                return jsonify({'error': '停止爬虫失败'}), 500
        else:
            return jsonify({'error': '爬虫服务未初始化'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/crawler/status', methods=['GET'])
def crawler_status():
    """获取爬虫状态"""
    try:
        if crawler_service:
            status = crawler_service.get_status()
            return jsonify(status), 200
        else:
            return jsonify({'error': '爬虫服务未初始化'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/ai/analyze', methods=['POST'])
def ai_analyze():
    """AI分析接口"""
    try:
        data = request.get_json()
        barrage_list = data.get('barrages', [])
        analysis_type = data.get('type', 'general')

        if not barrage_list:
            return jsonify({'error': '弹幕列表不能为空'}), 400

        if ai_service:
            # 使用asyncio.run包装异步调用
            result = asyncio.run(ai_service.analyze_barrages(barrage_list, analysis_type))
            return jsonify(result), 200
        else:
            return jsonify({'error': 'AI服务未初始化'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/websocket/connect', methods=['POST'])
def connect_websocket():
    """连接WebSocket"""
    try:
        data = request.get_json()
        platform = data.get('platform')
        room_id = data.get('room_id')

        if not platform or not room_id:
            return jsonify({'error': '缺少必要参数'}), 400

        if websocket_service:
            success = websocket_service.connect_to_room(platform, room_id)
            if success:
                return jsonify({'message': f'成功连接到 {platform} 房间 {room_id}'}), 200
            else:
                return jsonify({'error': 'WebSocket连接失败'}), 500
        else:
            return jsonify({'error': 'WebSocket服务未初始化'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_scheduler():
    """运行定时任务"""
    logger = logging.getLogger(__name__)
    logger.info("启动定时任务调度器")

    # 每分钟检查一次直播状态
    schedule.every(1).minutes.do(crawler_service.check_live_status if crawler_service else None)

    # 每5分钟清理一次缓存
    schedule.every(5).minutes.do(cleanup_cache)

    # 每30分钟检查一次服务健康状态
    schedule.every(30).minutes.do(check_service_health)

    while True:
        schedule.run_pending()
        time.sleep(1)  # 修复：使用time.sleep替代asyncio.sleep


def cleanup_cache():
    """清理缓存"""
    try:
        logger = logging.getLogger(__name__)
        # 清理过期的缓存数据
        if db_manager:
            db_manager.cleanup_expired_data()
        logger.info("缓存清理完成")
    except Exception as e:
        logging.error(f"缓存清理失败: {e}")


def check_service_health():
    """检查服务健康状态"""
    try:
        logger = logging.getLogger(__name__)

        # 检查各服务状态
        services_status = {
            'crawler': crawler_service.is_running() if crawler_service else False,
            'ai': ai_service.is_available() if ai_service else False,
            'websocket': websocket_service.is_connected() if websocket_service else False,
            'rabbitmq': rabbitmq_service.is_connected() if rabbitmq_service else False,
            'database': db_manager.is_connected() if db_manager else False
        }

        # 重启失败的服务
        for service_name, is_healthy in services_status.items():
            if not is_healthy:
                logger.warning(f"{service_name} 服务异常，尝试重启...")
                restart_service(service_name)

        logger.info(f"服务健康状态检查完成: {services_status}")

    except Exception as e:
        logging.error(f"服务健康检查失败: {e}")


def restart_service(service_name: str):
    """重启指定服务"""
    try:
        if service_name == 'rabbitmq' and rabbitmq_service:
            rabbitmq_service.reconnect()
        elif service_name == 'ai' and ai_service:
            ai_service.reinitialize()
        elif service_name == 'websocket' and websocket_service:
            websocket_service.reconnect()
        elif service_name == 'database' and db_manager:
            db_manager.reconnect()
    except Exception as e:
        logging.error(f"重启 {service_name} 服务失败: {e}")


def start_background_tasks():
    """启动后台任务"""
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # 启动爬虫监控
    if crawler_service:
        crawler_thread = threading.Thread(target=crawler_service.start_monitoring, daemon=True)
        crawler_thread.start()

    # 启动WebSocket监听
    if websocket_service:
        websocket_thread = threading.Thread(target=run_websocket_service, daemon=True)
        websocket_thread.start()


def run_websocket_service():
    """WebSocket服务的同步包装函数，用于在新线程中运行"""
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 启动WebSocket监听
        websocket_service.start_listening()

    except Exception as e:
        logging.error(f"WebSocket服务线程运行失败: {e}")
    finally:
        try:
            loop.close()
        except:
            pass


def main():
    """主函数"""
    try:
        # 初始化服务
        initialize_services()

        # 启动后台任务
        start_background_tasks()

        # 启动Flask应用
        logger = logging.getLogger(__name__)
        logger.info("盯播助手Python服务启动完成")
        logger.info("Flask服务监听端口: 5000")

        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False
        )

    except Exception as e:
        logging.error(f"服务启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()