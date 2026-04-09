package com.streammonitor.model.dto;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

/**
 * 弹幕分钟聚合数据DTO
 */
@Data
@Document(collection = "barrage_minute_summary")
public class BarrageMinuteSummary {

    @Id
    private String id;

    /**
     * 主播ID
     */
    private String streamerId;

    /**
     * 主播名称
     */
    private String streamerName;

    /**
     * 分钟时间
     */
    private LocalDateTime minuteTime;

    /**
     * 弹幕数量
     */
    private Integer barrageCount;

    /**
     * 独立用户数
     */
    private Integer uniqueUserCount;

    /**
     * 礼物总价值
     */
    private Double totalGiftValue;

    /**
     * 平均弹幕长度
     */
    private Double avgContentLength;

    /**
     * 创建时间
     */
    private LocalDateTime createdAt;

    /**
     * 更新时间
     */
    private LocalDateTime updatedAt;
}