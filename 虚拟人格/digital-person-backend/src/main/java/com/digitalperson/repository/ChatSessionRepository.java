package com.digitalperson.repository;

import com.digitalperson.entity.ChatSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ChatSessionRepository extends JpaRepository<ChatSession, Long> {
    List<ChatSession> findByUserIdOrderByCreatedAtDesc(Long userId);

    @Query("SELECT s FROM ChatSession s WHERE s.user.id = :userId AND s.sessionId = :sessionId")
    Optional<ChatSession> findByUserIdAndSessionId(@Param("userId") Long userId, @Param("sessionId") Long sessionId);

    void deleteByUserIdAndSessionId(Long userId, Long sessionId);
}