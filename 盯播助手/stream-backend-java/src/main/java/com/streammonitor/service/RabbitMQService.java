package com.streammonitor.service;

import java.util.Map;

/**
 * RabbitMQ消息队列服务接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface RabbitMQService {

    /**
     * 发送消息到爬虫队列
     *
     * @param message 消息内容
     */
    void sendToCrawlerQueue(Map<String, Object> message);

    /**
     * 发送通知消息
     *
     * @param message 消息内容
     */
    void sendNotificationMessage(Map<String, Object> message);

    /**
     * 发送AI分析请求
     *
     * @param message 消息内容
     */
    void sendAIAnalysisRequest(Map<String, Object> message);

    /**
     * 发送弹幕数据到分析队列
     *
     * @param message 消息内容
     */
    void sendBarrageToAnalysisQueue(Map<String, Object> message);

    /**
     * 发送心跳消息
     *
     * @param message 消息内容
     */
    void sendHeartbeatMessage(Map<String, Object> message);
}