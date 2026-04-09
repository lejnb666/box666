package com.streammonitor.controller;

import com.streammonitor.common.Result;
import com.streammonitor.dto.UserLoginDTO;
import com.streammonitor.model.entity.UserInfo;
import com.streammonitor.service.UserInfoService;
import com.streammonitor.utils.JwtUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

/**
 * 用户管理控制器
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@RestController
@RequestMapping("/user")
@RequiredArgsConstructor
@Validated
public class UserController {

    private final UserInfoService userInfoService;
    private final JwtUtils jwtUtils;
    private final StringRedisTemplate stringRedisTemplate;

    /**
     * 微信登录
     */
    @PostMapping("/login")
    public Result<?> wechatLogin(@Valid @RequestBody UserLoginDTO loginDTO) {
        try {
            log.info("用户微信登录，code: {}", loginDTO.getCode());
            return (Result<?>) userInfoService.wechatLogin(loginDTO);
        } catch (Exception e) {
            log.error("微信登录异常", e);
            return Result.error("登录失败，请稍后重试");
        }
    }

    /**
     * 获取当前用户信息
     */
    @GetMapping("/profile")
    public Result<UserInfo> getUserProfile(@RequestAttribute("userId") Long userId) {
        try {
            Optional<UserInfo> userInfo = userInfoService.getUserById(userId);
            return userInfo.map(Result::success)
                    .orElse(Result.fail("用户不存在"));
        } catch (Exception e) {
            log.error("获取用户信息异常", e);
            return Result.error("获取用户信息失败");
        }
    }

    /**
     * 更新用户信息
     */
    @PutMapping("/profile")
    public Result<UserInfo> updateUserProfile(@RequestAttribute("userId") Long userId,
                                              @Valid @RequestBody UserInfo userInfo) {
        try {
            userInfo.setId(userId);
            boolean success = userInfoService.updateUser(userInfo);
            if (success) {
                return Result.success("更新成功", userInfo);
            } else {
                return Result.fail("更新失败");
            }
        } catch (Exception e) {
            log.error("更新用户信息异常", e);
            return Result.error("更新用户信息失败");
        }
    }

    /**
     * 退出登录
     */
    @PostMapping("/logout")
    public Result<?> logout(@RequestAttribute("userId") Long userId) {
        try {
            // 这里可以添加清除缓存、记录登出日志等逻辑
            log.info("用户退出登录，userId: {}", userId);
            return Result.success("退出成功");
        } catch (Exception e) {
            log.error("退出登录异常", e);
            return Result.error("退出失败");
        }
    }

    /**
     * 获取用户统计信息
     */
    @GetMapping("/stats")
    public Result<Object> getUserStats(@RequestAttribute("userId") Long userId) {
        try {
            // 这里可以返回用户的监控任务数量、触发次数等统计信息
            // 实际实现中需要调用相应的服务方法
            return Result.success("获取成功", new Object());
        } catch (Exception e) {
            log.error("获取用户统计信息异常", e);
            return Result.error("获取统计信息失败");
        }
    }

    /**
     * 刷新Token
     */
    @PostMapping("/refresh-token")
    public Result<Map<String, Object>> refreshToken(@RequestHeader("Refresh-Token") String refreshToken) {
        try {
            log.info("开始刷新Token");

            // 1. 验证Refresh Token的有效性
            if (refreshToken == null || refreshToken.trim().isEmpty()) {
                return Result.fail("Refresh Token不能为空");
            }

            // 2. 检查Redis中该Token是否被加入黑名单
            String blacklistKey = "token:blacklist:" + refreshToken;
            Boolean isBlacklisted = stringRedisTemplate.hasKey(blacklistKey);
            if (Boolean.TRUE.equals(isBlacklisted)) {
                log.warn("尝试使用已加入黑名单的Refresh Token");
                return Result.fail("Token已失效，请重新登录");
            }

            // 3. 验证Refresh Token是否有效
            if (!jwtUtils.validateRefreshToken(refreshToken)) {
                return Result.fail("Refresh Token无效或已过期");
            }

            // 4. 从Refresh Token中提取用户信息
            String userId = jwtUtils.getUserIdFromToken(refreshToken);

            // 5. 检查用户是否存在
            Optional<UserInfo> userOpt = userInfoService.getUserById(Long.valueOf(userId));
            if (!userOpt.isPresent()) {
                return Result.fail("用户不存在");
            }

            UserInfo user = userOpt.get();
            if (user.getStatus() == 0) {
                return Result.fail("用户已被禁用");
            }

            // 6. 生成新的AccessToken
            String newAccessToken = jwtUtils.generateToken(userId);

            // 7. 将旧的Refresh Token加入黑名单（一次性使用）
            stringRedisTemplate.opsForValue().set(blacklistKey, "1", jwtUtils.getRefreshExpiration(), TimeUnit.MILLISECONDS);

            // 8. 生成新的Refresh Token
            String newRefreshToken = jwtUtils.generateRefreshToken(userId);

            // 9. 返回新的Token对
            Map<String, Object> result = new HashMap<>();
            result.put("accessToken", newAccessToken);
            result.put("refreshToken", newRefreshToken);
            result.put("expiresIn", jwtUtils.getExpiration());
            result.put("refreshExpiresIn", jwtUtils.getRefreshExpiration());

            log.info("Token刷新成功，用户ID: {}", userId);
            return Result.success("Token刷新成功", result);

        } catch (Exception e) {
            log.error("Token刷新异常", e);
            return Result.error("Token刷新失败，请重新登录");
        }
    }
}