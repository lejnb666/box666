package com.insightweaver.controller;

import com.insightweaver.dto.ResearchRequest;
import com.insightweaver.dto.ResearchResponse;
import com.insightweaver.service.ResearchService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.UUID;

/**
 * REST controller for research task management
 */
@RestController
@RequestMapping("/research")
@RequiredArgsConstructor
@Slf4j
public class ResearchController {

    private final ResearchService researchService;

    /**
     * Create a new research task
     */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ResearchResponse> createResearchTask(
            @Valid @RequestBody ResearchRequest request,
            Authentication authentication) {

        log.info("Creating new research task: {}", request.getTitle());
        String userId = authentication.getName();

        ResearchResponse response = researchService.createResearchTask(request, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * Get research task by ID
     */
    @GetMapping("/{taskId}")
    public ResponseEntity<ResearchResponse> getResearchTask(
            @PathVariable UUID taskId,
            Authentication authentication) {

        log.info("Fetching research task: {}", taskId);
        String userId = authentication.getName();

        ResearchResponse response = researchService.getResearchTask(taskId, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * Get all research tasks for current user
     */
    @GetMapping
    public ResponseEntity<List<ResearchResponse>> getUserResearchTasks(
            Authentication authentication) {

        log.info("Fetching all research tasks for user");
        String userId = authentication.getName();

        List<ResearchResponse> tasks = researchService.getUserResearchTasks(userId);
        return ResponseEntity.ok(tasks);
    }

    /**
     * Cancel a research task
     */
    @PostMapping("/{taskId}/cancel")
    public ResponseEntity<ResearchResponse> cancelResearchTask(
            @PathVariable UUID taskId,
            Authentication authentication) {

        log.info("Cancelling research task: {}", taskId);
        String userId = authentication.getName();

        ResearchResponse response = researchService.cancelResearchTask(taskId, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * Stream real-time updates for a research task
     */
    @GetMapping("/{taskId}/stream")
    public SseEmitter streamResearchProgress(
            @PathVariable UUID taskId,
            Authentication authentication) {

        log.info("Starting SSE stream for task: {}", taskId);
        String userId = authentication.getName();

        return researchService.createProgressStream(taskId, userId);
    }

    /**
     * Get research task history
     */
    @GetMapping("/{taskId}/history")
    public ResponseEntity<List<ResearchResponse.IntermediateResult>> getTaskHistory(
            @PathVariable UUID taskId,
            Authentication authentication) {

        log.info("Fetching history for task: {}", taskId);
        String userId = authentication.getName();

        List<ResearchResponse.IntermediateResult> history =
            researchService.getTaskHistory(taskId, userId);
        return ResponseEntity.ok(history);
    }

    /**
     * Update research task priority
     */
    @PutMapping("/{taskId}/priority")
    public ResponseEntity<ResearchResponse> updateTaskPriority(
            @PathVariable UUID taskId,
            @RequestParam String priority,
            Authentication authentication) {

        log.info("Updating priority for task: {} to {}", taskId, priority);
        String userId = authentication.getName();

        ResearchResponse response = researchService.updateTaskPriority(taskId, priority, userId);
        return ResponseEntity.ok(response);
    }

    /**
     * Get research statistics for current user
     */
    @GetMapping("/stats")
    public ResponseEntity<Object> getUserStats(Authentication authentication) {
        log.info("Fetching user statistics");
        String userId = authentication.getName();

        Object stats = researchService.getUserStats(userId);
        return ResponseEntity.ok(stats);
    }
}