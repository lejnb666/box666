package com.streammonitor.dto;

import lombok.Data;

import java.io.Serializable;
import java.time.LocalDate;
import java.util.Map;

/**
 * 分析数据数据传输对象
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
public class AnalyticsData implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 开始日期
     */
    private LocalDate startDate;

    /**
     * 结束日期
     */
    private LocalDate endDate;

    /**
     * 总推送次数
     */
    private long totalPushes;

    /**
     * 成功推送次数
     */
    private long successfulPushes;

    /**
     * 失败推送次数
     */
    private long failedPushes;

    /**
     * 推送成功率
     */
    private double successRate;

    /**
     * 触发类型统计
     */
    private Map<String, Long> triggerTypeStats;

    /**
     * 平台统计
     */
    private Map<String, Long> platformStats;

    /**
     * 平均响应时间（毫秒）
     */
    private long avgResponseTime;

    /**
     * 最活跃时间段
     */
    private String peakTime;

    /**
     * 最常监控的主播
     */
    private String topStreamer;

    public AnalyticsData() {
        this.totalPushes = 0;
        this.successfulPushes = 0;
        this.failedPushes = 0;
        this.successRate = 0.0;
        this.avgResponseTime = 0;
    }

    /**
     * 获取失败率
     */
    public double getFailureRate() {
        if (totalPushes > 0) {
            return 100.0 - successRate;
        }
        return 0.0;
    }

    /**
     * 获取成功率百分比字符串
     */
    public String getSuccessRatePercentage() {
        return String.format("%.2f%%", successRate);
    }

    /**
     * 获取失败率百分比字符串
     */
    public String getFailureRatePercentage() {
        return String.format("%.2f%%", getFailureRate());
    }

    /**
     * 判断是否为活跃用户（7天内有推送）
     */
    public boolean isActiveUser() {
        return totalPushes > 0;
    }

    /**
     * 获取推送密度（每天平均推送次数）
     */
    public double getPushDensity() {
        if (startDate != null && endDate != null) {
            long days = java.time.temporal.ChronoUnit.DAYS.between(startDate, endDate) + 1;
            return (double) totalPushes / days;
        }
        return 0.0;
    }

    @Override
    public String toString() {
        return String.format(
            "AnalyticsData{userId=%d, totalPushes=%d, successfulPushes=%d, failedPushes=%d, successRate=%.2f%%}",
            userId, totalPushes, successfulPushes, failedPushes, successRate
        );
    }
}