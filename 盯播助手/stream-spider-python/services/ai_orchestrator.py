#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Agent 工作流编排器 - 实现双层AI过滤机制的协调和成本控制

@author: exbox0403-cmd
@since: 2026/4/8
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

from services.local_filter import LocalFilterService
from services.ai_service import AIService


class EventType(Enum):
    """事件类型枚举"""
    PRODUCT_LAUNCH = "product_launch"
    LOTTERY = "lottery"
    DISCOUNT = "discount"
    GAME_HIGHLIGHT = "game_highlight"
    LIVE_START = "live_start"
    LIVE_END = "live_end"
    UNKNOWN = "unknown"


@dataclass
class AnalysisRequest:
    """分析请求数据类"""
    request_id: str
    platform: str
    room_id: str
    event_type: EventType
    trigger_reason: str
    barrages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    created_at: float
    priority: int = 1  # 优先级：1-普通，2-高，3-紧急


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    request_id: str
    is_triggered: bool
    confidence: float
    event_type: EventType
    analysis_method: str  # 'local_filter', 'ai_shallow', 'ai_deep'
    reasoning: str
    extracted_info: Dict[str, Any]
    cost_info: Dict[str, Any]
    processing_time: float
    created_at: float


class AICostController:
    """AI调用成本控制器"""

    def __init__(self):
        # 成本限制配置
        self.daily_budget = 100.0  # 每日预算（美元）
        self.request_limit = 1000  # 每日请求限制
        self.token_limit = 100000  # 每日token限制

        # 当前使用统计
        self.daily_cost = 0.0
        self.daily_requests = 0
        self.daily_tokens = 0
        self.last_reset = time.time()

        # 模型定价（美元/1K tokens）
        self.model_pricing = {
            'deepseek-chat': 0.002,  # DeepSeek Chat
            'deepseek-coder': 0.002,  # DeepSeek Coder
            'gpt-3.5-turbo': 0.0015,  # OpenAI GPT-3.5
            'gpt-4': 0.03  # OpenAI GPT-4
        }

    def check_budget(self, model: str, estimated_tokens: int) -> Tuple[bool, str]:
        """检查预算是否允许调用"""
        # 每日重置检查
        self._check_daily_reset()

        # 计算预估成本
        price_per_k = self.model_pricing.get(model, 0.002)
        estimated_cost = (estimated_tokens / 1000) * price_per_k

        # 检查各项限制
        if self.daily_cost + estimated_cost > self.daily_budget:
            return False, f"超出每日预算限制 (${self.daily_budget})"

        if self.daily_requests >= self.request_limit:
            return False, f"超出每日请求限制 ({self.request_limit})"

        if self.daily_tokens + estimated_tokens > self.token_limit:
            return False, f"超出每日token限制 ({self.token_limit})"

        return True, "预算充足"

    def record_usage(self, model: str, tokens_used: int):
        """记录使用情况"""
        price_per_k = self.model_pricing.get(model, 0.002)
        cost = (tokens_used / 1000) * price_per_k

        self.daily_cost += cost
        self.daily_requests += 1
        self.daily_tokens += tokens_used

        logger.info(f"AI调用成本记录 - 模型: {model}, Tokens: {tokens_used}, 成本: ${cost:.4f}")

    def _check_daily_reset(self):
        """检查是否需要每日重置"""
        current_time = time.time()
        if current_time - self.last_reset >= 86400:  # 24小时
            self.daily_cost = 0.0
            self.daily_requests = 0
            self.daily_tokens = 0
            self.last_reset = current_time
            logger.info("AI成本统计已重置")

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用情况统计"""
        return {
            'daily_cost': self.daily_cost,
            'daily_budget': self.daily_budget,
            'cost_usage_rate': self.daily_cost / self.daily_budget,
            'daily_requests': self.daily_requests,
            'request_limit': self.request_limit,
            'request_usage_rate': self.daily_requests / self.request_limit,
            'daily_tokens': self.daily_tokens,
            'token_limit': self.token_limit,
            'token_usage_rate': self.daily_tokens / self.token_limit,
            'remaining_budget': self.daily_budget - self.daily_cost,
            'remaining_requests': self.request_limit - self.daily_requests,
            'remaining_tokens': self.token_limit - self.daily_tokens
        }


class DeepSeekClient:
    """DeepSeek API客户端"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = 30

    async def analyze_with_deepseek(
        self,
        barrages: List[str],
        event_type: EventType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用DeepSeek进行深度分析"""
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt(event_type)

            # 构建用户提示词
            user_prompt = self._build_user_prompt(barrages, event_type, context)

            # 调用DeepSeek API
            response = await self._call_api(system_prompt, user_prompt)

            # 解析响应
            result = self._parse_response(response, event_type)

            return result

        except Exception as e:
            logger.error(f"DeepSeek分析失败: {e}")
            return {
                'is_triggered': False,
                'confidence': 0.0,
                'reasoning': f"API调用失败: {e}",
                'error': True
            }

    def _build_system_prompt(self, event_type: EventType) -> str:
        """构建系统提示词"""
        prompts = {
            EventType.PRODUCT_LAUNCH: (
                "你是一个专业的直播带货分析师，擅长从弹幕中识别商品上架的关键时刻。"
                "你需要分析连续的弹幕内容，判断主播是否正在上架新商品或进行促销。"
                "重点关注：商品介绍、价格公布、购买链接、库存信息、优惠信息等。"
                "返回JSON格式：{'is_triggered': bool, 'confidence': float, 'reasoning': str, 'product_info': dict}"
            ),
            EventType.LOTTERY: (
                "你是一个专业的直播活动分析师，擅长识别抽奖和福利活动。"
                "你需要分析连续的弹幕内容，判断主播是否正在进行抽奖活动。"
                "重点关注：抽奖规则、参与方式、奖品信息、中奖公布等。"
                "返回JSON格式：{'is_triggered': bool, 'confidence': float, 'reasoning': str, 'lottery_info': dict}"
            ),
            EventType.DISCOUNT: (
                "你是一个专业的价格分析师，擅长识别降价促销信息。"
                "你需要分析连续的弹幕内容，判断是否出现大额降价或特殊优惠。"
                "重点关注：价格变化、优惠幅度、限时信息、库存紧张等。"
                "返回JSON格式：{'is_triggered': bool, 'confidence': float, 'reasoning': str, 'discount_info': dict}"
            ),
            EventType.GAME_HIGHLIGHT: (
                "你是一个专业的电竞赛事分析师，擅长识别比赛关键时刻。"
                "你需要分析连续的弹幕内容，判断是否处于比赛高潮或重要时刻。"
                "重点关注：精彩操作、团战爆发、胜负关键、观众情绪等。"
                "返回JSON格式：{'is_triggered': bool, 'confidence': float, 'reasoning': str, 'highlight_info': dict}"
            )
        }

        return prompts.get(event_type, prompts[EventType.PRODUCT_LAUNCH])

    def _build_user_prompt(self, barrages: List[str], event_type: EventType, context: Dict[str, Any]) -> str:
        """构建用户提示词"""
        # 限制弹幕数量，避免token超限
        limited_barrages = barrages[-15:] if len(barrages) > 15 else barrages

        prompt = f"请分析以下直播弹幕，判断是否出现{event_type.value}相关事件：\n\n"

        # 添加上下文信息
        if context.get('streamer_name'):
            prompt += f"主播：{context['streamer_name']}\n"
        if context.get('room_title'):
            prompt += f"房间标题：{context['room_title']}\n"
        if context.get('category'):
            prompt += f"直播分类：{context['category']}\n"

        prompt += f"\n弹幕内容（按时间顺序）：\n"
        for i, barrage in enumerate(limited_barrages, 1):
            prompt += f"{i}. {barrage}\n"

        prompt += f"\n请基于以上信息进行分析和判断。"

        return prompt

    async def _call_api(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """调用DeepSeek API"""
        try:
            import aiohttp

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 1000
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API调用失败: {response.status} - {error_text}")
                        return None

        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return None

    def _parse_response(self, response: Dict[str, Any], event_type: EventType) -> Dict[str, Any]:
        """解析API响应"""
        try:
            if not response or 'choices' not in response:
                return {
                    'is_triggered': False,
                    'confidence': 0.0,
                    'reasoning': 'API响应格式错误',
                    'error': True
                }

            content = response['choices'][0]['message']['content']

            # 尝试解析JSON
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1

                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)

                    return {
                        'is_triggered': result.get('is_triggered', False),
                        'confidence': result.get('confidence', 0.0),
                        'reasoning': result.get('reasoning', ''),
                        'extracted_info': {
                            k: v for k, v in result.items()
                            if k not in ['is_triggered', 'confidence', 'reasoning']
                        },
                        'error': False
                    }

            except json.JSONDecodeError:
                pass

            # 如果JSON解析失败，进行文本分析
            return self._fallback_text_analysis(content, event_type)

        except Exception as e:
            logger.error(f"解析DeepSeek响应失败: {e}")
            return {
                'is_triggered': False,
                'confidence': 0.0,
                'reasoning': f'响应解析失败: {e}',
                'error': True
            }

    def _fallback_text_analysis(self, content: str, event_type: EventType) -> Dict[str, Any]:
        """备用的文本分析方法"""
        content_lower = content.lower()

        # 简单的关键词匹配
        positive_indicators = ['是', '有', '正在', '确实', '确认', '确定']
        negative_indicators = ['不是', '没有', '无', '否', '未']

        has_positive = any(indicator in content_lower for indicator in positive_indicators)
        has_negative = any(indicator in content_lower for indicator in negative_indicators)

        if has_positive and not has_negative:
            confidence = 0.7
            is_triggered = True
        elif has_negative and not has_positive:
            confidence = 0.7
            is_triggered = False
        else:
            confidence = 0.4
            is_triggered = has_positive

        return {
            'is_triggered': is_triggered,
            'confidence': confidence,
            'reasoning': content[:300],  # 截取部分内容
            'extracted_info': {},
            'error': False
        }


class AIOrchestrator:
    """AI Agent工作流编排器"""

    def __init__(self, ai_service: AIService, deepseek_api_key: Optional[str] = None):
        self.ai_service = ai_service
        self.local_filter = LocalFilterService()
        self.cost_controller = AICostController()

        # 初始化DeepSeek客户端
        self.deepseek_client = None
        if deepseek_api_key:
            self.deepseek_client = DeepSeekClient(deepseek_api_key)

        # 请求队列
        self.pending_requests: List[AnalysisRequest] = []
        self.processing_requests: Dict[str, AnalysisRequest] = {}
        self.completed_results: Dict[str, AnalysisResult] = {}

        # 工作流配置
        self.max_queue_size = 100
        self.processing_timeout = 300  # 5分钟超时
        self.result_retention = 3600  # 1小时保留

        # 性能统计
        self.stats = {
            'total_requests': 0,
            'local_filtered': 0,
            'ai_shallow_calls': 0,
            'ai_deep_calls': 0,
            'cost_saved': 0.0,
            'average_processing_time': 0.0
        }

        logger.info("AI Agent工作流编排器初始化完成")

    async def submit_analysis_request(
        self,
        platform: str,
        room_id: str,
        event_type: EventType,
        trigger_reason: str,
        barrages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 1
    ) -> str:
        """提交分析请求"""
        request_id = str(uuid.uuid4())

        request = AnalysisRequest(
            request_id=request_id,
            platform=platform,
            room_id=room_id,
            event_type=event_type,
            trigger_reason=trigger_reason,
            barrages=barrages,
            metadata=metadata or {},
            created_at=time.time(),
            priority=priority
        )

        # 检查队列大小
        if len(self.pending_requests) >= self.max_queue_size:
            # 移除最旧的请求
            removed = self.pending_requests.pop(0)
            logger.warning(f"队列已满，移除请求: {removed.request_id}")

        # 按优先级插入队列
        self._insert_by_priority(request)

        self.stats['total_requests'] += 1
        logger.info(f"分析请求已提交: {request_id}, 优先级: {priority}")

        return request_id

    async def process_next_request(self) -> Optional[str]:
        """处理下一个请求"""
        if not self.pending_requests:
            return None

        request = self.pending_requests.pop(0)
        self.processing_requests[request.request_id] = request

        try:
            start_time = time.time()

            # 执行双层AI分析
            result = await self._execute_analysis_workflow(request)

            processing_time = time.time() - start_time
            result.processing_time = processing_time

            # 保存结果
            self.completed_results[request.request_id] = result

            # 更新统计
            self._update_stats(result, processing_time)

            logger.info(
                f"分析完成: {request.request_id}, "
                f"触发: {result.is_triggered}, "
                f"方法: {result.analysis_method}, "
                f"耗时: {processing_time:.2f}s"
            )

            return request.request_id

        except Exception as e:
            logger.error(f"处理请求失败 {request.request_id}: {e}")
            return None

        finally:
            # 清理处理中的请求
            if request.request_id in self.processing_requests:
                del self.processing_requests[request.request_id]

    async def _execute_analysis_workflow(self, request: AnalysisRequest) -> AnalysisResult:
        """执行双层AI分析工作流"""
        # 第一步：本地浅层过滤
        should_trigger, reason, info = self.local_filter.should_trigger_ai_analysis(
            request.platform, request.room_id
        )

        if not should_trigger:
            self.stats['local_filtered'] += 1
            return AnalysisResult(
                request_id=request.request_id,
                is_triggered=False,
                confidence=0.0,
                event_type=request.event_type,
                analysis_method='local_filter',
                reasoning=reason,
                extracted_info=info,
                cost_info={'cost': 0.0, 'method': 'local_only'},
                processing_time=0.0,
                created_at=time.time()
            )

        # 第二步：获取过滤后的弹幕
        filtered_barrages = self.local_filter.get_filtered_barrages(
            request.platform, request.room_id, limit=30
        )

        if not filtered_barrages:
            return AnalysisResult(
                request_id=request.request_id,
                is_triggered=False,
                confidence=0.0,
                event_type=request.event_type,
                analysis_method='local_filter',
                reasoning='过滤后无有效弹幕',
                extracted_info={},
                cost_info={'cost': 0.0, 'method': 'local_only'},
                processing_time=0.0,
                created_at=time.time()
            )

        # 第三步：AI浅层分析（低成本模型）
        shallow_result = await self.ai_service.analyze_barrages(
            filtered_barrages,
            request.event_type.value
        )

        # 如果浅层分析置信度很高，直接返回
        if shallow_result.get('confidence', 0) > 0.8:
            self.stats['ai_shallow_calls'] += 1
            return AnalysisResult(
                request_id=request.request_id,
                is_triggered=shallow_result.get('is_triggered', False),
                confidence=shallow_result.get('confidence', 0.0),
                event_type=request.event_type,
                analysis_method='ai_shallow',
                reasoning=shallow_result.get('reason', ''),
                extracted_info=shallow_result.get('extracted_info', {}),
                cost_info={'cost': 0.01, 'method': 'shallow_ai'},
                processing_time=0.0,
                created_at=time.time()
            )

        # 第四步：AI深层仲裁（DeepSeek）
        if self.deepseek_client and shallow_result.get('confidence', 0) > 0.3:
            # 检查成本预算
            estimated_tokens = len(str(filtered_barrages)) // 4  # 粗略估算
            budget_ok, budget_msg = self.cost_controller.check_budget('deepseek-chat', estimated_tokens)

            if budget_ok:
                deep_result = await self.deepseek_client.analyze_with_deepseek(
                    [b.get('content', '') for b in filtered_barrages],
                    request.event_type,
                    {
                        'platform': request.platform,
                        'room_id': request.room_id,
                        **request.metadata
                    }
                )

                # 记录使用情况
                actual_tokens = estimated_tokens + 500  # 加上系统提示词
                self.cost_controller.record_usage('deepseek-chat', actual_tokens)

                self.stats['ai_deep_calls'] += 1

                return AnalysisResult(
                    request_id=request.request_id,
                    is_triggered=deep_result.get('is_triggered', False),
                    confidence=deep_result.get('confidence', 0.0),
                    event_type=request.event_type,
                    analysis_method='ai_deep',
                    reasoning=deep_result.get('reasoning', ''),
                    extracted_info=deep_result.get('extracted_info', {}),
                    cost_info={'cost': 0.05, 'method': 'deep_ai'},
                    processing_time=0.0,
                    created_at=time.time()
                )

            else:
                logger.warning(f"预算不足，跳过DeepSeek分析: {budget_msg}")

        # 如果无法进行深层分析，返回浅层结果
        return AnalysisResult(
            request_id=request.request_id,
            is_triggered=shallow_result.get('is_triggered', False),
            confidence=shallow_result.get('confidence', 0.0),
            event_type=request.event_type,
            analysis_method='ai_shallow',
            reasoning=f"{shallow_result.get('reason', '')} (预算不足，跳过深层分析)",
            extracted_info=shallow_result.get('extracted_info', {}),
            cost_info={'cost': 0.01, 'method': 'shallow_ai_only'},
            processing_time=0.0,
            created_at=time.time()
        )

    def _insert_by_priority(self, request: AnalysisRequest):
        """按优先级插入请求队列"""
        # 高优先级插入到前面
        if request.priority >= 3:
            self.pending_requests.insert(0, request)
        elif request.priority >= 2:
            # 中优先级插入到前1/3位置
            insert_pos = len(self.pending_requests) // 3
            self.pending_requests.insert(insert_pos, request)
        else:
            # 普通优先级插入到末尾
            self.pending_requests.append(request)

    def _update_stats(self, result: AnalysisResult, processing_time: float):
        """更新统计信息"""
        if result.analysis_method == 'local_filter':
            self.stats['cost_saved'] += 0.05  # 估算节省的成本

        # 更新平均处理时间
        total_requests = self.stats['total_requests']
        current_avg = self.stats['average_processing_time']
        self.stats['average_processing_time'] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )

    async def get_result(self, request_id: str) -> Optional[AnalysisResult]:
        """获取分析结果"""
        return self.completed_results.get(request_id)

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'pending_requests': len(self.pending_requests),
            'processing_requests': len(self.processing_requests),
            'completed_results': len(self.completed_results),
            'queue_full': len(self.pending_requests) >= self.max_queue_size
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        cost_stats = self.cost_controller.get_usage_stats()

        return {
            **self.stats,
            'cost_control': cost_stats,
            'efficiency': {
                'local_filter_rate': self.stats['local_filtered'] / max(1, self.stats['total_requests']),
                'ai_call_rate': (self.stats['ai_shallow_calls'] + self.stats['ai_deep_calls']) / max(1, self.stats['total_requests']),
                'cost_per_request': cost_stats['daily_cost'] / max(1, self.stats['total_requests'])
            }
        }

    async def cleanup_expired_data(self):
        """清理过期数据"""
        current_time = time.time()

        # 清理过期的处理中请求
        expired_processing = []
        for request_id, request in self.processing_requests.items():
            if current_time - request.created_at > self.processing_timeout:
                expired_processing.append(request_id)

        for request_id in expired_processing:
            del self.processing_requests[request_id]

        # 清理过期的结果
        expired_results = []
        for request_id, result in self.completed_results.items():
            if current_time - result.created_at > self.result_retention:
                expired_results.append(request_id)

        for request_id in expired_results:
            del self.completed_results[request_id]

        # 清理本地过滤器的过期数据
        await self.local_filter.cleanup_expired_data()

        logger.info(f"清理完成 - 处理中请求: {len(expired_processing)}, 结果: {len(expired_results)}")


# 使用示例
async def main():
    """测试AI编排器"""
    # 这里需要实际的AI服务和DeepSeek API密钥
    # orchestrator = AIOrchestrator(ai_service, "your-deepseek-api-key")
    pass


if __name__ == '__main__':
    asyncio.run(main())
