package com.streammonitor.model.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.time.LocalTime;

/**
 * 监控任务实体类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("monitor_task")
public class MonitorTask implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 任务ID
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    @TableField("user_id")
    private Long userId;

    /**
     * 主播配置ID
     */
    @TableField("streamer_config_id")
    private Long streamerConfigId;

    /**
     * 任务类型：live_start、product_launch、keyword_match等
     */
    @TableField("task_type")
    private String taskType;

    /**
     * 监控关键词，JSON格式
     */
    @TableField("keywords")
    private String keywords;

    /**
     * 是否启用AI分析：0-否，1-是
     */
    @TableField("ai_analysis")
    private Integer aiAnalysis;

    /**
     * 通知方式：wechat、sms、email
     */
    @TableField("notification_methods")
    private String notificationMethods;

    /**
     * 免打扰开始时间
     */
    @TableField("do_not_disturb_start")
    private LocalTime doNotDisturbStart;

    /**
     * 免打扰结束时间
     */
    @TableField("do_not_disturb_end")
    private LocalTime doNotDisturbEnd;

    /**
     * 状态：0-暂停，1-运行中，2-已完成
     */
    @TableField("status")
    private Integer status;

    /**
     * 最后触发时间
     */
    @TableField("last_triggered_at")
    private LocalDateTime lastTriggeredAt;

    /**
     * 触发次数
     */
    @TableField("trigger_count")
    private Integer triggerCount;

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

    // 关联字段（非数据库字段）
    @TableField(exist = false)
    private String streamerName;

    @TableField(exist = false)
    private String platform;
}