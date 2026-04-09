#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hadoop离线分析作业 - 对海量弹幕数据进行T+1分析
生成热词词云、情感分析曲线、用户行为分析等

@author: exbox0403-cmd
@since: 2026/4/8
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any

import pandas as pd
from pymongo import MongoClient
from hdfs import InsecureClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HadoopAnalyticsService:
    """Hadoop离线分析服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hdfs_client = None
        self.mongo_client = None

        # HDFS路径配置
        self.hdfs_paths = {
            'input': '/stream_monitor/input/barrage_data',
            'output': '/stream_monitor/output',
            'scripts': '/stream_monitor/scripts',
            'temp': '/stream_monitor/temp'
        }

        # MapReduce作业配置
        self.mr_jobs = {
            'hot_words': {
                'mapper': 'hot_words_mapper.py',
                'reducer': 'hot_words_reducer.py',
                'output_dir': 'hot_words'
            },
            'sentiment_analysis': {
                'mapper': 'sentiment_mapper.py',
                'reducer': 'sentiment_reducer.py',
                'output_dir': 'sentiment'
            },
            'user_behavior': {
                'mapper': 'user_behavior_mapper.py',
                'reducer': 'user_behavior_reducer.py',
                'output_dir': 'user_behavior'
            },
            'time_distribution': {
                'mapper': 'time_distribution_mapper.py',
                'reducer': 'time_distribution_reducer.py',
                'output_dir': 'time_distribution'
            }
        }

    def initialize(self):
        """初始化服务"""
        try:
            # 连接HDFS
            self.hdfs_client = InsecureClient(
                self.config['hdfs']['url'],
                user=self.config['hdfs']['user']
            )
            logger.info("HDFS连接成功")

            # 连接MongoDB
            self.mongo_client = MongoClient(
                host=self.config['mongodb']['host'],
                port=self.config['mongodb']['port'],
                username=self.config['mongodb']['username'],
                password=self.config['mongodb']['password']
            )
            logger.info("MongoDB连接成功")

            # 创建HDFS目录
            self._create_hdfs_directories()

        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            raise

    def _create_hdfs_directories(self):
        """创建必要的HDFS目录"""
        for path_name, path in self.hdfs_paths.items():
            try:
                self.hdfs_client.makedirs(path)
                logger.info(f"创建HDFS目录: {path}")
            except Exception as e:
                logger.warning(f"创建HDFS目录失败 {path}: {e}")

    def export_data_to_hdfs(self, date: datetime) -> str:
        """
        将MongoDB数据导出到HDFS

        Args:
            date: 分析日期

        Returns:
            HDFS文件路径
        """
        logger.info(f"开始导出 {date.date()} 的数据到HDFS")

        try:
            # 计算时间范围
            start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)

            # 从MongoDB查询数据
            db = self.mongo_client[self.config['mongodb']['database']]
            collection = db['barrage_data']

            query = {
                'timestamp': {
                    '$gte': start_time,
                    '$lt': end_time
                }
            }

            cursor = collection.find(query, {'_id': 0})

            # 临时文件路径
            temp_file = f"/tmp/barrage_data_{date.strftime('%Y%m%d')}.json"

            # 写入临时文件
            with open(temp_file, 'w', encoding='utf-8') as f:
                for doc in cursor:
                    f.write(json.dumps(doc, ensure_ascii=False) + '\n')

            logger.info(f"已导出数据到临时文件: {temp_file}")

            # 上传到HDFS
            hdfs_file_path = f"{self.hdfs_paths['input']}/barrage_data_{date.strftime('%Y%m%d')}.json"
            self.hdfs_client.upload(hdfs_file_path, temp_file, overwrite=True)

            # 清理临时文件
            os.remove(temp_file)

            logger.info(f"数据已上传到HDFS: {hdfs_file_path}")
            return hdfs_file_path

        except Exception as e:
            logger.error(f"数据导出到HDFS失败: {e}")
            raise

    def upload_mapreduce_scripts(self):
        """上传MapReduce脚本到HDFS"""
        logger.info("开始上传MapReduce脚本到HDFS")

        try:
            scripts_dir = "hadoop_scripts"
            os.makedirs(scripts_dir, exist_ok=True)

            # 创建热词分析脚本
            self._create_hot_words_scripts(scripts_dir)

            # 创建情感分析脚本
            self._create_sentiment_scripts(scripts_dir)

            # 创建用户行为分析脚本
            self._create_user_behavior_scripts(scripts_dir)

            # 创建时间分布分析脚本
            self._create_time_distribution_scripts(scripts_dir)

            # 上传所有脚本到HDFS
            for script_file in os.listdir(scripts_dir):
                local_path = os.path.join(scripts_dir, script_file)
                hdfs_path = f"{self.hdfs_paths['scripts']}/{script_file}"

                with open(local_path, 'r', encoding='utf-8') as f:
                    self.hdfs_client.write(hdfs_path, f, overwrite=True)

                logger.info(f"上传脚本: {script_file}")

        except Exception as e:
            logger.error(f"上传MapReduce脚本失败: {e}")
            raise

    def run_hot_words_analysis(self, input_path: str, date: datetime) -> str:
        """
        运行热词分析MapReduce作业

        Args:
            input_path: 输入文件路径
            date: 分析日期

        Returns:
            输出路径
        """
        logger.info(f"开始热词分析作业")

        try:
            output_path = f"{self.hdfs_paths['output']}/hot_words/{date.strftime('%Y%m%d')}"

            # 构建Hadoop命令
            cmd = [
                'hadoop', 'jar', self.config['hadoop']['streaming_jar'],
                '-file', f"{self.hdfs_paths['scripts']}/hot_words_mapper.py",
                '-mapper', 'python hot_words_mapper.py',
                '-file', f"{self.hdfs_paths['scripts']}/hot_words_reducer.py",
                '-reducer', 'python hot_words_reducer.py',
                '-input', input_path,
                '-output', output_path
            ]

            # 执行MapReduce作业
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='hadoop_scripts')

            if result.returncode == 0:
                logger.info(f"热词分析完成，输出路径: {output_path}")
                return output_path
            else:
                raise Exception(f"MapReduce作业失败: {result.stderr}")

        except Exception as e:
            logger.error(f"热词分析作业失败: {e}")
            raise

    def run_sentiment_analysis(self, input_path: str, date: datetime) -> str:
        """
        运行情感分析MapReduce作业

        Args:
            input_path: 输入文件路径
            date: 分析日期

        Returns:
            输出路径
        """
        logger.info(f"开始情感分析作业")

        try:
            output_path = f"{self.hdfs_paths['output']}/sentiment/{date.strftime('%Y%m%d')}"

            # 构建Hadoop命令
            cmd = [
                'hadoop', 'jar', self.config['hadoop']['streaming_jar'],
                '-file', f"{self.hdfs_paths['scripts']}/sentiment_mapper.py",
                '-mapper', 'python sentiment_mapper.py',
                '-file', f"{self.hdfs_paths['scripts']}/sentiment_reducer.py",
                '-reducer', 'python sentiment_reducer.py',
                '-input', input_path,
                '-output', output_path
            ]

            # 执行MapReduce作业
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='hadoop_scripts')

            if result.returncode == 0:
                logger.info(f"情感分析完成，输出路径: {output_path}")
                return output_path
            else:
                raise Exception(f"MapReduce作业失败: {result.stderr}")

        except Exception as e:
            logger.error(f"情感分析作业失败: {e}")
            raise

    def run_user_behavior_analysis(self, input_path: str, date: datetime) -> str:
        """
        运行用户行为分析MapReduce作业

        Args:
            input_path: 输入文件路径
            date: 分析日期

        Returns:
            输出路径
        """
        logger.info(f"开始用户行为分析作业")

        try:
            output_path = f"{self.hdfs_paths['output']}/user_behavior/{date.strftime('%Y%m%d')}"

            # 构建Hadoop命令
            cmd = [
                'hadoop', 'jar', self.config['hadoop']['streaming_jar'],
                '-file', f"{self.hdfs_paths['scripts']}/user_behavior_mapper.py",
                '-mapper', 'python user_behavior_mapper.py',
                '-file', f"{self.hdfs_paths['scripts']}/user_behavior_reducer.py",
                '-reducer', 'python user_behavior_reducer.py',
                '-input', input_path,
                '-output', output_path
            ]

            # 执行MapReduce作业
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='hadoop_scripts')

            if result.returncode == 0:
                logger.info(f"用户行为分析完成，输出路径: {output_path}")
                return output_path
            else:
                raise Exception(f"MapReduce作业失败: {result.stderr}")

        except Exception as e:
            logger.error(f"用户行为分析作业失败: {e}")
            raise

    def run_time_distribution_analysis(self, input_path: str, date: datetime) -> str:
        """
        运行时间分布分析MapReduce作业

        Args:
            input_path: 输入文件路径
            date: 分析日期

        Returns:
            输出路径
        """
        logger.info(f"开始时间分布分析作业")

        try:
            output_path = f"{self.hdfs_paths['output']}/time_distribution/{date.strftime('%Y%m%d')}"

            # 构建Hadoop命令
            cmd = [
                'hadoop', 'jar', self.config['hadoop']['streaming_jar'],
                '-file', f"{self.hdfs_paths['scripts']}/time_distribution_mapper.py",
                '-mapper', 'python time_distribution_mapper.py',
                '-file', f"{self.hdfs_paths['scripts']}/time_distribution_reducer.py",
                '-reducer', 'python time_distribution_reducer.py',
                '-input', input_path,
                '-output', output_path
            ]

            # 执行MapReduce作业
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='hadoop_scripts')

            if result.returncode == 0:
                logger.info(f"时间分布分析完成，输出路径: {output_path}")
                return output_path
            else:
                raise Exception(f"MapReduce作业失败: {result.stderr}")

        except Exception as e:
            logger.error(f"时间分布分析作业失败: {e}")
            raise

    def download_and_process_results(self, output_path: str, analysis_type: str) -> List[Dict[str, Any]]:
        """
        下载并处理分析结果

        Args:
            output_path: HDFS输出路径
            analysis_type: 分析类型

        Returns:
            处理后的结果数据
        """
        logger.info(f"下载并处理 {analysis_type} 分析结果")

        try:
            # 列出输出文件
            files = self.hdfs_client.list(output_path)
            result_files = [f for f in files if f.startswith('part-')]

            if not result_files:
                raise Exception(f"未找到输出文件: {output_path}")

            # 下载并合并结果
            results = []
            for result_file in result_files:
                file_path = f"{output_path}/{result_file}"

                with self.hdfs_client.read(file_path) as reader:
                    content = reader.read().decode('utf-8')

                # 解析结果
                for line in content.strip().split('\n'):
                    if line.strip():
                        try:
                            key, value = line.split('\t', 1)
                            results.append({
                                'key': key,
                                'value': json.loads(value),
                                'type': analysis_type
                            })
                        except Exception as e:
                            logger.warning(f"解析结果行失败: {line}, 错误: {e}")

            logger.info(f"已处理 {len(results)} 条{analysis_type}分析结果")
            return results

        except Exception as e:
            logger.error(f"下载并处理分析结果失败: {e}")
            raise

    def save_results_to_mysql(self, results: List[Dict[str, Any]], date: datetime):
        """
        将分析结果保存到MySQL

        Args:
            results: 分析结果
            date: 分析日期
        """
        logger.info(f"保存分析结果到MySQL")

        try:
            import mysql.connector

            # 连接MySQL
            conn = mysql.connector.connect(
                host=self.config['mysql']['host'],
                port=self.config['mysql']['port'],
                database=self.config['mysql']['database'],
                user=self.config['mysql']['user'],
                password=self.config['mysql']['password']
            )

            cursor = conn.cursor()

            # 按分析类型分组结果
            grouped_results = {}
            for result in results:
                analysis_type = result['type']
                if analysis_type not in grouped_results:
                    grouped_results[analysis_type] = []
                grouped_results[analysis_type].append(result)

            # 保存热词分析结果
            if 'hot_words' in grouped_results:
                self._save_hot_words_results(cursor, grouped_results['hot_words'], date)

            # 保存情感分析结果
            if 'sentiment' in grouped_results:
                self._save_sentiment_results(cursor, grouped_results['sentiment'], date)

            # 保存用户行为分析结果
            if 'user_behavior' in grouped_results:
                self._save_user_behavior_results(cursor, grouped_results['user_behavior'], date)

            # 保存时间分布分析结果
            if 'time_distribution' in grouped_results:
                self._save_time_distribution_results(cursor, grouped_results['time_distribution'], date)

            conn.commit()
            cursor.close()
            conn.close()

            logger.info("分析结果已保存到MySQL")

        except Exception as e:
            logger.error(f"保存分析结果到MySQL失败: {e}")
            raise

    def _save_hot_words_results(self, cursor, results: List[Dict[str, Any]], date: datetime):
        """保存热词分析结果"""
        for result in results:
            key = result['key']
            value = result['value']

            # 解析房间ID和热词信息
            parts = key.split(':', 1)
            if len(parts) == 2:
                room_id = parts[0]
                word = parts[1]
                count = value.get('count', 0)

                query = """
                    INSERT INTO barrage_summary
                    (streamer_config_id, platform, room_id, summary_minute, hot_keywords)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE hot_keywords = VALUES(hot_keywords)
                """

                # 这里需要根据实际的数据结构进行调整
                cursor.execute(query, (0, 'unknown', room_id, date, json.dumps({word: count})))

    def _save_sentiment_results(self, cursor, results: List[Dict[str, Any]], date: datetime):
        """保存情感分析结果"""
        for result in results:
            key = result['key']
            value = result['value']

            # 解析情感分析数据
            sentiment_score = value.get('avg_sentiment', 0)
            total_count = value.get('count', 0)

            query = """
                UPDATE barrage_summary
                SET sentiment_score = %s, barrage_count = %s
                WHERE summary_minute = %s
            """

            cursor.execute(query, (sentiment_score, total_count, date))

    def _save_user_behavior_results(self, cursor, results: List[Dict[str, Any]], date: datetime):
        """保存用户行为分析结果"""
        for result in results:
            key = result['key']
            value = result['value']

            # 这里可以根据需要保存用户行为数据
            pass

    def _save_time_distribution_results(self, cursor, results: List[Dict[str, Any]], date: datetime):
        """保存时间分布分析结果"""
        for result in results:
            key = result['key']
            value = result['value']

            # 这里可以根据需要保存时间分布数据
            pass

    def _create_hot_words_scripts(self, scripts_dir: str):
        """创建热词分析MapReduce脚本"""

        # Mapper脚本
        mapper_content = '''#!/usr/bin/env python3
import sys
import json
import jieba
from collections import Counter

# 常见停用词
STOP_WORDS = {
    '的', '了', '和', '是', '就', '都', '而', '及', '与', '在', '这', '那', '有', '我', '你', '他',
    '啊', '哦', '嗯', '哈', '呀', '啦', '哇', '么', '着', '过', '地', '得', '个', '们', '不',
    '好', '大', '小', '多', '少', '很', '太', '真', '更', '最', '还', '又', '也', '都', '要',
    '会', '能', '可以', '可能', '应该', '必须', '一定', '真的', '确实', '就是', '这个', '那个'
}

def is_valid_word(word):
    """判断是否为有效词汇"""
    if len(word) < 2:
        return False
    if word in STOP_WORDS:
        return False
    if word.isdigit():
        return False
    return True

def main():
    for line in sys.stdin:
        try:
            data = json.loads(line.strip())
            content = data.get('content', '')
            room_id = data.get('room_id', '')
            platform = data.get('platform', '')

            if content and room_id:
                # 分词
                words = jieba.lcut(content)

                # 过滤并统计
                for word in words:
                    if is_valid_word(word):
                        key = f"{room_id}:{word}"
                        print(f"{key}\t1")

        except Exception as e:
            continue

if __name__ == '__main__':
    main()
'''

        # Reducer脚本
        reducer_content = '''#!/usr/bin/env python3
import sys
import json

current_key = None
current_count = 0
total_count = 0

def main():
    global current_key, current_count, total_count

    for line in sys.stdin:
        try:
            key, value = line.strip().split('\t', 1)
            count = int(value)

            if current_key == key:
                current_count += count
            else:
                if current_key:
                    # 输出结果
                    room_id, word = current_key.split(':', 1)
                    result = {
                        'word': word,
                        'count': current_count,
                        'frequency': current_count / total_count if total_count > 0 else 0
                    }
                    print(f"{current_key}\t{json.dumps(result, ensure_ascii=False)}")

                current_key = key
                current_count = count
                total_count += count

        except Exception as e:
            continue

    # 输出最后一个key
    if current_key:
        room_id, word = current_key.split(':', 1)
        result = {
            'word': word,
            'count': current_count,
            'frequency': current_count / total_count if total_count > 0 else 0
        }
        print(f"{current_key}\t{json.dumps(result, ensure_ascii=False)}")

if __name__ == '__main__':
    main()
'''

        # 写入文件
        with open(os.path.join(scripts_dir, 'hot_words_mapper.py'), 'w', encoding='utf-8') as f:
            f.write(mapper_content)

        with open(os.path.join(scripts_dir, 'hot_words_reducer.py'), 'w', encoding='utf-8') as f:
            f.write(reducer_content)

    def _create_sentiment_scripts(self, scripts_dir: str):
        """创建情感分析MapReduce脚本"""

        # Mapper脚本
        mapper_content = '''#!/usr/bin/env python3
import sys
import json

# 简单的情感词典
POSITIVE_WORDS = {
    '好', '棒', '赞', '强', '厉害', '牛逼', '666', '优秀', '精彩', '喜欢', '爱', '支持',
    '开心', '高兴', '兴奋', '激动', '感动', '温暖', '美好', '完美', '赞', '不错', '可以'
}

NEGATIVE_WORDS = {
    '差', '烂', '垃圾', '失望', '讨厌', '恶心', '烦', '无聊', '糟糕', '垃圾', '不好',
    '生气', '愤怒', '伤心', '难过', '痛苦', '郁闷', '烦躁', '不爽', '垃圾', '废物'
}

def analyze_sentiment(text):
    """简单的情感分析"""
    if not text:
        return 0.0

    text_lower = text.lower()
    positive_count = sum(1 for word in POSITIVE_WORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_WORDS if word in text_lower)

    if positive_count + negative_count == 0:
        return 0.0

    return (positive_count - negative_count) / (positive_count + negative_count)

def main():
    for line in sys.stdin:
        try:
            data = json.loads(line.strip())
            content = data.get('content', '')
            room_id = data.get('room_id', '')
            timestamp = data.get('timestamp', '')

            if content and room_id:
                sentiment = analyze_sentiment(content)
                key = room_id
                value = {
                    'sentiment': sentiment,
                    'count': 1,
                    'timestamp': timestamp
                }
                print(f"{key}\t{json.dumps(value)}")

        except Exception as e:
            continue

if __name__ == '__main__':
    main()
'''

        # Reducer脚本
        reducer_content = '''#!/usr/bin/env python3
import sys
import json

current_key = None
sentiment_sum = 0.0
count = 0

def main():
    global current_key, sentiment_sum, count

    for line in sys.stdin:
        try:
            key, value_str = line.strip().split('\t', 1)
            value = json.loads(value_str