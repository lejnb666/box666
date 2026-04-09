package com.streammonitor.repository;

import com.streammonitor.model.entity.PushLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 推送历史记录仓库
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Repository
public interface PushLogRepository extends JpaRepository<PushLog, Long> {

    /**
     * 根据用户ID查询推送历史
     */
    List<PushLog> findByUserIdOrderBySentAtDesc(Long userId);

    /**
     * 根据任务ID查询推送历史
     */
    List<PushLog> findByTaskIdOrderBySentAtDesc(Long taskId);

    /**
     * 根据状态查询推送历史
     */
    List<PushLog> findByStatusOrderBySentAtDesc(Integer status);

    /**
     * 根据发送时间查询推送历史
     */
    List<PushLog> findBySentAtBetweenOrderBySentAtDesc(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 根据用户ID和状态查询
     */
    List<PushLog> findByUserIdAndStatusOrderBySentAtDesc(Long userId, Integer status);

    /**
     * 统计用户的推送数量
     */
    long countByUserId(Long userId);

    /**
     * 统计指定时间范围内的推送数量
     */
    long countBySentAtBetween(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 统计用户未读推送数量
     */
    long countByUserIdAndStatus(Long userId, Integer status);

    /**
     * 删除指定时间之前的推送记录
     */
    int deleteBySentAtBefore(LocalDateTime timestamp);

    /**
     * 根据状态和发送时间删除记录（用于数据维护）
     */
    int deleteByStatusAndSentAtBefore(Integer status, LocalDateTime timestamp);

    /**
     * 统计用户有效推送记录数（用户ID不为空）
     */
    long countByUserIdIsNotNull();

    /**
     * 根据发送时间统计推送数量
     */
    long countBySentAtAfter(LocalDateTime timestamp);

    /**
     * 获取最新的推送记录
     */
    List<PushLog> findTop10ByOrderBySentAtDesc();

    /**
     * 根据触发类型统计推送数量
     */
    @Query("SELECT p.triggerType, COUNT(p) FROM PushLog p GROUP BY p.triggerType")
    List<Object[]> countByTriggerType();

    /**
     * 根据平台统计推送数量
     */
    @Query("SELECT p.platform, COUNT(p) FROM PushLog p GROUP BY p.platform")
    List<Object[]> countByPlatform();

    /**
     * 获取用户推送统计
     */
    @Query("SELECT p.userId, COUNT(p), SUM(CASE WHEN p.status = 2 THEN 1 ELSE 0 END) " +
           "FROM PushLog p GROUP BY p.userId")
    List<Object[]> getUserPushStats();

    /**
     * 获取时间段内的推送趋势
     */
    @Query("SELECT DATE(p.sentAt), COUNT(p) FROM PushLog p " +
           "WHERE p.sentAt BETWEEN :startTime AND :endTime " +
           "GROUP BY DATE(p.sentAt) ORDER BY DATE(p.sentAt)")
    List<Object[]> getPushTrend(@Param("startTime") LocalDateTime startTime,
                               @Param("endTime") LocalDateTime endTime);
}