package com.insightweaver.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.LocalDateTime;
import java.util.UUID;

/**
 * Research Task entity representing a user's research request
 */
@Entity
@Table(name = "research_tasks")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@EntityListeners(AuditingEntityListener.class)
public class ResearchTask {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @NotBlank
    @Size(max = 500)
    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TaskStatus status;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TaskPriority priority;

    @Column(name = "user_id", nullable = false)
    private String userId;

    @Column(name = "agent_workflow", columnDefinition = "JSON")
    private String agentWorkflow;

    @Column(name = "final_report", columnDefinition = "TEXT")
    private String finalReport;

    @Column(name = "intermediate_results", columnDefinition = "JSON")
    private String intermediateResults;

    @Column(name = "error_message")
    private String errorMessage;

    @Column(name = "estimated_completion_time")
    private LocalDateTime estimatedCompletionTime;

    @Column(name = "actual_completion_time")
    private LocalDateTime actualCompletionTime;

    @Column(name = "token_usage")
    private Integer tokenUsage;

    @Column(name = "cost_estimate")
    private Double costEstimate;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @Column(name = "started_at")
    private LocalDateTime startedAt;

    @Column(name = "completed_at")
    private LocalDateTime completedAt;

    // Enum definitions
    public enum TaskStatus {
        PENDING,        // Task created but not started
        PLANNING,       // Planning agent is working
        RESEARCHING,    // Research agent is gathering information
        ANALYZING,      // Analysis agent is processing data
        WRITING,        // Writing agent is generating report
        COMPLETED,      // Task finished successfully
        FAILED,         // Task failed due to error
        CANCELLED       // Task cancelled by user
    }

    public enum TaskPriority {
        LOW, MEDIUM, HIGH, URGENT
    }

    // Business logic methods
    public boolean isActive() {
        return status == TaskStatus.PLANNING ||
               status == TaskStatus.RESEARCHING ||
               status == TaskStatus.ANALYZING ||
               status == TaskStatus.WRITING;
    }

    public boolean isCompleted() {
        return status == TaskStatus.COMPLETED;
    }

    public boolean hasFailed() {
        return status == TaskStatus.FAILED;
    }

    public long getDurationInMinutes() {
        if (startedAt != null && completedAt != null) {
            return java.time.Duration.between(startedAt, completedAt).toMinutes();
        }
        return 0;
    }

    public void markAsStarted() {
        this.status = TaskStatus.PLANNING;
        this.startedAt = LocalDateTime.now();
    }

    public void markAsCompleted(String report) {
        this.status = TaskStatus.COMPLETED;
        this.finalReport = report;
        this.completedAt = LocalDateTime.now();
        if (this.startedAt == null) {
            this.startedAt = LocalDateTime.now();
        }
    }

    public void markAsFailed(String errorMessage) {
        this.status = TaskStatus.FAILED;
        this.errorMessage = errorMessage;
        this.completedAt = LocalDateTime.now();
    }
}