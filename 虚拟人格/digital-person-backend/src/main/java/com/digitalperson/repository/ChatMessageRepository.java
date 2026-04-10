package com.digitalperson.repository;

import com.digitalperson.entity.ChatMessage;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatMessageRepository extends JpaRepository<ChatMessage, Long> {
    List<ChatMessage> findBySession_SessionIdOrderByCreatedAtAsc(Long sessionId);

    @Query("SELECT m FROM ChatMessage m WHERE m.session.sessionId = :sessionId ORDER BY m.createdAt DESC")
    List<ChatMessage> findRecentMessagesBySessionId(@Param("sessionId") Long sessionId, org.springframework.data.domain.Pageable pageable);

    @Query("SELECT m FROM ChatMessage m WHERE m.session.sessionId = :sessionId AND m.session.user.id = :userId")
    List<ChatMessage> findBySessionIdAndUserId(@Param("sessionId") Long sessionId, @Param("userId") Long userId);

    void deleteBySession_SessionId(Long sessionId);
}