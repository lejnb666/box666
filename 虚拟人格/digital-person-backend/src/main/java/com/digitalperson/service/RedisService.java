package com.digitalperson.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.TimeUnit;

@Service
public class RedisService {

    @Autowired
    private StringRedisTemplate redisTemplate;

    // Token management (whitelist/blacklist)
    public void addToWhitelist(String token, Long userId, long expirationInSeconds) {
        String key = "token:whitelist:" + token;
        redisTemplate.opsForValue().set(key, userId.toString(), expirationInSeconds, TimeUnit.SECONDS);
    }

    public boolean isTokenWhitelisted(String token) {
        String key = "token:whitelist:" + token;
        return redisTemplate.hasKey(key);
    }

    public void addToBlacklist(String token, long expirationInSeconds) {
        String key = "token:blacklist:" + token;
        redisTemplate.opsForValue().set(key, "blacklisted", expirationInSeconds, TimeUnit.SECONDS);
    }

    public boolean isTokenBlacklisted(String token) {
        String key = "token:blacklist:" + token;
        return redisTemplate.hasKey(key);
    }

    public void removeFromWhitelist(String token) {
        String key = "token:whitelist:" + token;
        redisTemplate.delete(key);
    }

    // Session context management (store last 10 messages)
    public void addMessageToSessionContext(Long sessionId, String messageJson) {
        String key = "session:context:" + sessionId;
        redisTemplate.opsForList().leftPush(key, messageJson);
        // Keep only last 10 messages
        redisTemplate.opsForList().trim(key, 0, 9);
        // Set expiration for 24 hours
        redisTemplate.expire(key, 24, TimeUnit.HOURS);
    }

    public List<String> getSessionContext(Long sessionId) {
        String key = "session:context:" + sessionId;
        return redisTemplate.opsForList().range(key, 0, -1);
    }

    public void clearSessionContext(Long sessionId) {
        String key = "session:context:" + sessionId;
        redisTemplate.delete(key);
    }

    // Online users tracking
    public void setUserOnline(Long userId, String sessionInfo) {
        String key = "user:online:" + userId;
        redisTemplate.opsForValue().set(key, sessionInfo, 30, TimeUnit.MINUTES);
    }

    public boolean isUserOnline(Long userId) {
        String key = "user:online:" + userId;
        return redisTemplate.hasKey(key);
    }

    public void setUserOffline(Long userId) {
        String key = "user:online:" + userId;
        redisTemplate.delete(key);
    }
}