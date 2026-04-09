#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地浅层过滤服务 - 实现高效的弹幕预处理和过滤

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import re
import time
import jieba
import jieba.analyse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Any, Optional
from loguru import logger


class LocalFilterService:
    """
    本地浅层过滤服务，用于在调用大模型前进行高效的弹幕过滤和预处理
    """

    def __init__(self):
        # 无意义弹幕关键词（用于过滤）
        self.meaningless_words = {
            '哈哈哈', '哈哈', 'hhh', '2333', '666', '6666', '牛逼', 'nb', '卧槽',
            '我草', '草', 'emmm', 'emm', '???', '？？？', '。。。。', '....', '~~~',
            '啊啊啊', '哇哇哇', '嘻嘻', '嘿嘿', '呵呵', '嗯嗯', '哦哦', '啊啊',
            '1111', '2222', '3333', '4444', '5555', '1234', 'qwer', 'asdf'
        }

        # 重复字符模式（如：啊啊啊啊啊啊）
        self.repeat_pattern = re.compile(r'(.)\1{3,}')  # 4个或以上重复字符

        # 纯数字/字母模式
        self.pure_number_pattern = re.compile(r'^[0-9]+$')
        self.pure_letter_pattern = re.compile(r'^[a-zA-Z]+$')

        # 关键事件触发词
        self.event_triggers = {
            'product_launch': {
                '上车', '链接', '购买', '下单', '商品', '现货', '发货', '包邮',
                '售后', '价格', '优惠', '折扣', '特价', '秒杀', '促销', '买',
                '卖', '库存', '限量', '抢购', '团购', '拼团', '优惠券', '红包'
            },
            'lottery': {
                '抽奖', '中奖', '礼物', '福袋', '红包', '转盘', '刮刮乐', '免费',
                '赠送', '福利', '奖品', '中奖了', '手气', '运气', '概率', '几率'
            },
            'discount': {
                '降价', '便宜', '划算', '超值', '白菜价', '吐血价', '骨折价',
                '跳楼价', '清仓', '甩卖', '处理', '特价', '秒杀', '限时', '抢购'
            },
            'game_highlight': {
                '五杀', '超神', '三杀', '双杀', '单杀', '团灭', 'ace', '翻盘',
                '逆袭', '天秀', '神仙操作', '666', '牛逼', '卧槽', '精彩',
                '刺激', '高潮', '决战', '最后一波', '赢了', '输了', 'gg'
            }
        }

        # 弹幕窗口管理
        self.barrage_windows: Dict[str, List[Dict]] = {}
        self.window_duration = 60  # 60秒窗口
        self.max_window_size = 100  # 最大弹幕数量

        # 高频词统计
        self.high_freq_words: Dict[str, Counter] = defaultdict(Counter)
        self.freq_update_interval = 300  # 5分钟更新一次
        self.last_freq_update = time.time()

        # 过滤统计
        self.stats = {
            'total_processed': 0,
            'filtered_meaningless': 0,
            'filtered_repeated': 0,
            'filtered_short': 0,
            'event_detected': 0,
            'density_spike': 0
        }

        # 密度检测参数
        self.density_window = 10  # 10秒密度窗口
        self.density_threshold = 50  # 每秒5条弹幕
        self.density_history: Dict[str, List[float]] = defaultdict(list)

        logger.info("本地浅层过滤服务初始化完成")

    async def process_barrage(self, platform: str, room_id: str, barrage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        处理单条弹幕，返回处理后的弹幕或None（如果被过滤）
        """
        self.stats['total_processed'] += 1

        content = barrage.get('content', '').strip()
        if not content:
            return None

        # 基础过滤
        filtered_content = self._basic_filter(content)
        if not filtered_content:
            return None

        # 更新弹幕窗口
        room_key = f"{platform}:{room_id}"
        self._update_barrage_window(room_key, {
            **barrage,
            'content': filtered_content,
            'processed_at': time.time()
        })

        # 更新高频词统计
        self._update_frequency_stats(room_key, filtered_content)

        return {
            **barrage,
            'content': filtered_content,
            'filtered': True
        }

    def _basic_filter(self, content: str) -> Optional[str]:
        """基础过滤规则"""
        # 过滤空内容和过短内容
        if len(content) < 2:
            self.stats['filtered_short'] += 1
            return None

        # 过滤纯数字/字母
        if self.pure_number_pattern.match(content) or self.pure_letter_pattern.match(content):
            if len(content) < 4:  # 短数字/字母直接过滤
                self.stats['filtered_meaningless'] += 1
                return None

        # 过滤重复字符（如：啊啊啊啊啊啊）
        if self.repeat_pattern.search(content):
            self.stats['filtered_repeated'] += 1
            return None

        # 过滤无意义词汇
        if content in self.meaningless_words:
            self.stats['filtered_meaningless'] += 1
            return None

        # 过滤过长的内容（可能是刷屏）
        if len(content) > 100:
            content = content[:100] + '...'

        return content

    def _update_barrage_window(self, room_key: str, barrage: Dict[str, Any]):
        """更新弹幕窗口"""
        current_time = time.time()

        if room_key not in self.barrage_windows:
            self.barrage_windows[room_key] = []

        # 添加新弹幕
        self.barrage_windows[room_key].append(barrage)

        # 清理过期弹幕
        cutoff_time = current_time - self.window_duration
        self.barrage_windows[room_key] = [
            b for b in self.barrage_windows[room_key]
            if b['processed_at'] > cutoff_time
        ]

        # 限制窗口大小
        if len(self.barrage_windows[room_key]) > self.max_window_size:
            self.barrage_windows[room_key] = self.barrage_windows[room_key][-self.max_window_size:]

    def _update_frequency_stats(self, room_key: str, content: str):
        """更新高频词统计"""
        current_time = time.time()

        # 定期重置统计
        if current_time - self.last_freq_update > self.freq_update_interval:
            self.high_freq_words.clear()
            self.last_freq_update = current_time

        # 分词并统计
        words = jieba.lcut(content)
        for word in words:
            if len(word) > 1 and not self.pure_number_pattern.match(word):
                self.high_freq_words[room_key][word] += 1

    def should_trigger_ai_analysis(self, platform: str, room_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        判断是否应该触发AI分析
        返回: (是否触发, 触发原因, 详细信息)
        """
        room_key = f"{platform}:{room_id}"

        # 检查弹幕窗口
        if room_key not in self.barrage_windows:
            return False, "无弹幕数据", {}

        barrages = self.barrage_windows[room_key]
        if len(barrages) < 5:  # 至少5条弹幕才分析
            return False, "弹幕数量不足", {}

        # 检查密度激增
        density_trigger, density_info = self._check_density_spike(room_key)
        if density_trigger:
            self.stats['density_spike'] += 1
            return True, "弹幕密度激增", density_info

        # 检查关键事件
        event_trigger, event_info = self._check_key_events(barrages)
        if event_trigger:
            self.stats['event_detected'] += 1
            return True, "检测到关键事件", event_info

        # 检查高频词异常
        freq_trigger, freq_info = self._check_frequency_anomaly(room_key)
        if freq_trigger:
            return True, "高频词异常", freq_info

        return False, "未达到触发条件", {}

    def _check_density_spike(self, room_key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查弹幕密度激增"""
        current_time = time.time()
        current_density = len(self.barrage_windows.get(room_key, [])) / self.window_duration

        # 记录当前密度
        self.density_history[room_key].append(current_density)

        # 只保留最近6个数据点（1分钟）
        if len(self.density_history[room_key]) > 6:
            self.density_history[room_key] = self.density_history[room_key][-6:]

        # 计算平均密度
        if len(self.density_history[room_key]) < 3:
            return False, {}

        avg_density = sum(self.density_history[room_key][:-1]) / (len(self.density_history[room_key]) - 1)
        current_density = self.density_history[room_key][-1]

        # 如果当前密度是平均密度的3倍以上，认为是激增
        if current_density > avg_density * 3 and current_density > self.density_threshold:
            return True, {
                'current_density': current_density,
                'average_density': avg_density,
                'spike_ratio': current_density / avg_density,
                'barrage_count': len(self.barrage_windows.get(room_key, []))
            }

        return False, {}

    def _check_key_events(self, barrages: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """检查关键事件触发词"""
        event_scores = defaultdict(int)
        event_keywords = defaultdict(list)

        for barrage in barrages[-20:]:  # 检查最近20条弹幕
            content = barrage.get('content', '').lower()

            for event_type, keywords in self.event_triggers.items():
                for keyword in keywords:
                    if keyword in content:
                        event_scores[event_type] += 1
                        event_keywords[event_type].append(keyword)

        # 如果有任何事件类型得分超过阈值
        for event_type, score in event_scores.items():
            if score >= 3:  # 3个或以上关键词匹配
                return True, {
                    'event_type': event_type,
                    'score': score,
                    'keywords': list(set(event_keywords[event_type])),
                    'barrages_analyzed': len(barrages)
                }

        return False, {}

    def _check_frequency_anomaly(self, room_key: str) -> Tuple[bool, Dict[str, Any]]:
        """检查高频词异常"""
        if room_key not in self.high_freq_words:
            return False, {}

        word_counts = self.high_freq_words[room_key]
        if len(word_counts) < 3:
            return False, {}

        # 获取最高频的词
        most_common = word_counts.most_common(3)
        top_word, top_count = most_common[0]

        # 如果某个词出现频率异常高（超过总量的50%）
        total_words = sum(word_counts.values())
        if top_count / total_words > 0.5 and top_count >= 10:
            return True, {
                'anomaly_word': top_word,
                'word_count': top_count,
                'total_words': total_words,
                'frequency_ratio': top_count / total_words,
                'top_words': most_common
            }

        return False, {}

    def get_filtered_barrages(self, platform: str, room_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """获取过滤后的弹幕用于AI分析"""
        room_key = f"{platform}:{room_id}"

        if room_key not in self.barrage_windows:
            return []

        # 返回最近的弹幕，限制数量
        barrages = self.barrage_windows[room_key]
        return barrages[-limit:] if len(barrages) > limit else barrages

    def extract_keywords(self, platform: str, room_id: str, top_k: int = 10) -> List[Tuple[str, int]]:
        """提取高频关键词"""
        room_key = f"{platform}:{room_id}"

        if room_key not in self.high_freq_words:
            return []

        return self.high_freq_words[room_key].most_common(top_k)

    def get_stats(self) -> Dict[str, Any]:
        """获取过滤统计信息"""
        return {
            **self.stats,
            'active_rooms': len(self.barrage_windows),
            'total_windows': len(self.barrage_windows),
            'filter_rate': (
                (self.stats['filtered_meaningless'] +
                 self.stats['filtered_repeated'] +
                 self.stats['filtered_short']) / max(1, self.stats['total_processed'])
            ),
            'event_detection_rate': self.stats['event_detected'] / max(1, self.stats['total_processed']),
            'density_spike_rate': self.stats['density_spike'] / max(1, self.stats['total_processed'])
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_processed': 0,
            'filtered_meaningless': 0,
            'filtered_repeated': 0,
            'filtered_short': 0,
            'event_detected': 0,
            'density_spike': 0
        }

    async def cleanup_expired_data(self):
        """清理过期数据"""
        current_time = time.time()
        expired_rooms = []

        # 清理过期弹幕窗口
        cutoff_time = current_time - self.window_duration
        for room_key, barrages in self.barrage_windows.items():
            # 过滤过期弹幕
            self.barrage_windows[room_key] = [
                b for b in barrages if b['processed_at'] > cutoff_time
            ]

            # 如果窗口为空，标记为过期
            if not self.barrage_windows[room_key]:
                expired_rooms.append(room_key)

        # 清理过期房间
        for room_key in expired_rooms:
            del self.barrage_windows[room_key]
            if room_key in self.high_freq_words:
                del self.high_freq_words[room_key]
            if room_key in self.density_history:
                del self.density_history[room_key]

        logger.info(f"清理完成，移除 {len(expired_rooms)} 个过期房间")


# 使用示例
async def main():
    """测试本地过滤服务"""
    filter_service = LocalFilterService()

    # 模拟弹幕数据
    test_barrages = [
        {'content': '哈哈哈', 'user_id': '1', 'timestamp': time.time()},
        {'content': '666666666666', 'user_id': '2', 'timestamp': time.time()},
        {'content': '上车了上车了！', 'user_id': '3', 'timestamp': time.time()},
        {'content': '链接在哪里？', 'user_id': '4', 'timestamp': time.time()},
        {'content': '买买买！', 'user_id': '5', 'timestamp': time.time()},
        {'content': '这个价格太便宜了', 'user_id': '6', 'timestamp': time.time()},
    ]

    # 处理弹幕
    for barrage in test_barrages:
        result = await filter_service.process_barrage('bilibili', '123456', barrage)
        if result:
            print(f"✅ 保留: {result['content']}")
        else:
            print(f"❌ 过滤: {barrage['content']}")

    # 检查是否触发AI分析
    should_trigger, reason, info = filter_service.should_trigger_ai_analysis('bilibili', '123456')
    print(f"\nAI分析触发: {should_trigger}, 原因: {reason}")
    if info:
        print(f"详细信息: {info}")

    # 获取统计信息
    stats = filter_service.get_stats()
    print(f"\n过滤统计: {stats}")


if __name__ == '__main__':
    asyncio.run(main())