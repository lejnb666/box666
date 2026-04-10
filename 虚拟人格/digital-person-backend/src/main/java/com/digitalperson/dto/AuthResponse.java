package com.digitalperson.dto;

public class AuthResponse {
    private String token;
    private String username;
    private Long userId;
    private String message;

    // Constructors
    public AuthResponse() {}

    public AuthResponse(String token, String username, Long userId, String message) {
        this.token = token;
        this.username = username;
        this.userId = userId;
        this.message = message;
    }

    // Getters and Setters
    public String getToken() {
        return token;
    }

    public void setToken(String token) {
        this.token = token;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }
}