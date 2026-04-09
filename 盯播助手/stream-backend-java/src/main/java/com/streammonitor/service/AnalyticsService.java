package com.streammonitor.service;

import com.streammonitor.dto.AnalyticsData;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

/**
 * 分析服务接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface AnalyticsService {

    /**
     * 获取用户分析数据
     *
     * @param userId 用户ID
     * @param startDate 开始日期
     * @param endDate 结束日期
     * @return 分析数据
     */
    AnalyticsData getUserAnalytics(Long userId, LocalDate startDate, LocalDate endDate);

    /**
     * 获取系统分析数据
     *
     * @param startDate 开始日期
     * @param endDate 结束日期
     * @return 系统分析数据
     */
    Map<String, Object> getSystemAnalytics(LocalDate startDate, LocalDate endDate);

    /**
     * 获取热门主播排行
     *
     * @param limit 返回数量限制
     * @return 热门主播列表
     */
    List<Map<String, Object>> getTopStreamers(int limit);

    /**
     * 获取活跃用户排行
     *
     * @param limit 返回数量限制
     * @return 活跃用户列表
     */
    List<Map<String, Object>> getTopUsers(int limit);

    /**
     * 获取实时统计数据
     *
     * @return 实时统计数据
     */
    Map<String, Object> getRealtimeStats();
}