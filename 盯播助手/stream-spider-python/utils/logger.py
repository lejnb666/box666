# -*- coding: utf-8 -*-

"""
日志工具类

@author: exbox0403-cmd
@since: 2026/4/8
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

from config.settings import settings


def setup_logger(
    name: Optional[str] = None,
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径

    Returns:
        配置好的日志记录器
    """
    # 创建日志器
    logger_name = name or __name__
    logger = logging.getLogger(logger_name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 设置日志级别
    log_level = getattr(logging, (level or settings.logging.level).upper())
    logger.setLevel(log_level)

    # 创建格式化器
    formatter = logging.Formatter(settings.logging.format)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 创建文件处理器
    if log_file or settings.logging.file_path:
        log_path = log_file or settings.logging.file_path
        file_handler = create_file_handler(log_path, log_level, formatter)
        if file_handler:
            logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('pika').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

    logger.info(f"日志器 {logger_name} 初始化完成")
    return logger


def create_file_handler(
    log_file: str,
    level: int,
    formatter: logging.Formatter
) -> Optional[logging.Handler]:
    """
    创建文件处理器

    Args:
        log_file: 日志文件路径
        level: 日志级别
        formatter: 格式化器

    Returns:
        文件处理器或None
    """
    try:
        # 确保目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # 创建带轮转的文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=settings.logging.max_file_size,
            backupCount=settings.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        return file_handler

    except Exception as e:
        print(f"创建文件处理器失败: {e}")
        return None


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志器名称

    Returns:
        日志记录器
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    日志混入类
    """

    @property
    def logger(self) -> logging.Logger:
        """获取日志记录器"""
        if not hasattr(self, '_logger'):
            self._logger = setup_logger(self.__class__.__name__)
        return self._logger


def log_execution_time(func):
    """
    记录函数执行时间的装饰器
    """
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()
        logger.debug(f"开始执行函数: {func.__name__}")

        try:
            result = func(*args, **kwargs)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.debug(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.3f}秒")
            return result
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
            raise

    return wrapper


def setup_structured_logger(
    name: str,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置结构化日志记录器

    Args:
        name: 日志器名称
        log_file: 日志文件路径

    Returns:
        配置好的日志记录器
    """
    logger = setup_logger(name, log_file=log_file)

    # 添加JSON格式化器（如果可用）
    try:
        import json

        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': self.formatTime(record),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }

                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)

                if hasattr(record, 'extra'):
                    log_entry.update(record.extra)

                return json.dumps(log_entry, ensure_ascii=False)

        # 为文件处理器添加JSON格式化器
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setFormatter(JSONFormatter())

    except ImportError:
        pass  # JSON不可用，使用默认格式化器

    return logger


if __name__ == '__main__':
    # 测试日志配置
    logger = setup_logger('test_logger')

    logger.debug('这是一条调试信息')
    logger.info('这是一条信息')
    logger.warning('这是一条警告')
    logger.error('这是一条错误信息')

    try:
        raise ValueError('测试异常')
    except Exception as e:
        logger.exception('捕获到异常')