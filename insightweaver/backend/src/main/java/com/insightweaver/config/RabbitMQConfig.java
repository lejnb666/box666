package com.insightweaver.config;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.rabbit.listener.MessageListenerContainer;
import org.springframework.amqp.rabbit.listener.SimpleMessageListenerContainer;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * RabbitMQ configuration for task queue management
 */
@Configuration
public class RabbitMQConfig {

    @Value("${insightweaver.queue.research-task-queue:research.tasks}")
    private String researchTaskQueue;

    @Value("${insightweaver.queue.agent-response-queue:agent.responses}")
    private String agentResponseQueue;

    @Value("${insightweaver.queue.notification-queue:notifications}")
    private String notificationQueue;

    @Bean
    public Queue researchTaskQueue() {
        return new Queue(researchTaskQueue, true, false, false);
    }

    @Bean
    public Queue agentResponseQueue() {
        return new Queue(agentResponseQueue, true, false, false);
    }

    @Bean
    public Queue notificationQueue() {
        return new Queue(notificationQueue, true, false, false);
    }

    @Bean
    public TopicExchange insightWeaverExchange() {
        return new TopicExchange("insightweaver.exchange");
    }

    @Bean
    public Binding researchTaskBinding() {
        return BindingBuilder.bind(researchTaskQueue())
                .to(insightWeaverExchange())
                .with("research.task.*");
    }

    @Bean
    public Binding agentResponseBinding() {
        return BindingBuilder.bind(agentResponseQueue())
                .to(insightWeaverExchange())
                .with("agent.response.*");
    }

    @Bean
    public Binding notificationBinding() {
        return BindingBuilder.bind(notificationQueue())
                .to(insightWeaverExchange())
                .with("notification.*");
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public RabbitTemplate rabbitTemplate(ConnectionFactory connectionFactory) {
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMessageConverter(jsonMessageConverter());
        return template;
    }

    @Bean
    public MessageListenerContainer messageListenerContainer(ConnectionFactory connectionFactory) {
        SimpleMessageListenerContainer container = new SimpleMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.setQueueNames(researchTaskQueue, agentResponseQueue, notificationQueue);
        container.setConcurrentConsumers(10);  // Increased from 3 to 10 for better parallelization
        container.setMaxConcurrentConsumers(20);  // Increased from 10 to 20 for peak loads
        container.setPrefetchCount(50);  // Increase prefetch for better throughput
        container.setTxSize(10);  // Process in batches of 10 for efficiency
        return container;
    }

    @Bean
    public MessageListenerContainer researchTaskListenerContainer(ConnectionFactory connectionFactory) {
        SimpleMessageListenerContainer container = new SimpleMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.setQueueNames(researchTaskQueue);
        container.setConcurrentConsumers(15);  // Higher concurrency for research tasks
        container.setMaxConcurrentConsumers(30);
        container.setPrefetchCount(20);
        container.setTxSize(5);
        return container;
    }
}