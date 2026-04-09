package com.streammonitor.model.document;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 商品监控记录文档 - MongoDB存储
 * 替代MySQL的product_monitor_log表，支持TTL自动过期
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "product_monitor_log")
@CompoundIndex(name = "product_monitor_query_index", def = "{'platform': 1, 'roomId': 1, 'detectedAt': -1}")
public class ProductMonitorDocument {

    @Id
    private String id;

    @Field("streamer_config_id")
    @Indexed
    private Long streamerConfigId;

    @Indexed
    private String platform;

    @Field("room_id")
    @Indexed
    private String roomId;

    @Field("product_name")
    private String productName;

    @Field("product_price")
    private BigDecimal productPrice;

    @Field("original_price")
    private BigDecimal originalPrice;

    @Field("discount_info")
    private String discountInfo;

    @Field("launch_time")
    private LocalDateTime launchTime;

    @Field("detected_by")
    @Indexed
    private String detectedBy; // keyword, ai

    @Field("detected_at")
    @Indexed
    private LocalDateTime detectedAt;

    @Field("trigger_content")
    private String triggerContent;

    @Field("ai_confidence")
    private Double aiConfidence;

    @Field("streamer_name")
    private String streamerName;

    @Field("user_id")
    private String userId;

    @Field("username")
    private String username;

    // 构造方法
    public ProductMonitorDocument(String platform, String roomId, String productName,
                                 BigDecimal productPrice, String detectedBy) {
        this.platform = platform;
        this.roomId = roomId;
        this.productName = productName;
        this.productPrice = productPrice;
        this.detectedBy = detectedBy;
        this.detectedAt = LocalDateTime.now();
        this.launchTime = LocalDateTime.now();
    }

    // 更新价格信息
    public void updatePriceInfo(BigDecimal originalPrice, String discountInfo) {
        this.originalPrice = originalPrice;
        this.discountInfo = discountInfo;
    }

    // 更新AI分析信息
    public void updateAIInfo(Double confidence, String triggerContent) {
        this.aiConfidence = confidence;
        this.triggerContent = triggerContent;
    }

    // 更新用户信息
    public void updateUserInfo(String userId, String username) {
        this.userId = userId;
        this.username = username;
    }

    // 更新主播信息
    public void updateStreamerInfo(String streamerName) {
        this.streamerName = streamerName;
    }
}