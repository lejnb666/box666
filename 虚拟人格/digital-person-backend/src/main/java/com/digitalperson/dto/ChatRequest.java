package com.digitalperson.dto;

public class ChatRequest {
    private String message;
    private Long sessionId;

    // Constructors
    public ChatRequest() {}

    public ChatRequest(String message, Long sessionId) {
        this.message = message;
        this.sessionId = sessionId;
    }

    // Getters and Setters
    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public Long getSessionId() {
        return sessionId;
    }

    public void setSessionId(Long sessionId) {
        this.sessionId = sessionId;
    }
}