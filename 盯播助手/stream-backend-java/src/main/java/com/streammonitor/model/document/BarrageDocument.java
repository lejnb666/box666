package com.streammonitor.model.document;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.index.TextIndexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 弹幕数据文档 - MongoDB存储
 * 用于替代MySQL的barrage_data表，支持TTL自动过期
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "barrage_data")
@CompoundIndex(name = "platform_room_timestamp_index", def = "{'platform': 1, 'roomId': 1, 'timestamp': -1}")
@CompoundIndex(name = "user_timestamp_index", def = "{'userId': 1, 'timestamp': -1}")
public class BarrageDocument {

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

    @Field("user_id")
    @Indexed
    private String userId;

    @Indexed
    private String username;

    @TextIndexed
    private String content;

    @Indexed
    private LocalDateTime timestamp;

    @Field("created_at")
    private LocalDateTime createdAt;

    private String type; // danmu, gift, welcome, etc.

    @Field("raw_data")
    private Map<String, Object> rawData;

    // 弹幕元数据
    @Field("user_level")
    private Integer userLevel;

    @Field("medal_level")
    private Integer medalLevel;

    @Field("medal_name")
    private String medalName;

    @Field("medal_room")
    private String medalRoom;

    @Field("is_admin")
    private Boolean isAdmin;

    @Field("is_vip")
    private Boolean isVip;

    // 礼物相关字段
    @Field("gift_name")
    private String giftName;

    @Field("gift_count")
    private Integer giftCount;

    @Field("gift_price")
    private Double giftPrice;

    // 构造方法
    public BarrageDocument(String platform, String roomId, String userId, String username,
                          String content, String type, LocalDateTime timestamp) {
        this.platform = platform;
        this.roomId = roomId;
        this.userId = userId;
        this.username = username;
        this.content = content;
        this.type = type;
        this.timestamp = timestamp;
        this.createdAt = LocalDateTime.now();
    }

    // 更新统计信息的方法
    public void updateMetadata(Integer userLevel, Integer medalLevel, String medalName,
                              String medalRoom, Boolean isAdmin, Boolean isVip) {
        this.userLevel = userLevel;
        this.medalLevel = medalLevel;
        this.medalName = medalName;
        this.medalRoom = medalRoom;
        this.isAdmin = isAdmin != null ? isAdmin : false;
        this.isVip = isVip != null ? isVip : false;
    }

    // 更新礼物信息
    public void updateGiftInfo(String giftName, Integer giftCount, Double giftPrice) {
        this.giftName = giftName;
        this.giftCount = giftCount != null ? giftCount : 1;
        this.giftPrice = giftPrice;
    }
}