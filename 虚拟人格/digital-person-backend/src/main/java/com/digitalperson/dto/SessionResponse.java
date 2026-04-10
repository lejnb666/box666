package com.digitalperson.dto;

import java.time.LocalDateTime;

public class SessionResponse {
    private Long sessionId;
    private String sessionName;
    private LocalDateTime createdAt;

    // Constructors
    public SessionResponse() {}

    public SessionResponse(Long sessionId, String sessionName, LocalDateTime createdAt) {
        this.sessionId = sessionId;
        this.sessionName = sessionName;
        this.createdAt = createdAt;
    }

    // Getters and Setters
    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
    }

    public String getSessionName() {
        return sessionName;
    }

    public void setSessionName(String sessionName) {
        this.sessionName = sessionName;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}