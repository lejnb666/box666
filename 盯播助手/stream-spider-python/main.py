#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
盯播助手Python爬虫和AI服务主入口
架构修复版：基于 Background Event Loop 模式解决多线程异步上下文冲突

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import logging
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import TimeoutError

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

app = Flask(__name__)
CORS(app)

# 全局服务变量
crawler_service: Optional[CrawlerService] = None
ai_service: Optional[AIService] = None
websocket_service: Optional[WebSocketService] = None
rabbitmq_service: Optional[RabbitMQService] = None
db_manager: Optional[DatabaseManager] = None

# 🚨 核心修复1：创建一个全局的后台事件循环，所有异步操作共享此 Loop
bg_loop = asyncio.new_event_loop()

def start_background_loop(loop: asyncio.AbstractEventLoop):
    """在一个独立的守护线程中永远运行这个事件循环"""
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except Exception as e:
        logging.error(f"后台事件循环崩溃: {e}\n{traceback.format_exc()}")

def run_async_safe(coro, timeout=10):
    """
    🚨 核心修复2：Flask 路由中的同步代码安全调用异步代码的桥梁
    将协程提交到 bg_loop 中执行，并等待结果
    """
    future = asyncio.run_coroutine_threadsafe(coro, bg_loop)
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        raise Exception("异步任务执行超时")
    except Exception as e:
        raise e

async def async_initialize_services():
    """在正确的事件循环中初始化服务，确保 aiohttp session 绑定到 bg_loop"""
    global crawler_service, ai_service, websocket_service, rabbitmq_service, db_manager
    logger = logging.getLogger(__name__)
    
    settings = Settings()
    
    db_manager = DatabaseManager(settings)
    db_manager.initialize()
    
    rabbitmq_service = RabbitMQService(settings)
    rabbitmq_service.connect()
    
    ai_service = AIService(settings)
    # 假设 AI Service 中使用了 aiohttp，必须在 async 环境下初始化
    if hasattr(ai_service, 'initialize_async'):
        await ai_service.initialize_async()
    else:
        ai_service.initialize()
        
    crawler_service = CrawlerService(settings, rabbitmq_service)
    websocket_service = WebSocketService(settings, ai_service, rabbitmq_service)
    
    logger.info("所有服务在后台事件循环中初始化完成")

def initialize_system():
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.info("开始初始化系统...")

    # 1. 启动后台事件循环线程
    t = threading.Thread(target=start_background_loop, args=(bg_loop,), daemon=True)
    t.start()

    # 2. 将初始化任务提交到后台事件循环
    future = asyncio.run_coroutine_threadsafe(async_initialize_services(), bg_loop)
    try:
        future.result(timeout=15)
    except Exception as e:
        logger.error(f"系统初始化失败: {e}\n{traceback.format_exc()}")
        sys.exit(1)


# ================== Flask 路由 (同步桥接异步) ==================

@app.route('/health', methods=['GET'])
def health_check():
    try:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'crawler': crawler_service is not None and crawler_service.is_running(),
                'ai': ai_service is not None and ai_service.is_available(),
                'websocket': websocket_service is not None and websocket_service.is_connected()
            }
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/v1/crawler/start', methods=['POST'])
def start_crawler():
    try:
        data = request.get_json()
        platform, room_id = data.get('platform'), data.get('room_id')
        if not platform or not room_id: return jsonify({'error': '缺少参数'}), 400
        
        if crawler_service:
            success = crawler_service.start_crawling(platform, room_id)
            return jsonify({'msg': 'Started'}) if success else jsonify({'error': 'Failed'}), 200 if success else 500
        return jsonify({'error': '未初始化'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/ai/analyze', methods=['POST'])
def ai_analyze():
    """AI 分析接口：通过 run_async_safe 桥接，防止事件循环冲突"""
    try:
        data = request.get_json()
        barrage_list = data.get('barrages', [])
        analysis_type = data.get('type', 'general')

        if not barrage_list:
            return jsonify({'error': '弹幕列表不能为空'}), 400

        if ai_service:
            # 🚨 提交到后台 bg_loop 执行，完美解决 Flask 与 aiohttp 的冲突
            result = run_async_safe(ai_service.analyze_barrages(barrage_list, analysis_type), timeout=30)
            return jsonify(result), 200
        return jsonify({'error': 'AI服务未初始化'}), 500

    except Exception as e:
        logging.error(f"AI分析请求报错: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ================== 后台调度与守护任务 ==================

def safe_check_live_status():
    if crawler_service:
        crawler_service.check_live_status()

def run_scheduler():
    logger = logging.getLogger(__name__)
    schedule.every(1).minutes.do(safe_check_live_status)
    
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            logger.error(f"定时器调度异常: {e}\n{traceback.format_exc()}")
        time.sleep(1)

def start_background_tasks():
    # 定时器线程
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # 🚨 将长连接监听也提交给 bg_loop，而不是新开事件循环
    if websocket_service:
        asyncio.run_coroutine_threadsafe(websocket_service.start_listening(), bg_loop)
    if crawler_service:
        threading.Thread(target=crawler_service.start_monitoring, daemon=True).start()

def main():
    try:
        initialize_system()
        start_background_tasks()
        
        logging.getLogger(__name__).info("盯播助手 Python 服务启动完成 (Port: 5000)")
        
        # 启动同步 Flask
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

    except Exception as e:
        logging.error(f"Flask 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
