package com.streammonitor.service.impl;

import com.alibaba.fastjson2.JSONObject;
import com.streammonitor.service.RabbitMQService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * RabbitMQ消息队列服务实现类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class RabbitMQServiceImpl implements RabbitMQService {

    private final RabbitTemplate rabbitTemplate;

    // 队列名称常量
    private static final String CRAWLER_QUEUE = "stream.crawler.queue";
    private static final String NOTIFICATION_QUEUE = "stream.notification.queue";
    private static final String AI_ANALYSIS_QUEUE = "stream.ai.analysis.queue";
    private static final String BARRAGE_ANALYSIS_QUEUE = "stream.barrage.analysis.queue";
    private static final String HEARTBEAT_QUEUE = "stream.heartbeat.queue";

    @Override
    public void sendToCrawlerQueue(Map<String, Object> message) {
        try {
            log.info("发送消息到爬虫队列: {}", message);
            String messageJson = JSONObject.toJSONString(message);
            rabbitTemplate.convertAndSend(CRAWLER_QUEUE, messageJson);
            log.info("消息发送成功到爬虫队列");
        } catch (Exception e) {
            log.error("发送消息到爬虫队列失败", e);
            throw new RuntimeException("发送消息到爬虫队列失败", e);
        }
    }

    @Override
    public void sendNotificationMessage(Map<String, Object> message) {
        try {
            log.info("发送通知消息: {}", message);
            String messageJson = JSONObject.toJSONString(message);
            rabbitTemplate.convertAndSend(NOTIFICATION_QUEUE, messageJson);
            log.info("通知消息发送成功");
        } catch (Exception e) {
            log.error("发送通知消息失败", e);
            throw new RuntimeException("发送通知消息失败", e);
        }
    }

    @Override
    public void sendAIAnalysisRequest(Map<String, Object> message) {
        try {
            log.info("发送AI分析请求: {}", message);
            String messageJson = JSONObject.toJSONString(message);
            rabbitTemplate.convertAndSend(AI_ANALYSIS_QUEUE, messageJson);
            log.info("AI分析请求发送成功");
        } catch (Exception e) {
            log.error("发送AI分析请求失败", e);
            throw new RuntimeException("发送AI分析请求失败", e);
        }
    }

    @Override
    public void sendBarrageToAnalysisQueue(Map<String, Object> message) {
        try {
            log.debug("发送弹幕数据到分析队列: {}", message);
            String messageJson = JSONObject.toJSONString(message);
            rabbitTemplate.convertAndSend(BARRAGE_ANALYSIS_QUEUE, messageJson);
            log.debug("弹幕数据发送成功到分析队列");
        } catch (Exception e) {
            log.error("发送弹幕数据到分析队列失败", e);
            throw new RuntimeException("发送弹幕数据到分析队列失败", e);
        }
    }

    @Override
    public void sendHeartbeatMessage(Map<String, Object> message) {
        try {
            log.debug("发送心跳消息: {}", message);
            String messageJson = JSONObject.toJSONString(message);
            rabbitTemplate.convertAndSend(HEARTBEAT_QUEUE, messageJson);
            log.debug("心跳消息发送成功");
        } catch (Exception e) {
            log.error("发送心跳消息失败", e);
            throw new RuntimeException("发送心跳消息失败", e);
        }
    }
}