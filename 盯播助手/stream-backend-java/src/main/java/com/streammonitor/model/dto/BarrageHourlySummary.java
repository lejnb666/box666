package com.streammonitor.model.dto;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.Date;

/**
 * 弹幕小时聚合数据DTO
 */
@Data
@Document(collection = "barrage_hourly_aggregation")
public class BarrageHourlySummary {

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
     * 小时时间
     */
    private LocalDateTime hourTime;

    /**
     * 总弹幕数量
     */
    private Integer totalBarrageCount;

    /**
     * 总独立用户数
     */
    private Integer totalUniqueUsers;

    /**
     * 总礼物价值
     */
    private Double totalGiftValue;

    /**
     * 平均内容长度
     */
    private Double avgContentLength;

    /**
     * 分钟聚合记录数
     */
    private Integer minuteCount;

    /**
     * 创建时间
     */
    private Date createdAt;

    /**
     * 更新时间
     */
    private Date updatedAt;
}