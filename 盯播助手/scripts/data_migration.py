#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
大数据迁移脚本 - 将MySQL中的弹幕数据迁移到MongoDB
支持增量迁移和数据一致性验证

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import mysql.connector
from pymongo import MongoClient
from pymongo.errors import BulkWriteError
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class DataMigrationService:
    """数据迁移服务"""

    def __init__(self, mysql_config: Dict[str, Any], mongo_config: Dict[str, Any]):
        self.mysql_config = mysql_config
        self.mongo_config = mongo_config

        # 初始化连接
        self.mysql_conn = None
        self.mongo_client = None
        self.mongo_db = None

        # 迁移统计
        self.stats = {
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'start_time': None,
            'end_time': None
        }

    def connect(self):
        """建立数据库连接"""
        try:
            # 连接MySQL
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            logger.info("MySQL连接成功")

            # 连接MongoDB
            self.mongo_client = MongoClient(
                host=self.mongo_config['host'],
                port=self.mongo_config['port'],
                username=self.mongo_config['username'],
                password=self.mongo_config['password'],
                authSource=self.mongo_config['auth_source']
            )
            self.mongo_db = self.mongo_client[self.mongo_config['database']]
            logger.info("MongoDB连接成功")

        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.mysql_conn:
            self.mysql_conn.close()
        if self.mongo_client:
            self.mongo_client.close()
        logger.info("数据库连接已关闭")

    def migrate_barrage_data(self, batch_size: int = 1000,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        迁移弹幕数据

        Args:
            batch_size: 批次大小
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            迁移统计信息
        """
        self.stats['start_time'] = datetime.now()
        logger.info(f"开始弹幕数据迁移，批次大小: {batch_size}")

        try:
            # 获取总记录数
            total_count = self._get_total_count(start_date, end_date)
            logger.info(f"需要迁移的总记录数: {total_count}")

            if total_count == 0:
                logger.info("没有需要迁移的数据")
                return self.stats

            # 分批迁移
            offset = 0
            while offset < total_count:
                batch_start_time = time.time()

                # 获取批次数据
                batch_data = self._fetch_batch_data(offset, batch_size, start_date, end_date)

                if not batch_data:
                    break

                # 转换并插入MongoDB
                success_count = self._insert_batch_to_mongo(batch_data)

                # 更新统计
                self.stats['total_processed'] += len(batch_data)
                self.stats['success_count'] += success_count
                self.stats['error_count'] += len(batch_data) - success_count

                # 计算进度
                progress = (self.stats['total_processed'] / total_count) * 100
                batch_time = time.time() - batch_start_time

                logger.info(
                    f"进度: {progress:.1f}% | "
                    f"已处理: {self.stats['total_processed']}/{total_count} | "
                    f"成功: {self.stats['success_count']} | "
                    f"失败: {self.stats['error_count']} | "
                    f"批次耗时: {batch_time:.2f}s"
                )

                offset += batch_size

                # 避免过快请求
                time.sleep(0.1)

            self.stats['end_time'] = datetime.now()
            total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

            logger.info(
                f"数据迁移完成 | "
                f"总耗时: {total_time:.2f}s | "
                f"总记录数: {self.stats['total_processed']} | "
                f"成功率: {(self.stats['success_count'] / self.stats['total_processed'] * 100):.2f}%"
            )

            return self.stats

        except Exception as e:
            logger.error(f"数据迁移失败: {e}")
            self.stats['end_time'] = datetime.now()
            return self.stats

    def _get_total_count(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> int:
        """获取需要迁移的总记录数"""
        cursor = self.mysql_conn.cursor()

        query = "SELECT COUNT(*) FROM barrage_data WHERE 1=1"
        params = []

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        cursor.close()

        return count

    def _fetch_batch_data(self, offset: int, batch_size: int,
                         start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """获取批次数据"""
        cursor = self.mysql_conn.cursor(dictionary=True)

        query = """
            SELECT
                id, streamer_config_id, platform, room_id, user_id, username,
                content, timestamp, created_at, type, user_level, medal_level,
                medal_name, medal_room, is_admin, is_vip, gift_name, gift_count, gift_price
            FROM barrage_data
            WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND timestamp <= %s"
            params.append(end_date)

        query += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([batch_size, offset])

        cursor.execute(query, params)
        data = cursor.fetchall()
        cursor.close()

        return data

    def _insert_batch_to_mongo(self, batch_data: List[Dict[str, Any]]) -> int:
        """将批次数据插入MongoDB"""
        try:
            # 转换数据格式
            documents = []
            for row in batch_data:
                document = self._convert_to_mongo_document(row)
                documents.append(document)

            # 批量插入
            if documents:
                result = self.mongo_db.barrage_data.insert_many(documents, ordered=False)
                return len(result.inserted_ids)

            return 0

        except BulkWriteError as bwe:
            logger.warning(f"批量写入错误，部分数据可能重复: {bwe.details}")
            return bwe.details.get('nInserted', 0)

        except Exception as e:
            logger.error(f"插入MongoDB失败: {e}")
            return 0

    def _convert_to_mongo_document(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """将MySQL行数据转换为MongoDB文档"""
        document = {
            'id': str(row['id']),
            'streamer_config_id': row['streamer_config_id'],
            'platform': row['platform'],
            'room_id': row['room_id'],
            'user_id': row['user_id'],
            'username': row['username'],
            'content': row['content'],
            'timestamp': row['timestamp'],
            'created_at': row['created_at'] or datetime.now(),
            'type': row['type'] or 'danmu'
        }

        # 添加元数据
        if row['user_level'] is not None:
            document['user_level'] = row['user_level']

        if row['medal_level'] is not None:
            document['medal_level'] = row['medal_level']

        if row['medal_name']:
            document['medal_name'] = row['medal_name']

        if row['medal_room']:
            document['medal_room'] = row['medal_room']

        if row['is_admin'] is not None:
            document['is_admin'] = bool(row['is_admin'])

        if row['is_vip'] is not None:
            document['is_vip'] = bool(row['is_vip'])

        # 添加礼物信息
        if row['gift_name']:
            document['gift_name'] = row['gift_name']
            document['gift_count'] = row['gift_count'] or 1
            document['gift_price'] = float(row['gift_price']) if row['gift_price'] else 0.0

        return document

    def verify_data_consistency(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        验证数据一致性

        Returns:
            一致性检查结果
        """
        logger.info("开始验证数据一致性")

        try:
            # 获取MySQL数据量
            mysql_count = self._get_total_count(start_date, end_date)

            # 构建MongoDB查询条件
            mongo_query = {}
            if start_date or end_date:
                mongo_query['timestamp'] = {}
                if start_date:
                    mongo_query['timestamp']['$gte'] = start_date
                if end_date:
                    mongo_query['timestamp']['$lte'] = end_date

            # 获取MongoDB数据量
            mongo_count = self.mongo_db.barrage_data.count_documents(mongo_query)

            # 计算差异
            difference = abs(mysql_count - mongo_count)
            tolerance = max(1, mysql_count * 0.01)  # 1%容错率

            is_consistent = difference <= tolerance

            result = {
                'is_consistent': is_consistent,
                'mysql_count': mysql_count,
                'mongo_count': mongo_count,
                'difference': difference,
                'tolerance': tolerance,
                'consistency_rate': (min(mysql_count, mongo_count) / max(mysql_count, mongo_count) * 100) if max(mysql_count, mongo_count) > 0 else 100
            }

            logger.info(
                f"数据一致性验证完成 | "
                f"MySQL: {mysql_count} | "
                f"MongoDB: {mongo_count} | "
                f"差异: {difference} | "
                f"一致性: {'✅' if is_consistent else '❌'}"
            )

            return result

        except Exception as e:
            logger.error(f"数据一致性验证失败: {e}")
            return {'error': str(e)}

    def cleanup_mysql_data(self, before_date: datetime) -> int:
        """
        清理MySQL中已迁移的数据

        Args:
            before_date: 清理此日期之前的数据

        Returns:
            清理的记录数
        """
        logger.info(f"开始清理 {before_date} 之前的MySQL数据")

        try:
            cursor = self.mysql_conn.cursor()

            # 先统计要删除的记录数
            count_query = "SELECT COUNT(*) FROM barrage_data WHERE timestamp < %s"
            cursor.execute(count_query, (before_date,))
            delete_count = cursor.fetchone()[0]

            if delete_count == 0:
                logger.info("没有需要清理的数据")
                return 0

            # 执行删除
            delete_query = "DELETE FROM barrage_data WHERE timestamp < %s"
            cursor.execute(delete_query, (before_date,))

            self.mysql_conn.commit()
            cursor.close()

            logger.info(f"已清理 {delete_count} 条MySQL记录")
            return delete_count

        except Exception as e:
            logger.error(f"清理MySQL数据失败: {e}")
            self.mysql_conn.rollback()
            return 0

def main():
    """主函数"""
    # 数据库配置
    mysql_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'database': 'stream_monitor',
        'user': 'stream_user',
        'password': 'stream_password',
        'charset': 'utf8mb4'
    }

    mongo_config = {
        'host': '127.0.0.1',
        'port': 27017,
        'username': 'mongo_admin',
        'password': 'mongo_password',
        'database': 'stream_monitor',
        'auth_source': 'admin'
    }

    # 创建迁移服务
    migrator = DataMigrationService(mysql_config, mongo_config)

    try:
        # 连接数据库
        migrator.connect()

        # 执行数据迁移
        print("=" * 60)
        print("开始数据迁移")
        print("=" * 60)

        # 迁移最近30天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        stats = migrator.migrate_barrage_data(
            batch_size=2000,
            start_date=start_date,
            end_date=end_date
        )

        print(f"\n迁移完成:")
        print(f"总处理: {stats['total_processed']} 条")
        print(f"成功: {stats['success_count']} 条")
        print(f"失败: {stats['error_count']} 条")
        print(f"耗时: {(stats['end_time'] - stats['start_time']).total_seconds():.2f} 秒")

        # 验证数据一致性
        print("\n" + "=" * 60)
        print("验证数据一致性")
        print("=" * 60)

        consistency_result = migrator.verify_data_consistency(start_date, end_date)

        if consistency_result.get('is_consistent'):
            print("✅ 数据一致性验证通过")
            print(f"一致性率: {consistency_result['consistency_rate']:.2f}%")
        else:
            print("❌ 数据一致性验证失败")
            print(f"MySQL记录数: {consistency_result['mysql_count']}")
            print(f"MongoDB记录数: {consistency_result['mongo_count']}")
            print(f"差异: {consistency_result['difference']}")

        # 询问是否清理MySQL数据
        print("\n" + "=" * 60)
        response = input("是否清理MySQL中已迁移的数据？(y/N): ")

        if response.lower() == 'y':
            cleanup_date = end_date - timedelta(days=7)  # 清理7天前的数据
            cleaned_count = migrator.cleanup_mysql_data(cleanup_date)
            print(f"已清理 {cleaned_count} 条MySQL记录")

        print("\n数据迁移任务完成！")

    except Exception as e:
        logger.error(f"迁移任务失败: {e}")
        sys.exit(1)

    finally:
        migrator.close()

if __name__ == '__main__':
    main()