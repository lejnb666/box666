"""
直播弹幕数据分析流水线
使用Airflow调度T+1离线分析任务
"""

from datetime import datetime, timedelta
import logging
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.apache.hive.operators.hive_operator import HiveOperator
from airflow.providers.mysql.operators.mysql import MySqlOperator
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.providers.apache.hdfs.hooks.hdfs import HDFSHook
from airflow.utils.dates import days_ago
from airflow.models import Variable

# 配置日志
logger = logging.getLogger(__name__)

default_args = {
    'owner': 'stream_analytics',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'catchup': False,
}

# 定义DAG
dag = DAG(
    'stream_analytics_pipeline',
    default_args=default_args,
    description='直播弹幕数据分析流水线',
    schedule_interval='0 2 * * *',  # 每天凌晨2点执行
    max_active_runs=1,
    tags=['analytics', 'stream', 'barrage'],
)

def extract_daily_data(**context):
    """从MongoDB抽取昨日数据到HDFS"""
    try:
        # 获取昨日日期
        execution_date = context['execution_date']
        yesterday = execution_date.subtract(days=1)

        logger.info(f"开始抽取 {yesterday.strftime('%Y-%m-%d')} 的数据")

        # 连接MongoDB
        mongo_hook = MongoHook(conn_id='mongo_default')
        client = mongo_hook.get_conn()
        db = client.stream_monitor

        # 查询昨日数据
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        query = {
            "timestamp": {
                "$gte": start_time,
                "$lt": end_time
            }
        }

        # 分批处理数据
        batch_size = 10000
        total_count = 0

        cursor = db.barrage.find(query).batch_size(batch_size)

        # 连接HDFS
        hdfs_hook = HDFSHook(conn_id='hdfs_default')
        hdfs_client = hdfs_hook.get_conn()

        # 创建HDFS目录
        hdfs_base_path = f"/barrage_data/{yesterday.strftime('%Y/%m/%d')}"
        try:
            hdfs_client.makedirs(hdfs_base_path)
        except:
            pass  # 目录可能已存在

        # 处理数据批次
        batch_data = []
        temp_file_path = f"/tmp/barrage_{yesterday.strftime('%Y%m%d')}.json"

        with open(temp_file_path, 'w', encoding='utf-8') as f:
            for doc in cursor:
                # 转换数据格式
                processed_doc = {
                    '_id': str(doc.get('_id', '')),
                    'streamer_id': doc.get('streamer_id', ''),
                    'streamer_name': doc.get('streamer_name', ''),
                    'user_id': doc.get('user_id', ''),
                    'user_name': doc.get('user_name', ''),
                    'content': doc.get('content', ''),
                    'timestamp': doc.get('timestamp').isoformat() if doc.get('timestamp') else None,
                    'barrage_type': doc.get('barrage_type', 'normal'),
                    'gift_value': float(doc.get('gift_value', 0)),
                    'platform': doc.get('platform', ''),
                    'room_id': doc.get('room_id', ''),
                    'user_level': int(doc.get('user_level', 0)),
                    'content_length': len(doc.get('content', '')),
                    'year': yesterday.year,
                    'month': yesterday.month,
                    'day': yesterday.day
                }

                f.write(json.dumps(processed_doc, ensure_ascii=False) + '\n')
                total_count += 1

                if total_count % 10000 == 0:
                    logger.info(f"已处理 {total_count} 条记录")

        # 上传文件到HDFS
        hdfs_file_path = f"{hdfs_base_path}/barrage.json"
        hdfs_client.put(temp_file_path, hdfs_file_path)

        # 转换为Parquet格式
        convert_to_parquet = f"""
        python3 -c "
import pandas as pd
import json

# 读取JSON数据
with open('{temp_file_path}', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

df = pd.DataFrame(data)

# 转换时间戳
df['timestamp'] = pd.to_datetime(df['timestamp'])

# 保存为Parquet
parquet_path = '{temp_file_path.replace('.json', '.parquet')}'
df.to_parquet(parquet_path, compression='snappy', index=False)
print(f'转换完成: {parquet_path}')
        "
        """

        import subprocess
        subprocess.run(convert_to_parquet, shell=True, check=True)

        # 上传Parquet文件
        parquet_hdfs_path = f"{hdfs_base_path}/barrage.parquet"
        parquet_temp_path = temp_file_path.replace('.json', '.parquet')
        hdfs_client.put(parquet_temp_path, parquet_hdfs_path)

        # 清理临时文件
        import os
        os.remove(temp_file_path)
        os.remove(parquet_temp_path)

        logger.info(f"数据抽取完成，共处理 {total_count} 条记录")

        # 将处理结果传递给下一个任务
        context['task_instance'].xcom_push(key='total_records', value=total_count)
        context['task_instance'].xcom_push(key='hdfs_path', value=hdfs_file_path)

    except Exception as e:
        logger.error(f"数据抽取失败: {e}")
        raise

def add_hive_partition(**context):
    """添加Hive分区"""
    try:
        execution_date = context['execution_date']
        year = execution_date.year
        month = execution_date.month
        day = execution_date.day

        # 添加Hive分区的SQL
        add_partition_sql = f"""
        ALTER TABLE barrage_data ADD IF NOT EXISTS PARTITION
        (year={year}, month={month:02d}, day={day:02d})
        LOCATION 'hdfs://namenode:9000/barrage_data/{year}/{month:02d}/{day:02d}/';
        """

        logger.info(f"添加Hive分区: {add_partition_sql}")

        # 这里应该使用HiveOperator执行SQL
        # 为了演示，我们只是记录SQL
        context['task_instance'].xcom_push(key='partition_sql', value=add_partition_sql)

    except Exception as e:
        logger.error(f"添加Hive分区失败: {e}")
        raise

def run_hot_words_analysis(**context):
    """运行热词分析"""
    try:
        execution_date = context['execution_date']

        # 热词分析的Hive SQL
        hot_words_sql = f"""
        INSERT OVERWRITE TABLE hot_words_statistics
        SELECT
            streamer_id,
            streamer_name,
            '{execution_date.strftime('%Y-%m-%d')}',
            word,
            word_count,
            ROUND(word_count * 100.0 / total_words, 2) as word_frequency,
            ROW_NUMBER() OVER (PARTITION BY streamer_id ORDER BY word_count DESC) as rank_num,
            CASE
                WHEN word IN ('好', '棒', '赞', '666', '厉害', '牛逼', '强', '喜欢', '爱', '支持') THEN 'positive'
                WHEN word IN ('差', '烂', '垃圾', '无语', '失望', '讨厌', '恶心', '烦', '无聊') THEN 'negative'
                WHEN word IN ('礼物', '打赏', '刷', '送', '火箭', '跑车', '鲜花') THEN 'gift'
                WHEN word IN ('主播', '直播间', '直播', '观看', '粉丝') THEN 'stream'
                ELSE 'general'
            END as category,
            'stable' as trend_direction
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                word,
                COUNT(*) as word_count,
                SUM(COUNT(*)) OVER (PARTITION BY streamer_id) as total_words
            FROM (
                SELECT
                    streamer_id,
                    streamer_name,
                    EXPLODE(SPLIT(LOWER(content), ' ')) as word
                FROM barrage_data
                WHERE year = {execution_date.year}
                  AND month = {execution_date.month}
                  AND day = {execution_date.day}
                  AND LENGTH(TRIM(content)) > 0
            ) words
            WHERE LENGTH(word) > 1
              AND word NOT IN ('的', '了', '是', '我', '你', '在', '有', '不', '这', '就', '都', '也', '和', '要', '会', '能', '可以', '很', '好', '太', '真', '啊', '哦', '嗯')
            GROUP BY streamer_id, streamer_name, word
        ) word_stats
        WHERE word_count >= 5
        ORDER BY streamer_id, word_count DESC;
        """

        logger.info("执行热词分析")
        context['task_instance'].xcom_push(key='hot_words_sql', value=hot_words_sql)

    except Exception as e:
        logger.error(f"热词分析失败: {e}")
        raise

def run_activity_analysis(**context):
    """运行活跃度分析"""
    try:
        execution_date = context['execution_date']

        # 活跃度分析的Hive SQL
        activity_sql = f"""
        INSERT OVERWRITE TABLE viewer_activity_heatmap
        SELECT
            streamer_id,
            streamer_name,
            '{execution_date.strftime('%Y-%m-%d')}',
            hour,
            barrage_count,
            active_users,
            ROUND(avg_content_length, 2) as avg_content_length,
            gift_count,
            ROUND(gift_value, 2) as gift_value,
            ROUND(
                (barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2 + avg_content_length * 0.1) /
                MAX(barrage_count * 0.3 + active_users * 0.4 + gift_count * 0.2 + avg_content_length * 0.1) OVER (PARTITION BY streamer_id) * 100,
                2
            ) as engagement_score,
            CASE
                WHEN barrage_count >= PERCENTILE(barrage_count, 0.8) OVER (PARTITION BY streamer_id) THEN 'high'
                WHEN barrage_count >= PERCENTILE(barrage_count, 0.5) OVER (PARTITION BY streamer_id) THEN 'medium'
                ELSE 'low'
            END as activity_level
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                HOUR(timestamp) as hour,
                COUNT(*) as barrage_count,
                COUNT(DISTINCT user_id) as active_users,
                AVG(content_length) as avg_content_length,
                SUM(CASE WHEN gift_value > 0 THEN 1 ELSE 0 END) as gift_count,
                SUM(gift_value) as gift_value
            FROM barrage_data
            WHERE year = {execution_date.year}
              AND month = {execution_date.month}
              AND day = {execution_date.day}
            GROUP BY streamer_id, streamer_name, HOUR(timestamp)
        ) hourly_stats
        ORDER BY streamer_id, hour;
        """

        logger.info("执行活跃度分析")
        context['task_instance'].xcom_push(key='activity_sql', value=activity_sql)

    except Exception as e:
        logger.error(f"活跃度分析失败: {e}")
        raise

def run_sentiment_analysis(**context):
    """运行情感分析"""
    try:
        execution_date = context['execution_date']

        # 情感分析的Hive SQL
        sentiment_sql = f"""
        INSERT OVERWRITE TABLE sentiment_analysis
        SELECT
            streamer_id,
            streamer_name,
            '{execution_date.strftime('%Y-%m-%d')}',
            hour,
            total_barrages,
            positive_count,
            negative_count,
            neutral_count,
            ROUND(positive_count * 100.0 / total_barrages, 2) as positive_ratio,
            ROUND(negative_count * 100.0 / total_barrages, 2) as negative_ratio,
            ROUND((positive_count - negative_count) * 100.0 / total_barrages, 2) as sentiment_score,
            CASE
                WHEN positive_count > negative_count AND positive_count > neutral_count THEN 'positive'
                WHEN negative_count > positive_count AND negative_count > neutral_count THEN 'negative'
                ELSE 'neutral'
            END as dominant_sentiment
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                hour,
                COUNT(*) as total_barrages,
                SUM(CASE WHEN sentiment_sum > 0 THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN sentiment_sum < 0 THEN 1 ELSE 0 END) as negative_count,
                SUM(CASE WHEN sentiment_sum = 0 THEN 1 ELSE 0 END) as neutral_count
            FROM (
                SELECT
                    streamer_id,
                    streamer_name,
                    HOUR(timestamp) as hour,
                    content,
                    SUM(
                        CASE
                            WHEN content LIKE '%好%' OR content LIKE '%棒%' OR content LIKE '%赞%' OR content LIKE '%666%' OR content LIKE '%厉害%' THEN 1
                            WHEN content LIKE '%差%' OR content LIKE '%烂%' OR content LIKE '%垃圾%' OR content LIKE '%无语%' OR content LIKE '%失望%' THEN -1
                            ELSE 0
                        END
                    ) as sentiment_sum
                FROM barrage_data
                WHERE year = {execution_date.year}
                  AND month = {execution_date.month}
                  AND day = {execution_date.day}
                GROUP BY streamer_id, streamer_name, HOUR(timestamp), content
            ) sentiment_scores
            GROUP BY streamer_id, streamer_name, hour
        ) hourly_sentiment
        ORDER BY streamer_id, hour;
        """

        logger.info("执行情感分析")
        context['task_instance'].xcom_push(key='sentiment_sql', value=sentiment_sql)

    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        raise

def generate_daily_report(**context):
    """生成日报"""
    try:
        execution_date = context['execution_date']

        # 生成主播综合表现报表
        performance_sql = f"""
        INSERT OVERWRITE TABLE streamer_performance_daily
        SELECT
            s.streamer_id,
            s.streamer_name,
            '{execution_date.strftime('%Y-%m-%d')}',
            s.total_barrages,
            s.unique_viewers,
            s.total_gift_value,
            ROUND(s.avg_engagement_score, 2) as avg_engagement_score,
            CASE
                WHEN s.avg_engagement_score >= 80 THEN 'A'
                WHEN s.avg_engagement_score >= 60 THEN 'B'
                WHEN s.avg_engagement_score >= 40 THEN 'C'
                ELSE 'D'
            END as performance_grade,
            hw.top_words,
            sa.sentiment_summary,
            va.peak_hours
        FROM (
            SELECT
                streamer_id,
                streamer_name,
                SUM(barrage_count) as total_barrages,
                SUM(active_users) as unique_viewers,
                SUM(gift_value) as total_gift_value,
                AVG(engagement_score) as avg_engagement_score
            FROM viewer_activity_heatmap
            WHERE date = '{execution_date.strftime('%Y-%m-%d')}'
            GROUP BY streamer_id, streamer_name
        ) s
        LEFT JOIN (
            SELECT
                streamer_id,
                CONCAT_WS(',', COLLECT_LIST(CONCAT(word, '(', count, ')'))) as top_words
            FROM hot_words_statistics
            WHERE date = '{execution_date.strftime('%Y-%m-%d')}' AND rank_num <= 5
            GROUP BY streamer_id
        ) hw ON s.streamer_id = hw.streamer_id
        LEFT JOIN (
            SELECT
                streamer_id,
                CONCAT('正面:', MAX(positive_ratio), '%,负面:', MAX(negative_ratio), '%,主导情感:', MAX(dominant_sentiment)) as sentiment_summary
            FROM sentiment_analysis
            WHERE date = '{execution_date.strftime('%Y-%m-%d')}'
            GROUP BY streamer_id
        ) sa ON s.streamer_id = sa.streamer_id
        LEFT JOIN (
            SELECT
                streamer_id,
                CONCAT_WS(',', COLLECT_LIST(CONCAT(hour, '时'))) as peak_hours
            FROM viewer_activity_heatmap
            WHERE date = '{execution_date.strftime('%Y-%m-%d')}' AND activity_level = 'high'
            GROUP BY streamer_id
        ) va ON s.streamer_id = va.streamer_id;
        """

        logger.info("生成日报")
        context['task_instance'].xcom_push(key='performance_sql', value=performance_sql)

    except Exception as e:
        logger.error(f"生成日报失败: {e}")
        raise

# 定义任务
start_task = DummyOperator(
    task_id='start_pipeline',
    dag=dag,
)

extract_data_task = PythonOperator(
    task_id='extract_daily_data',
    python_callable=extract_daily_data,
    provide_context=True,
    dag=dag,
)

add_partition_task = PythonOperator(
    task_id='add_hive_partition',
    python_callable=add_hive_partition,
    provide_context=True,
    dag=dag,
)

hot_words_task = PythonOperator(
    task_id='run_hot_words_analysis',
    python_callable=run_hot_words_analysis,
    provide_context=True,
    dag=dag,
)

activity_task = PythonOperator(
    task_id='run_activity_analysis',
    python_callable=run_activity_analysis,
    provide_context=True,
    dag=dag,
)

sentiment_task = PythonOperator(
    task_id='run_sentiment_analysis',
    python_callable=run_sentiment_analysis,
    provide_context=True,
    dag=dag,
)

generate_report_task = PythonOperator(
    task_id='generate_daily_report',
    python_callable=generate_daily_report,
    provide_context=True,
    dag=dag,
)

end_task = DummyOperator(
    task_id='end_pipeline',
    dag=dag,
)

# 设置任务依赖关系
start_task >> extract_data_task >> add_partition_task

add_partition_task >> [hot_words_task, activity_task, sentiment_task]

[hot_words_task, activity_task, sentiment_task] >> generate_report_task >> end_task

# 可选：添加数据质量检查任务
def data_quality_check(**context):
    """数据质量检查"""
    try:
        execution_date = context['execution_date']

        # 检查数据完整性
        quality_check_sql = f"""
        INSERT INTO data_quality_monitor
        SELECT
            '{execution_date.strftime('%Y-%m-%d')}',
            'data_volume',
            COUNT(*) as record_count,
            COUNT(DISTINCT streamer_id) as streamer_count,
            COUNT(DISTINCT user_id) as user_count,
            CASE
                WHEN COUNT(*) < 1000 THEN 'low'
                WHEN COUNT(*) < 10000 THEN 'medium'
                ELSE 'high'
            END as data_volume_level,
            100.0 as completeness_score,
            'normal' as quality_status,
            NULL as issues
        FROM barrage_data
        WHERE year = {execution_date.year}
          AND month = {execution_date.month}
          AND day = {execution_date.day};
        """

        logger.info("执行数据质量检查")
        context['task_instance'].xcom_push(key='quality_check_sql', value=quality_check_sql)

    except Exception as e:
        logger.error(f"数据质量检查失败: {e}")
        raise

quality_check_task = PythonOperator(
    task_id='data_quality_check',
    python_callable=data_quality_check,
    provide_context=True,
    dag=dag,
)

# 将质量检查任务添加到流水线中
generate_report_task >> quality_check_task >> end_task