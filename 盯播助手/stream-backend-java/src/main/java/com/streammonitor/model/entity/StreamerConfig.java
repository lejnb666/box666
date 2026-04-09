package com.streammonitor.model.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 主播配置实体类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("streamer_config")
public class StreamerConfig implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 配置ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 主播ID
     */
    @TableField("streamer_id")
    private String streamerId;

    /**
     * 平台：bilibili、douyu、huya等
     */
    @TableField("platform")
    private String platform;

    /**
     * 房间ID
     */
    @TableField("room_id")
    private String roomId;

    /**
     * 主播名称
     */
    @TableField("streamer_name")
    private String streamerName;

    /**
     * 主播头像
     */
    @TableField("avatar_url")
    private String avatarUrl;

    /**
     * 直播分类
     */
    @TableField("category")
    private String category;

    /**
     * 状态：0-禁用，1-正常
     */
    @TableField("status")
    private Integer status;

    /**
     * 创建时间
     */
    @TableField(value = "created_at", fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    /**
     * 更新时间
     */
    @TableField(value = "updated_at", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}