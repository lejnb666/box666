package com.streammonitor.service;

import com.streammonitor.dto.UserLoginDTO;
import com.streammonitor.model.entity.UserInfo;

import java.util.Optional;

/**
 * 用户信息服务接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface UserInfoService {

    /**
     * 微信登录
     *
     * @param loginDTO 登录信息
     * @return 用户信息和JWT token
     */
    Object wechatLogin(UserLoginDTO loginDTO);

    /**
     * 根据OpenID获取用户信息
     *
     * @param openid 微信OpenID
     * @return 用户信息
     */
    Optional<UserInfo> getUserByOpenid(String openid);

    /**
     * 创建或更新用户信息
     *
     * @param userInfo 用户信息
     * @return 用户信息
     */
    UserInfo createOrUpdateUser(UserInfo userInfo);

    /**
     * 根据ID获取用户信息
     *
     * @param userId 用户ID
     * @return 用户信息
     */
    Optional<UserInfo> getUserById(Long userId);

    /**
     * 更新用户信息
     *
     * @param userInfo 用户信息
     * @return 更新结果
     */
    boolean updateUser(UserInfo userInfo);

    /**
     * 处理用户数据库逻辑（带事务）
     *
     * @param openid 微信OpenID
     * @param loginDTO 登录信息
     * @return 用户信息
     */
    UserInfo processUserDatabaseLogic(String openid, UserLoginDTO loginDTO);

    /**
     * 禁用用户
     *
     * @param userId 用户ID
     * @return 更新结果
     */
    boolean disableUser(Long userId);
}