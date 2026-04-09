package com.streammonitor.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.io.Serializable;

/**
 * 主播搜索DTO
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
public class StreamerSearchDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 平台：bilibili、douyu、huya等
     */
    @NotBlank(message = "平台不能为空")
    private String platform;

    /**
     * 房间ID或主播ID
     */
    @NotBlank(message = "房间ID或主播ID不能为空")
    private String roomId;

    /**
     * 主播名称（可选）
     */
    private String streamerName;
}