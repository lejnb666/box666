package com.streammonitor.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.io.Serializable;
import java.time.LocalTime;

/**
 * 监控任务DTO
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
public class MonitorTaskDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 任务ID（更新时使用）
     */
    private Long id;

    /**
     * 主播配置ID
     */
    @NotNull(message = "主播配置ID不能为空")
    private Long streamerConfigId;

    /**
     * 任务类型：live_start、product_launch、keyword_match等
     */
    @NotBlank(message = "任务类型不能为空")
    private String taskType;

    /**
     * 监控关键词，多个关键词用逗号分隔
     */
    private String keywords;

    /**
     * 是否启用AI分析：0-否，1-是
     */
    private Integer aiAnalysis = 0;

    /**
     * 通知方式：wechat、sms、email，多个用逗号分隔
     */
    private String notificationMethods = "wechat";

    /**
     * 免打扰开始时间
     */
    private LocalTime doNotDisturbStart;

    /**
     * 免打扰结束时间
     */
    private LocalTime doNotDisturbEnd;

    /**
     * 状态：0-暂停，1-运行中
     */
    private Integer status = 1;
}