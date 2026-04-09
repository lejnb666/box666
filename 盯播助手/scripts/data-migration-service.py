#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移服务 - 从MongoDB迁移数据到HDFS
用于大数据架构演进的数据抽取和迁移
"""

import os
import sys
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pymongo import MongoClient
from hdfs import InsecureClient
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pv
from typing import Dict, List, Any, Optional
import schedule
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataMigrationService:
    """数据迁移服务类"""

    def __init__(self, config_path: str = None):
        """初始化服务"""
        self.config = self._load_config(config_path)
        self.mongo_client = None
        self.hdfs_client = None
        self._init_connections()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "mongodb": {
                "host": "localhost",
                "port": 27017,
                "database": "stream_monitor",
                "username": "mongo_admin",
                "password": "mongo_password"
            },
            "hdfs": {
                "host": "localhost",
                "port": 9870,
                "user": "hadoop"
            },
            "batch_size": 10000,
            "max_workers": 4
        }

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                # 合并配置
                for key, value in custom_config.items():
                    if isinstance(value, dict) and key in default_config:
                        default_config[key].update(value)
                    else:
                        default_config[key] = value

        return default_config

    def _init_connections(self):
        """初始化数据库连接"""
        try:
            # MongoDB连接
            mongo_config = self.config['mongodb']
            self.mongo_client = MongoClient(
                host=mongo_config['host'],
                port=mongo_config['port'],
                username=mongo_config['username'],
                password=mongo_config['password'],
                authSource=mongo_config['database']
            )
            self.db = self.mongo_client[mongo_config['database']]

            # HDFS连接
            hdfs_config = self.config['hdfs']
            self.hdfs_client = InsecureClient(
                f"http://{hdfs_config['host']}:{hdfs_config['port']}",
                user=hdfs_config['user']
            )

            logger.info("数据库连接初始化成功")

        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    def extract_daily_barrage_data(self, target_date: datetime) -> Optional[str]:
        """抽取指定日期的弹幕数据到HDFS"""
        try:
            start_time = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)

            logger.info(f"开始抽取 {start_time.strftime('%Y-%m-%d')} 的弹幕数据")

            # 构建查询条件
            query = {
                "timestamp": {
                    "$gte": start_time,
                    "$lt": end_time
                }
            }

            # 分批处理数据
            batch_size = self.config['batch_size']
            total_processed = 0

            # 创建HDFS目录结构
            hdfs_base_path = f"/barrage_data/{target_date.strftime('%Y/%m/%d')}"
            self._ensure_hdfs_directory(hdfs_base_path)

            # 临时文件用于存储批次数据
            temp_files = []

            # 使用游标分批读取MongoDB数据
            cursor = self.db.barrage.find(query).batch_size(batch_size)
            batch_data = []

            for doc in cursor:
                # 转换数据格式
                processed_doc = self._transform_barrage_doc(doc)
                batch_data.append(processed_doc)

                if len(batch_data) >= batch_size:
                    # 处理批次数据
                    temp_file = self._process_batch(batch_data, target_date, len(temp_files))
                    temp_files.append(temp_file)
                    total_processed += len(batch_data)
                    logger.info(f"已处理 {total_processed} 条记录")
                    batch_data = []

            # 处理剩余的批次
            if batch_data:
                temp_file = self._process_batch(batch_data, target_date, len(temp_files))
                temp_files.append(temp_file)
                total_processed += len(batch_data)

            # 合并所有批次文件
            final_file_path = f"{hdfs_base_path}/barrage.parquet"
            self._merge_parquet_files(temp_files, final_file_path)

            # 清理临时文件
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass

            logger.info(f"数据抽取完成，共处理 {total_processed} 条记录，保存到 {final_file_path}")
            return final_file_path

        except Exception as e:
            logger.error(f"数据抽取失败: {e}")
            raise

    def _transform_barrage_doc(self, doc: Dict) -> Dict:
        """转换MongoDB文档格式"""
        return {
            '_id': str(doc.get('_id', '')),
            'streamer_id': doc.get('streamer_id', ''),
            'streamer_name': doc.get('streamer_name', ''),
            'user_id': doc.get('user_id', ''),
            'user_name': doc.get('user_name', ''),
            'content': doc.get('content', ''),
            'timestamp': doc.get('timestamp'),
            'barrage_type': doc.get('barrage_type', 'normal'),
            'gift_value': float(doc.get('gift_value', 0)),
            'platform': doc.get('platform', ''),
            'room_id': doc.get('room_id', ''),
            'user_level': int(doc.get('user_level', 0)),
            'content_length': len(doc.get('content', ''))
        }

    def _process_batch(self, batch_data: List[Dict], target_date: datetime, batch_index: int) -> str:
        """处理批次数据"""
        # 转换为DataFrame
        df = pd.DataFrame(batch_data)

        # 添加分区字段
        df['year'] = target_date.year
        df['month'] = target_date.month
        df['day'] = target_date.day

        # 转换为PyArrow Table
        table = pa.Table.from_pandas(df)

        # 保存临时文件
        temp_file = f"temp_barrage_batch_{batch_index}_{int(time.time())}.parquet"
        pq.write_table(table, temp_file, compression='SNAPPY')

        return temp_file

    def _merge_parquet_files(self, temp_files: List[str], final_path: str):
        """合并Parquet文件"""
        tables = []

        for temp_file in temp_files:
            table = pq.read_table(temp_file)
            tables.append(table)

        # 合并所有表
        merged_table = pa.concat_tables(tables)

        # 上传到HDFS
        with self.hdfs_client.write(final_path, overwrite=True) as writer:
            pq.write_table(merged_table, writer, compression='SNAPPY')

    def _ensure_hdfs_directory(self, hdfs_path: str):
        """确保HDFS目录存在"""
        try:
            # 分解路径并逐级创建目录
            path_parts = hdfs_path.strip('/').split('/')
            current_path = ''

            for part in path_parts:
                current_path += f'/{part}'
                try:
                    self.hdfs_client.status(current_path)
                except:
                    self.hdfs_client.makedirs(current_path)

        except Exception as e:
            logger.error(f"创建HDFS目录失败 {hdfs_path}: {e}")
            raise

    def generate_hive_ddl(self, database_name: str = "stream_analysis") -> str:
        """生成Hive DDL语句"""
        ddl = f"""
-- 创建数据库
CREATE DATABASE IF NOT EXISTS {database_name};
USE {database_name};

-- 创建弹幕数据外部表
CREATE EXTERNAL TABLE IF NOT EXISTS barrage_data (
    _id STRING,
    streamer_id STRING,
    streamer_name STRING,
    user_id STRING,
    user_name STRING,
    content STRING,
    timestamp TIMESTAMP,
    barrage_type STRING,
    gift_value DOUBLE,
    platform STRING,
    room_id STRING,
    user_level INT,
    content_length INT
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 'hdfs://namenode:9000/barrage_data/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY',
    'parquet.enable.dictionary'='true'
);

-- 创建分区发现表（用于自动发现新分区）
MSCK REPAIR TABLE barrage_data;

-- 创建热词分析视图
CREATE OR REPLACE VIEW hot_words_daily AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    word,
    COUNT(*) as word_count,
    ROW_NUMBER() OVER (PARTITION BY streamer_id, year, month, day ORDER BY COUNT(*) DESC) as rank
FROM (
    SELECT
        streamer_id,
        streamer_name,
        year, month, day,
        EXPLODE(SPLIT(LOWER(content), ' ')) as word
    FROM barrage_data
    WHERE LENGTH(TRIM(content)) > 0
) words
WHERE LENGTH(word) > 1
  AND word NOT IN ('的', '了', '是', '我', '你', '在', '有', '不', '这', '就', '都', '也', '和', '要', '会', '能', '可以', '很', '好', '太', '真', '啊', '哦', '嗯')
GROUP BY streamer_id, streamer_name, year, month, day, word;

-- 创建观众活跃度热力图视图
CREATE OR REPLACE VIEW viewer_activity_heatmap AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    HOUR(timestamp) as hour,
    COUNT(*) as barrage_count,
    COUNT(DISTINCT user_id) as active_users,
    AVG(content_length) as avg_content_length,
    SUM(CASE WHEN gift_value > 0 THEN 1 ELSE 0 END) as gift_count
FROM barrage_data
GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp);

-- 创建情感分析视图
CREATE OR REPLACE VIEW sentiment_trend AS
SELECT
    streamer_id,
    streamer_name,
    year, month, day,
    HOUR(timestamp) as hour,
    sentiment_type,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY streamer_id, year, month, day, HOUR(timestamp)) as percentage
FROM (
    SELECT
        *,
        CASE
            WHEN content LIKE '%好%' OR content LIKE '%棒%' OR content LIKE '%赞%' OR content LIKE '%666%' OR content LIKE '%厉害%' THEN 'positive'
            WHEN content LIKE '%差%' OR content LIKE '%烂%' OR content LIKE '%垃圾%' OR content LIKE '%无语%' OR content LIKE '%失望%' THEN 'negative'
            ELSE 'neutral'
        END as sentiment_type
    FROM barrage_data
) with_sentiment
GROUP BY streamer_id, streamer_name, year, month, day, HOUR(timestamp), sentiment_type
ORDER BY hour, sentiment_type;
"""
        return ddl

    def schedule_daily_migration(self):
        """调度每日数据迁移任务"""
        def job():
            try:
                # 迁移昨天的数据
                yesterday = datetime.now() - timedelta(days=1)
                self.extract_daily_barrage_data(yesterday)

                # 生成Hive分区
                self._add_hive_partition(yesterday)

                logger.info(f"每日数据迁移任务完成: {yesterday.strftime('%Y-%m-%d')}")

            except Exception as e:
                logger.error(f"每日数据迁移任务失败: {e}")

        # 每天凌晨2点执行
        schedule.every().day.at("02:00").do(job)

        logger.info("每日数据迁移调度已启动")

        while True:
            schedule.run_pending()
            time.sleep(60)

    def _add_hive_partition(self, target_date: datetime):
        """添加Hive分区（需要通过HiveServer2执行）"""
        # 这里需要实现Hive连接和SQL执行
        # 可以通过pyhive库连接HiveServer2
        pass

    def run_migration_range(self, start_date: str, end_date: str):
        """运行指定日期范围的数据迁移"""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')

            current_date = start
            while current_date <= end:
                logger.info(f"开始迁移 {current_date.strftime('%Y-%m-%d')} 的数据")
                self.extract_daily_barrage_data(current_date)
                current_date += timedelta(days=1)

            logger.info("数据迁移范围任务完成")

        except Exception as e:
            logger.error(f"数据迁移范围任务失败: {e}")
            raise

    def close(self):
        """关闭连接"""
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("连接已关闭")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据迁移服务')
    parser.add_argument('--config', type=str, help='配置文件路径')
    parser.add_argument('--action', choices=['daily', 'range', 'ddl'], required=True, help='执行动作')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--database', type=str, default='stream_analysis', help='Hive数据库名称')

    args = parser.parse_args()

    try:
        service = DataMigrationService(args.config)

        if args.action == 'daily':
            # 执行单日迁移（昨天）
            yesterday = datetime.now() - timedelta(days=1)
            service.extract_daily_barrage_data(yesterday)

        elif args.action == 'range':
            # 执行日期范围迁移
            if not args.start_date or not args.end_date:
                print("范围迁移需要指定 --start-date 和 --end-date")
                return
            service.run_migration_range(args.start_date, args.end_date)

        elif args.action == 'ddl':
            # 生成Hive DDL
            ddl = service.generate_hive_ddl(args.database)
            print(ddl)

            # 保存到文件
            with open(f'hive_ddl_{args.database}.sql', 'w', encoding='utf-8') as f:
                f.write(ddl)
            print(f"\nDDL已保存到 hive_ddl_{args.database}.sql")

        service.close()

    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()