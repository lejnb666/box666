package com.digitalperson.controller;

import com.digitalperson.dto.SessionResponse;
import com.digitalperson.entity.ChatSession;
import com.digitalperson.service.SessionService;
import com.digitalperson.util.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import java.util.List;

@RestController
@RequestMapping("/api/sessions")
@CrossOrigin(origins = "*")
public class SessionController {

    @Autowired
    private SessionService sessionService;

    @Autowired
    private JwtUtil jwtUtil;

    private Long getUserIdFromToken(HttpServletRequest request) {
        String token = request.getHeader("Authorization");
        if (token != null && token.startsWith("Bearer ")) {
            token = token.substring(7);
            return jwtUtil.extractUserId(token);
        }
        throw new RuntimeException("Invalid token");
    }

    @PostMapping
    public ResponseEntity<ChatSession> createSession(@RequestParam String sessionName, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromToken(request);
            ChatSession session = sessionService.createSession(userId, sessionName);
            return ResponseEntity.ok(session);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @GetMapping
    public ResponseEntity<List<SessionResponse>> getUserSessions(HttpServletRequest request) {
        try {
            Long userId = getUserIdFromToken(request);
            List<SessionResponse> sessions = sessionService.getUserSessions(userId);
            return ResponseEntity.ok(sessions);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @DeleteMapping("/{sessionId}")
    public ResponseEntity<Void> deleteSession(@PathVariable Long sessionId, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromToken(request);
            sessionService.deleteSession(userId, sessionId);
            return ResponseEntity.ok().build();
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }
}