package com.streammonitor.service;

import com.streammonitor.model.dto.BarrageMinuteSummary;
import org.springframework.scheduling.annotation.Scheduled;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 弹幕聚合服务接口
 * 负责实时聚合MongoDB中的弹幕数据
 */
public interface BarrageAggregationService {

    /**
     * 每分钟执行一次聚合 - 实时聚合
     */
    void aggregateMinuteData();

    /**
     * 每小时执行一次聚合
     */
    void aggregateHourlyData();

    /**
     * 每日执行一次聚合
     */
    void aggregateDailyData();

    /**
     * 获取指定主播的聚合数据
     *
     * @param streamerId 主播ID
     * @param startTime 开始时间
     * @param endTime 结束时间
     * @return 聚合数据列表
     */
    List<BarrageMinuteSummary> getStreamerAggregatedData(String streamerId, LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 清理过期的聚合数据
     */
    void cleanupExpiredData();
}