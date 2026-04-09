package com.streammonitor.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.io.Serializable;

/**
 * 用户登录DTO
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
public class UserLoginDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 微信小程序登录code
     */
    @NotBlank(message = "登录code不能为空")
    private String code;

    /**
     * 用户昵称
     */
    private String nickname;

    /**
     * 用户头像URL
     */
    private String avatarUrl;

    /**
     * 手机号
     */
    private String phone;
}