package com.streammonitor.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ配置类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Configuration
public class RabbitMQConfig {

    // 队列名称
    public static final String CRAWLER_QUEUE = "stream.crawler.queue";
    public static final String NOTIFICATION_QUEUE = "stream.notification.queue";
    public static final String AI_ANALYSIS_QUEUE = "stream.ai.analysis.queue";
    public static final String BARRAGE_ANALYSIS_QUEUE = "stream.barrage.analysis.queue";
    public static final String HEARTBEAT_QUEUE = "stream.heartbeat.queue";

    // 交换机名称
    public static final String STREAM_EXCHANGE = "stream.monitor.exchange";

    // 路由键
    public static final String CRAWLER_ROUTING_KEY = "stream.crawler";
    public static final String NOTIFICATION_ROUTING_KEY = "stream.notification";
    public static final String AI_ANALYSIS_ROUTING_KEY = "stream.ai.analysis";
    public static final String BARRAGE_ANALYSIS_ROUTING_KEY = "stream.barrage.analysis";
    public static final String HEARTBEAT_ROUTING_KEY = "stream.heartbeat";

    /**
     * 创建主题交换机
     */
    @Bean
    public TopicExchange streamExchange() {
        return new TopicExchange(STREAM_EXCHANGE, true, false);
    }

    /**
     * 爬虫任务队列
     */
    @Bean
    public Queue crawlerQueue() {
        return QueueBuilder.durable(CRAWLER_QUEUE)
                .withArgument("x-message-ttl", 24 * 60 * 60 * 1000) // 24小时TTL
                .withArgument("x-max-length", 10000) // 最大消息数
                .build();
    }

    /**
     * 通知队列
     */
    @Bean
    public Queue notificationQueue() {
        return QueueBuilder.durable(NOTIFICATION_QUEUE)
                .withArgument("x-message-ttl", 24 * 60 * 60 * 1000)
                .withArgument("x-max-length", 5000)
                .build();
    }

    /**
     * AI分析队列
     */
    @Bean
    public Queue aiAnalysisQueue() {
        return QueueBuilder.durable(AI_ANALYSIS_QUEUE)
                .withArgument("x-message-ttl", 30 * 60 * 1000) // 30分钟TTL
                .withArgument("x-max-length", 2000)
                .build();
    }

    /**
     * 弹幕分析队列
     */
    @Bean
    public Queue barrageAnalysisQueue() {
        return QueueBuilder.durable(BARRAGE_ANALYSIS_QUEUE)
                .withArgument("x-message-ttl", 10 * 60 * 1000) // 10分钟TTL
                .withArgument("x-max-length", 10000)
                .build();
    }

    /**
     * 心跳队列
     */
    @Bean
    public Queue heartbeatQueue() {
        return QueueBuilder.durable(HEARTBEAT_QUEUE)
                .withArgument("x-message-ttl", 5 * 60 * 1000) // 5分钟TTL
                .build();
    }

    /**
     * 绑定爬虫队列
     */
    @Bean
    public Binding crawlerBinding() {
        return BindingBuilder.bind(crawlerQueue())
                .to(streamExchange())
                .with(CRAWLER_ROUTING_KEY);
    }

    /**
     * 绑定通知队列
     */
    @Bean
    public Binding notificationBinding() {
        return BindingBuilder.bind(notificationQueue())
                .to(streamExchange())
                .with(NOTIFICATION_ROUTING_KEY);
    }

    /**
     * 绑定AI分析队列
     */
    @Bean
    public Binding aiAnalysisBinding() {
        return BindingBuilder.bind(aiAnalysisQueue())
                .to(streamExchange())
                .with(AI_ANALYSIS_ROUTING_KEY);
    }

    /**
     * 绑定弹幕分析队列
     */
    @Bean
    public Binding barrageAnalysisBinding() {
        return BindingBuilder.bind(barrageAnalysisQueue())
                .to(streamExchange())
                .with(BARRAGE_ANALYSIS_ROUTING_KEY);
    }

    /**
     * 绑定心跳队列
     */
    @Bean
    public Binding heartbeatBinding() {
        return BindingBuilder.bind(heartbeatQueue())
                .to(streamExchange())
                .with(HEARTBEAT_ROUTING_KEY);
    }

    /**
     * 配置消息转换器
     */
    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    /**
     * 配置RabbitTemplate
     */
    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        template.setExchange(STREAM_EXCHANGE);
        template.setRoutingKey(CRAWLER_ROUTING_KEY);
        return template;
    }
}