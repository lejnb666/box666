package com.insightweaver.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * DTO for research task creation request
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResearchRequest {

    @NotBlank(message = "Title is required")
    @Size(max = 500, message = "Title must not exceed 500 characters")
    private String title;

    @Size(max = 2000, message = "Description must not exceed 2000 characters")
    private String description;

    @JsonProperty("research_topics")
    private List<String> researchTopics;

    @JsonProperty("preferred_sources")
    private List<String> preferredSources;

    @JsonProperty("output_format")
    private OutputFormat outputFormat;

    @JsonProperty("tone_style")
    private ToneStyle toneStyle;

    @JsonProperty("max_sources")
    private Integer maxSources;

    @JsonProperty("include_citations")
    private Boolean includeCitations;

    @JsonProperty("custom_instructions")
    private String customInstructions;

    @JsonProperty("deadline_minutes")
    private Integer deadlineMinutes;

    @JsonProperty("additional_context")
    private Map<String, Object> additionalContext;

    // Enum definitions
    public enum OutputFormat {
        MARKDOWN, HTML, PLAIN_TEXT, PDF
    }

    public enum ToneStyle {
        FORMAL, INFORMAL, ACADEMIC, JOURNALISTIC, TECHNICAL, CONVERSATIONAL
    }

    // Validation methods
    public boolean hasCustomInstructions() {
        return customInstructions != null && !customInstructions.trim().isEmpty();
    }

    public boolean requiresCitations() {
        return includeCitations != null && includeCitations;
    }

    public boolean hasPreferredSources() {
        return preferredSources != null && !preferredSources.isEmpty();
    }

    public boolean hasResearchTopics() {
        return researchTopics != null && !researchTopics.isEmpty();
    }

    public int getEffectiveMaxSources() {
        return maxSources != null && maxSources > 0 ? maxSources : 20;
    }

    public int getEffectiveDeadlineMinutes() {
        return deadlineMinutes != null && deadlineMinutes > 0 ? deadlineMinutes : 30;
    }
}