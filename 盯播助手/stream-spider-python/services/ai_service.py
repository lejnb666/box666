# -*- coding: utf-8 -*-

"""
AI服务 - 负责语义分析和内容理解

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple, Any

import aiohttp
import jieba
import openai
from loguru import logger

from config.settings import settings
from utils.logger import LoggerMixin


class AIService(LoggerMixin):
    """
    AI服务类，负责弹幕语义分析和内容理解
    """

    def __init__(self, app_settings):
        self.settings = app_settings.ai
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_initialized = False

        # AI调用成本控制参数
        self.min_density_threshold = 50  # 每分钟最少弹幕数才触发AI分析
        self.rule_confidence_threshold = 0.8  # 规则置信度阈值，高于此值不调用AI
        self.ai_confidence_threshold = 0.4  # AI调用阈值，规则置信度在此区间才调用AI
        self.last_ai_call_time = 0  # 上次AI调用时间
        self.ai_call_interval = 60  # AI调用最小间隔（秒）

        # 系统提示词模板
        self.system_prompts = {
            'lottery': "你是一个直播内容分析专家，请根据以下连续弹幕判断当前主播是否正在进行抽奖活动。"
                      "抽奖活动的特征包括：提到'抽奖'、'中奖'、'礼物'、'福袋'、'红包'等关键词，"
                      "或者主播明确表示正在进行抽奖。请返回JSON格式结果："
                      "{'is_lottery': True/False, 'confidence': 0.0-1.0, 'reason': '判断理由'}",

            'discount': "你是一个直播内容分析专家，请根据以下连续弹幕判断当前主播是否在进行大额降价促销。"
                       "降价促销的特征包括：提到'降价'、'优惠'、'折扣'、'秒杀'、'特价'等关键词，"
                       "或者价格明显下调。请返回JSON格式结果："
                       "{'is_discount': True/False, 'confidence': 0.0-1.0, 'reason': '判断理由'}",

            'game_highlight': "你是一个电竞直播内容分析专家，请根据以下连续弹幕判断当前是否处于比赛高潮或关键时刻。"
                             "比赛高潮的特征包括：提到'666'、'牛逼'、'精彩'、'团战'、'五杀'等关键词，"
                             "或者观众情绪激动。请返回JSON格式结果："
                             "{'is_highlight': True/False, 'confidence': 0.0-1.0, 'reason': '判断理由'}",

            'product_launch': "你是一个直播带货分析专家，请根据以下连续弹幕判断当前主播是否正在上架新商品。"
                             "商品上架的特征包括：提到'上车'、'链接'、'购买'、'下单'、'商品'等关键词，"
                             "或者主播介绍商品特点。请返回JSON格式结果："
                             "{'is_product_launch': True/False, 'confidence': 0.0-1.0, 'reason': '判断理由'}"
        }

        # 关键词词典
        self.keyword_dict = {
            'lottery': ['抽奖', '中奖', '礼物', '福袋', '红包', '转盘', '刮刮乐', '免费', '赠送'],
            'discount': ['降价', '优惠', '折扣', '秒杀', '特价', '促销', '大促', '便宜', '划算'],
            'game_highlight': ['666', '牛逼', '精彩', '团战', '五杀', '超神', '秀', '天秀', '操作'],
            'product_launch': ['上车', '链接', '购买', '下单', '商品', '现货', '发货', '包邮', '售后']
        }

    def initialize(self):
        """初始化AI服务"""
        try:
            # 配置OpenAI
            openai.api_key = self.settings.api_key
            openai.api_base = self.settings.api_base_url

            # 创建HTTP会话
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.settings.timeout)
            )

            self.is_initialized = True
            self.logger.info("AI服务初始化完成")

        except Exception as e:
            self.logger.error(f"AI服务初始化失败: {e}")
            raise

    async def close(self):
        """关闭AI服务"""
        if self.session:
            await self.session.close()
        self.is_initialized = False
        self.logger.info("AI服务已关闭")

    def is_available(self) -> bool:
        """检查AI服务是否可用"""
        return self.is_initialized and self.settings.api_key

    async def analyze_barrages(
        self,
        barrages: List[Dict[str, Any]],
        analysis_type: str = 'general'
    ) -> Dict[str, Any]:
        """
        分析弹幕内容（优化成本控制版本）

        Args:
            barrages: 弹幕列表
            analysis_type: 分析类型 (lottery, discount, game_highlight, product_launch, general)

        Returns:
            分析结果
        """
        if not self.is_available():
            return {
                'error': 'AI服务不可用',
                'is_triggered': False,
                'confidence': 0.0,
                'analysis_type': analysis_type
            }

        try:
            # 预处理弹幕
            processed_barrages = self._preprocess_barrages(barrages)

            # 检查弹幕密度，低密度直接返回
            if not self._check_barrage_density(processed_barrages):
                return {
                    'is_triggered': False,
                    'confidence': 0.0,
                    'method': 'density_check',
                    'reason': '弹幕密度不足，跳过AI分析',
                    'analysis_type': analysis_type
                }

            # 规则匹配分析
            rule_result = self._rule_based_analysis(processed_barrages, analysis_type)

            # 如果规则匹配置信度很高，直接返回（避免AI调用）
            if rule_result['confidence'] >= self.rule_confidence_threshold:
                self.logger.info(f"规则分析置信度高({rule_result['confidence']:.2f})，跳过AI调用")
                return rule_result

            # 检查是否满足AI调用条件
            if not self._should_call_ai(rule_result['confidence']):
                return {
                    'is_triggered': rule_result['is_triggered'],
                    'confidence': rule_result['confidence'],
                    'method': 'rule_only',
                    'reason': '规则置信度较低，但不符合AI调用条件',
                    'analysis_type': analysis_type
                }

            # 检查AI调用频率限制
            if not self._check_ai_call_frequency():
                return {
                    'is_triggered': rule_result['is_triggered'],
                    'confidence': rule_result['confidence'],
                    'method': 'rate_limited',
                    'reason': 'AI调用频率限制，使用规则结果',
                    'analysis_type': analysis_type
                }

            # 调用AI API进行深度分析（作为专家仲裁）
            ai_result = await self._call_ai_api(processed_barrages, analysis_type)

            # 合并结果
            final_result = self._merge_results(rule_result, ai_result)

            self.logger.info(
                f"AI分析完成 - 类型: {analysis_type}, "
                f"触发: {final_result['is_triggered']}, "
                f"置信度: {final_result['confidence']:.2f}, "
                f"方法: {final_result['method']}"
            )

            return final_result

        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            return {
                'error': str(e),
                'is_triggered': False,
                'confidence': 0.0,
                'analysis_type': analysis_type
            }

    def _preprocess_barrages(self, barrages: List[Dict[str, Any]]) -> List[str]:
        """预处理弹幕数据"""
        processed = []
        for barrage in barrages:
            content = barrage.get('content', '').strip()
            if content and len(content) > 1:  # 过滤空内容和单字
                processed.append(content)
        return processed

    def _rule_based_analysis(
        self,
        barrages: List[str],
        analysis_type: str
    ) -> Dict[str, Any]:
        """基于规则的初步分析"""
        if analysis_type not in self.keyword_dict:
            return {
                'is_triggered': False,
                'confidence': 0.0,
                'method': 'rule_based',
                'matched_keywords': [],
                'analysis_type': analysis_type
            }

        keywords = self.keyword_dict[analysis_type]
        matched_keywords = []
        match_count = 0

        # 分词并匹配关键词
        for barrage in barrages:
            words = jieba.lcut(barrage)
            for word in words:
                if word in keywords:
                    matched_keywords.append(word)
                    match_count += 1

        # 计算置信度
        unique_matches = len(set(matched_keywords))
        total_barrages = len(barrages)

        if match_count == 0:
            confidence = 0.0
        elif unique_matches >= 3 or match_count >= 5:
            confidence = min(0.9, 0.5 + (unique_matches * 0.1) + (match_count * 0.05))
        else:
            confidence = min(0.7, 0.3 + (unique_matches * 0.1) + (match_count * 0.02))

        return {
            'is_triggered': confidence > 0.5,
            'confidence': confidence,
            'method': 'rule_based',
            'matched_keywords': list(set(matched_keywords)),
            'match_count': match_count,
            'analysis_type': analysis_type
        }

    async def _call_ai_api(
        self,
        barrages: List[str],
        analysis_type: str
    ) -> Dict[str, Any]:
        """调用AI API进行分析"""
        try:
            # 准备消息
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompts.get(analysis_type, self.system_prompts['general'])
                },
                {
                    "role": "user",
                    "content": f"请分析以下弹幕：\n{chr(10).join(barrages[-10:])}"  # 取最近10条
                }
            ]

            # 调用AI API
            response = await self._make_api_call(messages)

            # 解析响应
            if response and 'choices' in response:
                content = response['choices'][0]['message']['content']
                return self._parse_ai_response(content, analysis_type)

            return {
                'is_triggered': False,
                'confidence': 0.0,
                'method': 'ai_api',
                'error': 'API响应格式错误',
                'analysis_type': analysis_type
            }

        except Exception as e:
            self.logger.error(f"AI API调用失败: {e}")
            return {
                'is_triggered': False,
                'confidence': 0.0,
                'method': 'ai_api',
                'error': str(e),
                'analysis_type': analysis_type
            }

    async def _make_api_call(self, messages: List[Dict]) -> Optional[Dict]:
        """执行API调用"""
        for attempt in range(self.settings.retry_count):
            try:
                response = await self.session.post(
                    f"{self.settings.api_base_url}/chat/completions",
                    json={
                        "model": self.settings.model_name,
                        "messages": messages,
                        "max_tokens": self.settings.max_tokens,
                        "temperature": self.settings.temperature
                    },
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    self.logger.warning(f"API调用失败 (尝试 {attempt + 1}): {response.status} - {error_text}")

            except Exception as e:
                self.logger.warning(f"API调用异常 (尝试 {attempt + 1}): {e}")

            # 重试延迟
            if attempt < self.settings.retry_count - 1:
                await asyncio.sleep(self.settings.retry_delay * (attempt + 1))

        return None

    def _parse_ai_response(self, content: str, analysis_type: str) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试解析JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_content = content[json_start:json_end]
                result = json.loads(json_content)

                # 标准化结果格式
                standardized = {
                    'is_triggered': False,
                    'confidence': 0.0,
                    'method': 'ai_api',
                    'reason': result.get('reason', ''),
                    'raw_response': content,
                    'analysis_type': analysis_type
                }

                # 根据分析类型提取结果
                if analysis_type == 'lottery':
                    standardized['is_triggered'] = result.get('is_lottery', False)
                    standardized['confidence'] = result.get('confidence', 0.0)
                elif analysis_type == 'discount':
                    standardized['is_triggered'] = result.get('is_discount', False)
                    standardized['confidence'] = result.get('confidence', 0.0)
                elif analysis_type == 'game_highlight':
                    standardized['is_triggered'] = result.get('is_highlight', False)
                    standardized['confidence'] = result.get('confidence', 0.0)
                elif analysis_type == 'product_launch':
                    standardized['is_triggered'] = result.get('is_product_launch', False)
                    standardized['confidence'] = result.get('confidence', 0.0)

                return standardized

            # 如果无法解析JSON，进行文本分析
            return self._fallback_text_analysis(content, analysis_type)

        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            return self._fallback_text_analysis(content, analysis_type)

    def _fallback_text_analysis(self, content: str, analysis_type: str) -> Dict[str, Any]:
        """备用的文本分析方法"""
        content_lower = content.lower()

        # 简单的关键词匹配
        positive_indicators = ['true', '是', '有', '正在', '确实', '确认']
        negative_indicators = ['false', '否', '没有', '不是', '无']

        has_positive = any(indicator in content_lower for indicator in positive_indicators)
        has_negative = any(indicator in content_lower for indicator in negative_indicators)

        if has_positive and not has_negative:
            confidence = 0.6
            is_triggered = True
        elif has_negative and not has_positive:
            confidence = 0.6
            is_triggered = False
        else:
            confidence = 0.3
            is_triggered = has_positive

        return {
            'is_triggered': is_triggered,
            'confidence': confidence,
            'method': 'fallback_text',
            'reason': content[:200],  # 截取部分内容作为理由
            'raw_response': content,
            'analysis_type': analysis_type
        }

    def _merge_results(
        self,
        rule_result: Dict[str, Any],
        ai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并规则和AI分析结果"""
        # 如果任一方置信度很高，采用高置信度结果
        if rule_result['confidence'] > 0.85:
            return rule_result
        if ai_result['confidence'] > 0.85:
            return ai_result

        # 如果结果一致，提高置信度
        if rule_result['is_triggered'] == ai_result['is_triggered']:
            merged_confidence = (rule_result['confidence'] + ai_result['confidence']) / 2
            return {
                **rule_result,
                'confidence': min(0.95, merged_confidence + 0.1),
                'method': 'merged_agreement'
            }

        # 结果不一致时，采用AI结果但降低置信度
        return {
            **ai_result,
            'confidence': ai_result['confidence'] * 0.8,
            'method': 'merged_ai_preferred',
            'rule_based_result': rule_result
        }

    def _check_barrage_density(self, barrages: List[str]) -> bool:
        """检查弹幕密度是否达到AI分析阈值"""
        return len(barrages) >= self.min_density_threshold

    def _should_call_ai(self, rule_confidence: float) -> bool:
        """判断是否应该调用AI API"""
        # 只有当规则置信度处于模糊区间时才调用AI
        return self.ai_confidence_threshold <= rule_confidence < self.rule_confidence_threshold

    def _check_ai_call_frequency(self) -> bool:
        """检查AI调用频率限制"""
        current_time = time.time()
        if current_time - self.last_ai_call_time < self.ai_call_interval:
            return False
        self.last_ai_call_time = current_time
        return True

    def reinitialize(self):
        """重新初始化服务"""
        self.logger.info("重新初始化AI服务")
        asyncio.create_task(self.close())
        time.sleep(1)  # 等待关闭完成
        self.initialize()

    async def get_analysis_stats(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return {
            'is_available': self.is_available(),
            'api_base_url': self.settings.api_base_url,
            'model_name': self.settings.model_name,
            'supported_types': list(self.system_prompts.keys()),
            'keyword_categories': list(self.keyword_dict.keys())
        }