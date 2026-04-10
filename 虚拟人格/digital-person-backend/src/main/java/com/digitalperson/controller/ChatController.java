package com.digitalperson.controller;

import com.digitalperson.dto.ChatRequest;
import com.digitalperson.entity.ChatMessage;
import com.digitalperson.repository.ChatMessageRepository;
import com.digitalperson.repository.ChatSessionRepository;
import com.digitalperson.service.ChatService;
import com.digitalperson.service.SessionService;
import com.digitalperson.util.JwtUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.servlet.http.HttpServletRequest;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@CrossOrigin(origins = "*")
public class ChatController {

    @Autowired
    private ChatService chatService;

    @Autowired
    private SessionService sessionService;

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private ChatMessageRepository messageRepository;

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

    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> chat(@RequestBody ChatRequest chatRequest, HttpServletRequest request) {
        String userMessage = chatRequest.getMessage();
        if (userMessage == null || userMessage.trim().isEmpty()) {
            return ResponseEntity.badRequest().body(Map.of(
                "error", "Message cannot be empty"
            ));
        }

        try {
            Long userId = getUserIdFromToken(request);

            // Use existing session or create new one
            Long sessionId = chatRequest.getSessionId();
            if (sessionId == null) {
                com.digitalperson.entity.ChatSession newSession = sessionService.createSession(userId, "New Chat " + System.currentTimeMillis());
                sessionId = newSession.getSessionId();
            }

            // Verify session belongs to user
            sessionService.getSessionByUserAndId(userId, sessionId);

            // Get recent messages for context
            List<ChatMessage> recentMessages = messageRepository.findRecentMessagesBySessionId(sessionId, org.springframework.data.domain.PageRequest.of(0, 10));

            String response = chatService.processMessage(userMessage, recentMessages);

            // Save user message
            ChatMessage userMsg = new ChatMessage();
            userMsg.setSession(sessionRepository.findById(sessionId).orElseThrow());
            userMsg.setSenderType(ChatMessage.SenderType.USER);
            userMsg.setContent(userMessage);
            messageRepository.save(userMsg);

            // Save AI response
            ChatMessage aiMsg = new ChatMessage();
            aiMsg.setSession(sessionRepository.findById(sessionId).orElseThrow());
            aiMsg.setSenderType(ChatMessage.SenderType.AI);
            aiMsg.setContent(response);
            messageRepository.save(aiMsg);

            Map<String, Object> responseMap = new HashMap<>();
            responseMap.put("response", response);
            responseMap.put("success", true);
            responseMap.put("sessionId", sessionId);

            return ResponseEntity.ok(responseMap);
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of(
                "error", "Internal server error: " + e.getMessage(),
                "success", false
            ));
        }
    }

    @GetMapping("/messages/{sessionId}")
    public ResponseEntity<List<ChatMessage>> getSessionMessages(@PathVariable Long sessionId, HttpServletRequest request) {
        try {
            Long userId = getUserIdFromToken(request);
            List<ChatMessage> messages = messageRepository.findBySessionIdAndUserId(sessionId, userId);
            return ResponseEntity.ok(messages);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }
}