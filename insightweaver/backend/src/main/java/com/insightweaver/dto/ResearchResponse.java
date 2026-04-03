package com.insightweaver.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * DTO for research task response
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResearchResponse {

    private UUID id;
    private String title;
    private String description;

    @JsonProperty("current_status")
    private String currentStatus;

    @JsonProperty("progress_percentage")
    private Integer progressPercentage;

    @JsonProperty("agent_statuses")
    private Map<String, AgentStatus> agentStatuses;

    @JsonProperty("intermediate_results")
    private List<IntermediateResult> intermediateResults;

    @JsonProperty("final_report")
    private String finalReport;

    @JsonProperty("estimated_completion_time")
    private LocalDateTime estimatedCompletionTime;

    @JsonProperty("actual_completion_time")
    private LocalDateTime actualCompletionTime;

    @JsonProperty("token_usage")
    private Integer tokenUsage;

    @JsonProperty("sources_used")
    private List<SourceInfo> sourcesUsed;

    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    @JsonProperty("updated_at")
    private LocalDateTime updatedAt;

    @JsonProperty("error_message")
    private String errorMessage;

    // Nested classes
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AgentStatus {
        private String name;
        private String status;
        private String currentAction;
        private Double progress;
        private LocalDateTime lastUpdate;
        private Map<String, Object> metadata;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IntermediateResult {
        private String agent;
        private String type;
        private Object data;
        private LocalDateTime timestamp;
        private Map<String, Object> metadata;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SourceInfo {
        private String title;
        private String url;
        private String snippet;
        private Double relevanceScore;
        private String sourceType;
        private LocalDateTime retrievedAt;
    }

    // Utility methods
    public boolean isCompleted() {
        return "COMPLETED".equals(currentStatus);
    }

    public boolean isInProgress() {
        return progressPercentage != null && progressPercentage > 0 && progressPercentage < 100;
    }

    public boolean hasError() {
        return errorMessage != null && !errorMessage.isEmpty();
    }

    public long getDurationMinutes() {
        if (createdAt != null && actualCompletionTime != null) {
            return java.time.Duration.between(createdAt, actualCompletionTime).toMinutes();
        }
        return 0;
    }
}