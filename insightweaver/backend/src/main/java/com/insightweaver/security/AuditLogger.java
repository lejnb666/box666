package com.insightweaver.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import brave.Tracer;
import brave.Tracing;
import org.springframework.beans.factory.annotation.Autowired;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Comprehensive audit logging for security and compliance
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AuditLogger extends OncePerRequestFilter {

    private final ObjectMapper objectMapper;

    @Autowired
    private Tracer tracer;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {

        long startTime = System.currentTimeMillis();
        String requestId = UUID.randomUUID().toString();

        // Get distributed tracing ID
        String traceId = "";
        String spanId = "";
        if (tracer != null && tracer.currentSpan() != null) {
            traceId = tracer.currentSpan().context().traceIdString();
            spanId = tracer.currentSpan().context().spanIdString();
        }

        // Generate audit log entry
        AuditLogEntry auditEntry = AuditLogEntry.builder()
                .requestId(requestId)
                .traceId(traceId)
                .spanId(spanId)
                .timestamp(LocalDateTime.now())
                .method(request.getMethod())
                .url(request.getRequestURL().toString())
                .clientIp(getClientIp(request))
                .userAgent(request.getHeader("User-Agent"))
                .userId(getUserId(request))
                .sessionId(request.getSession().getId())
                .build();

        try {
            // Continue the filter chain
            filterChain.doFilter(request, response);

            // Log successful request
            auditEntry.setStatusCode(response.getStatus());
            auditEntry.setResponseTime(System.currentTimeMillis() - startTime);
            auditEntry.setStatus("SUCCESS");

            logAuditEntry(auditEntry);

        } catch (Exception e) {
            // Log failed request
            auditEntry.setStatusCode(500);
            auditEntry.setResponseTime(System.currentTimeMillis() - startTime);
            auditEntry.setStatus("ERROR");
            auditEntry.setErrorMessage(e.getMessage());

            logAuditEntry(auditEntry);
            throw e;
        }
    }

    private void logAuditEntry(AuditLogEntry entry) {
        try {
            String auditJson = objectMapper.writeValueAsString(entry);
            log.info("AUDIT_LOG: {}", auditJson);

            // Also store in database for compliance (would be implemented with JPA repository)
            // auditLogRepository.save(entry);

        } catch (Exception e) {
            log.error("Failed to log audit entry", e);
        }
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    private String getUserId(HttpServletRequest request) {
        // Extract user ID from JWT token or session
        // Implementation would depend on your authentication mechanism
        return request.getUserPrincipal() != null ?
               request.getUserPrincipal().getName() : "anonymous";
    }

    @Builder
    @Data
    public static class AuditLogEntry {
        private String requestId;
        private String traceId;  // Distributed tracing ID
        private String spanId;   // Span ID for operation tracking
        private LocalDateTime timestamp;
        private String method;
        private String url;
        private String clientIp;
        private String userAgent;
        private String userId;
        private String sessionId;
        private int statusCode;
        private long responseTime;
        private String status;
        private String errorMessage;
        private Map<String, Object> additionalData;
    }
}