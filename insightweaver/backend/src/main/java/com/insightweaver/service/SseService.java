package com.insightweaver.service;

import com.insightweaver.dto.ResearchResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;

/**
 * Service for managing Server-Sent Events (SSE) connections and real-time updates
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class SseService implements MessageListener {

    private final RedisTemplate<String, Object> redisTemplate;
    private final ExecutorService sseExecutorService;
    private final Map<String, SseEmitter> activeEmitters = new ConcurrentHashMap<>();

    private static final String AGENT_STATUS_CHANNEL = "agent_status_updates";
    private static final String WORKFLOW_STATUS_CHANNEL = "workflow_status_updates";
    private static final long SSE_TIMEOUT = 300_000L; // 5 minutes
    private static final long HEARTBEAT_INTERVAL = 30_000L; // 30 seconds

    /**
     * Create a new SSE emitter for real-time task updates
     */
    public SseEmitter createTaskEmitter(String taskId, String userId) {
        log.info("Creating SSE emitter for task: {} user: {}", taskId, userId);

        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);

        // Store emitter for later use
        String emitterKey = getEmitterKey(taskId, userId);
        activeEmitters.put(emitterKey, emitter);

        // Set up emitter callbacks
        emitter.onCompletion(() -> {
            log.info("SSE emitter completed for task: {}", taskId);
            activeEmitters.remove(emitterKey);
        });

        emitter.onTimeout(() -> {
            log.info("SSE emitter timed out for task: {}", taskId);
            activeEmitters.remove(emitterKey);
        });

        emitter.onError((ex) -> {
            log.error("SSE emitter error for task: {}", taskId, ex);
            activeEmitters.remove(emitterKey);
        });

        // Send initial connection event
        try {
            emitter.send(SseEmitter.event()
                    .name("connection")
                    .data(Map.of(
                            "status", "connected",
                            "taskId", taskId,
                            "timestamp", LocalDateTime.now().toString()
                    )));
        } catch (IOException e) {
            log.error("Failed to send initial SSE event for task: {}", taskId, e);
            activeEmitters.remove(emitterKey);
            throw new RuntimeException("Failed to establish SSE connection", e);
        }

        return emitter;
    }

    /**
     * Send real-time update to specific task emitter
     */
    public void sendTaskUpdate(String taskId, String userId, ResearchResponse update) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.get(emitterKey);

        if (emitter != null) {
            sseExecutorService.submit(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name("task_update")
                            .data(update));
                } catch (IOException e) {
                    log.error("Failed to send task update for task: {}", taskId, e);
                    activeEmitters.remove(emitterKey);
                }
            });
        }
    }

    /**
     * Send agent status update
     */
    public void sendAgentStatusUpdate(String taskId, String userId, Map<String, Object> agentStatus) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.get(emitterKey);

        if (emitter != null) {
            sseExecutorService.submit(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name("agent_update")
                            .data(agentStatus));
                } catch (IOException e) {
                    log.error("Failed to send agent update for task: {}", taskId, e);
                    activeEmitters.remove(emitterKey);
                }
            });
        }
    }

    /**
     * Send progress update
     */
    public void sendProgressUpdate(String taskId, String userId, Map<String, Object> progress) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.get(emitterKey);

        if (emitter != null) {
            sseExecutorService.submit(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name("progress_update")
                            .data(progress));
                } catch (IOException e) {
                    log.error("Failed to send progress update for task: {}", taskId, e);
                    activeEmitters.remove(emitterKey);
                }
            });
        }
    }

    /**
     * Send task completion event
     */
    public void sendTaskCompletion(String taskId, String userId, String finalReport) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.get(emitterKey);

        if (emitter != null) {
            sseExecutorService.submit(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name("completion")
                            .data(Map.of(
                                    "taskId", taskId,
                                    "status", "completed",
                                    "finalReport", finalReport,
                                    "timestamp", LocalDateTime.now().toString()
                            )));

                    // Complete the emitter
                    emitter.complete();
                } catch (IOException e) {
                    log.error("Failed to send completion event for task: {}", taskId, e);
                } finally {
                    activeEmitters.remove(emitterKey);
                }
            });
        }
    }

    /**
     * Send error event
     */
    public void sendErrorEvent(String taskId, String userId, String errorMessage) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.get(emitterKey);

        if (emitter != null) {
            sseExecutorService.submit(() -> {
                try {
                    emitter.send(SseEmitter.event()
                            .name("error")
                            .data(Map.of(
                                    "taskId", taskId,
                                    "status", "error",
                                    "errorMessage", errorMessage,
                                    "timestamp", LocalDateTime.now().toString()
                            )));
                } catch (IOException e) {
                    log.error("Failed to send error event for task: {}", taskId, e);
                } finally {
                    activeEmitters.remove(emitterKey);
                }
            });
        }
    }

    /**
     * Handle Redis pub/sub messages for real-time updates
     */
    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            String channel = new String(message.getChannel());
            String messageBody = new String(message.getBody());

            // Parse the message
            // Note: In a real implementation, you'd use a proper JSON parser
            // This is a simplified version

            if (AGENT_STATUS_CHANNEL.equals(channel)) {
                handleAgentStatusUpdate(messageBody);
            } else if (WORKFLOW_STATUS_CHANNEL.equals(channel)) {
                handleWorkflowStatusUpdate(messageBody);
            }

        } catch (Exception e) {
            log.error("Error processing Redis message", e);
        }
    }

    /**
     * Handle agent status updates from Redis
     */
    private void handleAgentStatusUpdate(String messageBody) {
        // Parse message and forward to appropriate SSE emitters
        // Implementation would depend on your JSON parsing strategy
        log.debug("Received agent status update: {}", messageBody);
    }

    /**
     * Handle workflow status updates from Redis
     */
    private void handleWorkflowStatusUpdate(String messageBody) {
        // Parse message and forward to appropriate SSE emitters
        // Implementation would depend on your JSON parsing strategy
        log.debug("Received workflow status update: {}", messageBody);
    }

    /**
     * Send heartbeat to keep SSE connections alive
     */
    @Scheduled(fixedRate = HEARTBEAT_INTERVAL)
    public void sendHeartbeats() {
        activeEmitters.forEach((key, emitter) -> {
            try {
                emitter.send(SseEmitter.event().name("heartbeat").data("ping"));
            } catch (IOException e) {
                log.debug("Failed to send heartbeat, removing emitter: {}", key);
                activeEmitters.remove(key);
            }
        });
    }

    /**
     * Clean up expired emitters
     */
    @Scheduled(fixedRate = 60000) // Every minute
    public void cleanupExpiredEmitters() {
        // Remove any emitters that might have been missed by callbacks
        activeEmitters.entrySet().removeIf(entry -> {
            SseEmitter emitter = entry.getValue();
            // Check if emitter is still active
            // Note: SseEmitter doesn't have an isComplete() method in older versions
            // You might need to track this separately
            return false; // Simplified for this example
        });
    }

    /**
     * Get the number of active SSE connections
     */
    public int getActiveConnectionsCount() {
        return activeEmitters.size();
    }

    /**
     * Check if a specific task has an active SSE connection
     */
    public boolean hasActiveConnection(String taskId, String userId) {
        return activeEmitters.containsKey(getEmitterKey(taskId, userId));
    }

    /**
     * Manually close SSE connection for a task
     */
    public void closeConnection(String taskId, String userId) {
        String emitterKey = getEmitterKey(taskId, userId);
        SseEmitter emitter = activeEmitters.remove(emitterKey);
        if (emitter != null) {
            try {
                emitter.send(SseEmitter.event().name("closed").data("Connection closed by server"));
                emitter.complete();
            } catch (IOException e) {
                log.debug("Error closing SSE emitter for task: {}", taskId, e);
            }
        }
    }

    /**
     * Generate unique key for emitter storage
     */
    private String getEmitterKey(String taskId, String userId) {
        return taskId + ":" + userId;
    }
}