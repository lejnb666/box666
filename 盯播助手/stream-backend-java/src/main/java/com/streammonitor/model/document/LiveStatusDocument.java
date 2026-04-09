package com.streammonitor.model.document;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.time.LocalDateTime;

/**
 * 直播状态记录文档 - MongoDB存储
 * 替代MySQL的live_status_log表，支持TTL自动过期
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@NoArgsConstructor
@@AllArgsConstructor
@Document(collection = "live_status_log")
@CompoundIndex(name = "live_status_query_index", def = "{'platform': 1, 'roomId': 1, 'timestamp': -1}")
public class LiveStatusDocument {

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

    @Indexed
    private Integer status; // 0-未开播，1-直播中，2-停播

    private String title;

    private String category;

    @Field("viewer_count")
    private Integer viewerCount;

    @Field("start_time")
    private LocalDateTime startTime;

    @Field("end_time")
    private LocalDateTime endTime;

    @Indexed
    private LocalDateTime timestamp;

    @Field("recorded_at")
    private LocalDateTime recordedAt;

    @Field("streamer_name")
    private String streamerName;

    @Field("avatar_url")
    private String avatarUrl;

    // 构造方法
    public LiveStatusDocument(String platform, String roomId, Integer status,
                             String title, String category, Integer viewerCount) {
        this.platform = platform;
        this.roomId = roomId;
        this.status = status;
        this.title = title;
        this.category = category;
        this.viewerCount = viewerCount != null ? viewerCount : 0;
        this.timestamp = LocalDateTime.now();
        this.recordedAt = LocalDateTime.now();
    }

    // 更新直播时间
    public void updateLiveTime(LocalDateTime startTime, LocalDateTime endTime) {
        this.startTime = startTime;
        this.endTime = endTime;
    }

    // 更新主播信息
    public void updateStreamerInfo(String streamerName, String avatarUrl) {
        this.streamerName = streamerName;
        this.avatarUrl = avatarUrl;
    }
}