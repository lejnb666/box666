package com.insightweaver.security;

import com.insightweaver.service.RedisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.TimeUnit;

/**
 * Advanced rate limiting filter with multiple strategies
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
@RequiredArgsConstructor
@Slf4j
public class RateLimitFilter extends OncePerRequestFilter {

    private final RedisService redisService;

    // Rate limit configurations
    private static final int DEFAULT_REQUESTS_PER_MINUTE = 100;
    private static final int BURST_MULTIPLIER = 2;
    private static final int PENALTY_DURATION_MINUTES = 15;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {

        String clientIdentifier = getClientIdentifier(request);
        String requestPath = request.getRequestURI();

        // Skip rate limiting for certain paths
        if (shouldSkipRateLimit(requestPath)) {
            filterChain.doFilter(request, response);
            return;
        }

        try {
            // Check if client is blocked
            if (isClientBlocked(clientIdentifier)) {
                sendRateLimitResponse(response, "Rate limit exceeded. Please try again later.");
                return;
            }

            // Apply different rate limiting strategies
            if (!allowRequest(clientIdentifier, requestPath, request)) {
                // Apply penalty
                applyPenalty(clientIdentifier);
                sendRateLimitResponse(response, "Rate limit exceeded for this endpoint.");
                return;
            }

            // Add rate limit headers
            addRateLimitHeaders(response, clientIdentifier, requestPath, request);

            filterChain.doFilter(request, response);

        } catch (Exception e) {
            log.error("Rate limiting error for client: {}", clientIdentifier, e);
            // Don't block the request on rate limiting errors
            filterChain.doFilter(request, response);
        }
    }

    private String getClientIdentifier(HttpServletRequest request) {
        // Use API key if available, otherwise use IP
        String apiKey = request.getHeader("X-API-Key");
        if (apiKey != null && !apiKey.isEmpty()) {
            return "api_key:" + apiKey;
        }

        // Use user ID if authenticated
        if (request.getUserPrincipal() != null) {
            return "user:" + request.getUserPrincipal().getName();
        }

        // Fall back to IP address
        return "ip:" + getClientIp(request);
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        String xRealIp = request.getHeader("X-Real-IP");
        if (xRealIp != null && !xRealIp.isEmpty()) {
            return xRealIp;
        }
        return request.getRemoteAddr();
    }

    private boolean shouldSkipRateLimit(String requestPath) {
        return requestPath.startsWith("/actuator/health") ||
               requestPath.startsWith("/actuator/info") ||
               requestPath.contains("/public/") ||
               requestPath.endsWith(".css") ||
               requestPath.endsWith(".js") ||
               requestPath.endsWith(".png") ||
               requestPath.endsWith(".jpg") ||
               requestPath.endsWith(".ico");
    }

    private boolean isClientBlocked(String clientIdentifier) {
        String blockKey = "rate_limit:block:" + clientIdentifier;
        return redisService.getValue(blockKey).isPresent();
    }

    private boolean allowRequest(String clientIdentifier, String requestPath, HttpServletRequest request) {
        // Apply different rate limits based on endpoint type and user level
        RateLimitConfig config = getRateLimitConfig(requestPath, request);

        // Use token bucket algorithm for smooth rate limiting
        return tryConsumeToken(clientIdentifier, requestPath, config);
    }

    private boolean tryConsumeToken(String clientIdentifier, String requestPath, RateLimitConfig config) {
        String tokenKey = "rate_limit:tokens:" + clientIdentifier + ":" + sanitizePath(requestPath);
        String timestampKey = "rate_limit:timestamp:" + clientIdentifier + ":" + sanitizePath(requestPath);

        long now = Instant.now().getEpochSecond();
        long windowStart = now - 60; // 1 minute window

        // Get current state
        Integer currentTokens = (Integer) redisService.getValue(tokenKey).orElse(config.getMaxRequests());
        Long lastRefill = (Long) redisService.getValue(timestampKey).orElse(now);

        // Refill tokens based on time passed
        long timePassed = now - lastRefill;
        int tokensToAdd = (int) (timePassed * config.getMaxRequests() / 60); // Refill rate per second
        currentTokens = Math.min(config.getMaxRequests(), currentTokens + tokensToAdd);

        // Update timestamp
        redisService.setValue(timestampKey, now, 120); // 2 minute TTL

        // Consume token if available
        if (currentTokens > 0) {
            redisService.setValue(tokenKey, currentTokens - 1, 120);
            return true;
        }

        return false;
    }

    private void applyPenalty(String clientIdentifier) {
        String blockKey = "rate_limit:block:" + clientIdentifier;
        redisService.setValue(blockKey, "blocked", PENALTY_DURATION_MINUTES * 60);

        log.warn("Applied rate limit penalty to client: {} for {} minutes",
                clientIdentifier, PENALTY_DURATION_MINUTES);
    }

    private void addRateLimitHeaders(HttpServletResponse response, String clientIdentifier, String requestPath, HttpServletRequest request) {
        RateLimitConfig config = getRateLimitConfig(requestPath, request);
        String tokenKey = "rate_limit:tokens:" + clientIdentifier + ":" + sanitizePath(requestPath);

        Integer remainingTokens = (Integer) redisService.getValue(tokenKey).orElse(config.getMaxRequests());

        response.setHeader("X-RateLimit-Limit", String.valueOf(config.getMaxRequests()));
        response.setHeader("X-RateLimit-Remaining", String.valueOf(Math.max(0, remainingTokens - 1)));
        response.setHeader("X-RateLimit-Reset", String.valueOf(60)); // Reset in 60 seconds
        response.setHeader("X-RateLimit-UserLevel", getUserLevel(request)); // Add user level info
    }

    private void sendRateLimitResponse(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setContentType("application/json");
        response.setHeader("Retry-After", "60");

        String jsonResponse = String.format(
                "{\"error\": \"Too Many Requests\", \"message\": \"%s\", \"status\": 429}",
                message
        );

        response.getWriter().write(jsonResponse);
    }

    private RateLimitConfig getRateLimitConfig(String requestPath, HttpServletRequest request) {
        // Get user level from UserPrincipal if available
        String userLevel = getUserLevel(request);

        // Base rate limits by endpoint type
        int baseLimit;
        if (requestPath.startsWith("/api/v1/auth")) {
            baseLimit = 10; // 10 requests per minute for auth
        } else if (requestPath.startsWith("/api/v1/research")) {
            baseLimit = 30; // 30 requests per minute for research
        } else if (requestPath.startsWith("/api/v1/admin")) {
            baseLimit = 20; // 20 requests per minute for admin
        } else {
            baseLimit = DEFAULT_REQUESTS_PER_MINUTE;
        }

        // Apply user level multipliers
        int adjustedLimit = adjustLimitByUserLevel(baseLimit, userLevel);

        return new RateLimitConfig(adjustedLimit, 60);
    }

    private String getUserLevel(HttpServletRequest request) {
        // Extract user level from UserPrincipal or JWT token
        if (request.getUserPrincipal() != null) {
            // In a real implementation, you would parse the JWT token or
            // query user database to get user level/role
            String userName = request.getUserPrincipal().getName();

            // Example logic - in production, this would come from your user management system
            if (userName.startsWith("admin_") || isUserInRole(request, "ADMIN")) {
                return "ADMIN";
            } else if (userName.startsWith("premium_") || isUserInRole(request, "PREMIUM")) {
                return "PREMIUM";
            } else if (userName.startsWith("member_") || isUserInRole(request, "MEMBER")) {
                return "MEMBER";
            }
        }

        // Check for API key header for programmatic access
        String apiKey = request.getHeader("X-API-Key");
        if (apiKey != null && !apiKey.isEmpty()) {
            String keyLevel = getApiKeyLevel(apiKey);
            if (keyLevel != null) {
                return keyLevel;
            }
        }

        return "GUEST"; // Default level
    }

    private boolean isUserInRole(HttpServletRequest request, String role) {
        // Check if user has specific role
        // This is a simplified implementation
        return request.isUserInRole(role);
    }

    private String getApiKeyLevel(String apiKey) {
        // In production, this would lookup the API key in database/cache
        // to determine the associated user level and limits
        if (apiKey.startsWith("ak_admin_")) {
            return "ADMIN";
        } else if (apiKey.startsWith("ak_premium_")) {
            return "PREMIUM";
        } else if (apiKey.startsWith("ak_member_")) {
            return "MEMBER";
        }
        return "GUEST";
    }

    private int adjustLimitByUserLevel(int baseLimit, String userLevel) {
        // User level multipliers for rate limiting
        switch (userLevel) {
            case "ADMIN":
                return baseLimit * 10; // Admins get 10x the base limit
            case "PREMIUM":
                return baseLimit * 5;  // Premium users get 5x the base limit
            case "MEMBER":
                return baseLimit * 2;  // Regular members get 2x the base limit
            case "GUEST":
            default:
                return baseLimit;      // Guests get the base limit
        }
    }

    private String sanitizePath(String path) {
        // Remove dynamic parts from path for rate limiting
        return path.replaceAll("/[0-9a-fA-F\\-]+", "/:id")
                  .replaceAll("/[0-9]+", "/:number");
    }

    @Data
    @AllArgsConstructor
    private static class RateLimitConfig {
        private int maxRequests;
        private int windowSeconds;
    }
}