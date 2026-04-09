package com.streammonitor.model.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Date;

/**
 * 监控任务实体类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@TableName("monitoring_tasks")
public class MonitoringTask implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 用户ID
     */
    @TableField("user_id")
    private Long userId;

    /**
     * 平台（bilibili, douyu, huya, douyin）
     */
    @TableField("platform")
    private String platform;

    /**
     * 房间号
     */
    @TableField("room_id")
    private String roomId;

    /**
     * 主播名称
     */
    @TableField("streamer_name")
    private String streamerName;

    /**
     * 任务类型（live_start, product_launch, keyword_match）
     */
    @TableField("task_type")
    private String taskType;

    /**
     * 关键词（JSON格式）
     */
    @TableField("keywords")
    private String keywords;

    /**
     * 是否启用AI分析
     */
    @TableField("ai_analysis")
    private Boolean aiAnalysis = false;

    /**
     * 通知方式（JSON格式）
     */
    @TableField("notification_methods")
    private String notificationMethods;

    /**
     * 免打扰开始时间
     */
    @TableField("do_not_disturb_start")
    private String doNotDisturbStart;

    /**
     * 免打扰结束时间
     */
    @TableField("do_not_disturb_end")
    private String doNotDisturbEnd;

    /**
     * 监控间隔（秒）
     */
    @TableField("monitor_interval")
    private Integer monitorInterval = 60;

    /**
     * 调试模式
     */
    @TableField("debug_mode")
    private Boolean debugMode = false;

    /**
     * 任务状态（0: 已停止, 1: 运行中）
     */
    @TableField("status")
    private Integer status = 0;

    /**
     * 触发次数
     */
    @TableField("trigger_count")
    private Integer triggerCount = 0;

    /**
     * 最后触发时间
     */
    @TableField("last_triggered_at")
    private LocalDateTime lastTriggeredAt;

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

    /**
     * 任务描述
     */
    @TableField("description")
    private String description;

    /**
     * 主播配置ID
     */
    @TableField("streamer_config_id")
    private Long streamerConfigId;

    public MonitoringTask() {
    }

    public MonitoringTask(Long userId, String platform, String roomId, String taskType) {
        this.userId = userId;
        this.platform = platform;
        this.roomId = roomId;
        this.taskType = taskType;
        this.status = 1;
        this.triggerCount = 0;
        this.aiAnalysis = false;
        this.monitorInterval = 60;
        this.debugMode = false;
    }

    /**
     * 增加触发次数
     */
    public void incrementTriggerCount() {
        this.triggerCount = (this.triggerCount == null ? 0 : this.triggerCount) + 1;
        this.lastTriggeredAt = LocalDateTime.now();
    }

    /**
     * 检查是否在免打扰时间
     */
    public boolean isInDoNotDisturbTime() {
        if (doNotDisturbStart == null || doNotDisturbEnd == null) {
            return false;
        }

        LocalDateTime now = LocalDateTime.now();
        int currentHour = now.getHour();
        int currentMinute = now.getMinute();

        // 解析免打扰时间
        String[] startParts = doNotDisturbStart.split(":");
        String[] endParts = doNotDisturbEnd.split(":");

        if (startParts.length != 2 || endParts.length != 2) {
            return false;
        }

        int startHour = Integer.parseInt(startParts[0]);
        int startMinute = Integer.parseInt(startParts[1]);
        int endHour = Integer.parseInt(endParts[0]);
        int endMinute = Integer.parseInt(endParts[1]);

        int currentTimeInMinutes = currentHour * 60 + currentMinute;
        int startTimeInMinutes = startHour * 60 + startMinute;
        int endTimeInMinutes = endHour * 60 + endMinute;

        if (startTimeInMinutes <= endTimeInMinutes) {
            // 同一天的时间段
            return currentTimeInMinutes >= startTimeInMinutes && currentTimeInMinutes <= endTimeInMinutes;
        } else {
            // 跨天的时间段
            return currentTimeInMinutes >= startTimeInMinutes || currentTimeInMinutes <= endTimeInMinutes;
        }
    }

    @Override
    public String toString() {
        return "MonitoringTask{" +
                "id=" + id +
                ", userId=" + userId +
                ", platform='" + platform + '\'' +
                ", roomId='" + roomId + '\'' +
                ", taskType='" + taskType + '\'' +
                ", status=" + status +
                ", triggerCount=" + triggerCount +
                '}';
    }
}