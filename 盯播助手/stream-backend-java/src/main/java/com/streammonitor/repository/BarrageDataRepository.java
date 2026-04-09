package com.streammonitor.repository;

import com.streammonitor.model.entity.BarrageData;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 弹幕数据MySQL仓库（用于数据迁移，后续可废弃）
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Repository
public interface BarrageDataRepository extends JpaRepository<BarrageData, Long> {

    /**
     * 根据平台查询弹幕数据
     */
    List<BarrageData> findByPlatformOrderByTimestampDesc(String platform);

    /**
     * 根据房间ID查询弹幕数据
     */
    List<BarrageData> findByRoomIdOrderByTimestampDesc(String roomId);

    /**
     * 根据用户ID查询弹幕数据
     */
    List<BarrageData> findByUserIdOrderByTimestampDesc(String userId);

    /**
     * 根据时间范围查询弹幕数据
     */
    List<BarrageData> findByTimestampBetweenOrderByTimestampDesc(
            LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 分页查询指定时间范围内的弹幕数据
     */
    Page<BarrageData> findByTimestampBetweenOrderByTimestampAsc(
            LocalDateTime startTime, LocalDateTime endTime, Pageable pageable);

    /**
     * 根据平台和房间ID查询弹幕数据
     */
    List<BarrageData> findByPlatformAndRoomIdOrderByTimestampDesc(
            String platform, String roomId);

    /**
     * 统计指定时间范围内的弹幕数量
     */
    long countByTimestampBetween(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 统计指定平台的弹幕数量
     */
    long countByPlatform(String platform);

    /**
     * 统计指定房间的弹幕数量
     */
    long countByRoomId(String roomId);

    /**
     * 统计指定用户的弹幕数量
     */
    long countByUserId(String userId);

    /**
     * 删除指定时间之前的弹幕数据
     */
    long deleteByTimestampBefore(LocalDateTime timestamp);

    /**
     * 删除指定平台的所有弹幕数据
     */
    long deleteByPlatform(String platform);

    /**
     * 删除指定房间的所有弹幕数据
     */
    long deleteByRoomId(String roomId);

    /**
     * 获取最新的弹幕数据
     */
    List<BarrageData> findTop100ByOrderByTimestampDesc();

    /**
     * 根据内容关键词搜索弹幕
     */
    List<BarrageData> findByContentContainingOrderByTimestampDesc(String keyword);

    /**
     * 获取弹幕统计信息
     */
    @Query("SELECT p.platform, COUNT(p) FROM BarrageData p GROUP BY p.platform")
    List<Object[]> getPlatformStats();

    /**
     * 获取时间段内的弹幕趋势
     */
    @Query("SELECT DATE(p.timestamp), COUNT(p) FROM BarrageData p " +
           "WHERE p.timestamp BETWEEN :startTime AND :endTime " +
           "GROUP BY DATE(p.timestamp) ORDER BY DATE(p.timestamp)")
    List<Object[]> getBarrageTrend(@Param("startTime") LocalDateTime startTime,
                                  @Param("endTime") LocalDateTime endTime);

    /**
     * 获取活跃用户排行
     */
    @Query("SELECT p.userId, p.username, COUNT(p) FROM BarrageData p " +
           "GROUP BY p.userId, p.username ORDER BY COUNT(p) DESC")
    List<Object[]> getActiveUsers();
}