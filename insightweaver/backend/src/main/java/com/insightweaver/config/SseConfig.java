package com.insightweaver.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Configuration for Server-Sent Events (SSE) functionality
 */
@Configuration
public class SseConfig {

    /**
     * Thread pool for handling SSE connections
     */
    @Bean
    public ExecutorService sseExecutorService() {
        return Executors.newFixedThreadPool(100);
    }

    /**
     * Concurrent map to store active SSE emitters by task ID
     */
    @Bean
    public ConcurrentHashMap<String, SseEmitter> activeEmitters() {
        return new ConcurrentHashMap<>();
    }
}