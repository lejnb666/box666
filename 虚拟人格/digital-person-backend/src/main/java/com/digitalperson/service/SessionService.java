package com.digitalperson.service;

import com.digitalperson.dto.SessionResponse;
import com.digitalperson.entity.ChatSession;
import com.digitalperson.entity.User;
import com.digitalperson.repository.ChatSessionRepository;
import com.digitalperson.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class SessionService {

    @Autowired
    private ChatSessionRepository sessionRepository;

    @Autowired
    private UserRepository userRepository;

    public ChatSession createSession(Long userId, String sessionName) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));

        ChatSession session = new ChatSession(user, sessionName);
        return sessionRepository.save(session);
    }

    public List<SessionResponse> getUserSessions(Long userId) {
        List<ChatSession> sessions = sessionRepository.findByUserIdOrderByCreatedAtDesc(userId);
        return sessions.stream()
                .map(this::convertToSessionResponse)
                .collect(Collectors.toList());
    }

    public ChatSession getSessionByUserAndId(Long userId, Long sessionId) {
        return sessionRepository.findByUserIdAndSessionId(userId, sessionId)
                .orElseThrow(() -> new RuntimeException("Session not found or access denied"));
    }

    public void deleteSession(Long userId, Long sessionId) {
        ChatSession session = getSessionByUserAndId(userId, sessionId);
        sessionRepository.delete(session);
    }

    private SessionResponse convertToSessionResponse(ChatSession session) {
        return new SessionResponse(
                session.getSessionId(),
                session.getSessionName(),
                session.getCreatedAt()
        );
    }
}