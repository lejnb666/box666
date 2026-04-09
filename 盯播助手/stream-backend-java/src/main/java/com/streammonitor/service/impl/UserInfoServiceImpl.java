package com.streammonitor.service.impl;

import com.alibaba.fastjson2.JSONObject;
import com.streammonitor.common.Result;
import com.streammonitor.common.ResultCode;
import com.streammonitor.config.AppConfig;
import com.streammonitor.dto.UserLoginDTO;
import com.streammonitor.model.entity.UserInfo;
import com.streammonitor.repository.UserInfoRepository;
import com.streammonitor.service.UserInfoService;
import com.streammonitor.utils.JwtUtils;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.aop.framework.AopContext;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.sql.SQLIntegrityConstraintViolationException;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.TimeUnit;

import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;

/**
 * 用户信息服务实现类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserInfoServiceImpl implements UserInfoService {

    private final UserInfoRepository userInfoRepository;
    private final StringRedisTemplate stringRedisTemplate;
    private final RestTemplate restTemplate;
    private final JwtUtils jwtUtils;
    private final AppConfig appConfig;
    private final RedissonClient redissonClient;

    @Value("${app.config.wechat.app-id}")
    private String wechatAppId;

    @Value("${app.config.wechat.app-secret}")
    private String wechatAppSecret;

    private static final String WECHAT_LOGIN_URL = "https://api.weixin.qq.com/sns/jscode2session";
    private static final String REDIS_USER_KEY_PREFIX = "user:openid:";
    private static final String REDIS_ID_TO_OPENID_KEY_PREFIX = "user:id:openid:";
    private static final long REDIS_USER_EXPIRE = 30L; // 30天

    @Override
    public Object wechatLogin(UserLoginDTO loginDTO) {
        try {
            // 1. 无事务环境下发起网络请求，避免大事务问题
            Map<String, Object> wechatResponse = getWechatSession(loginDTO.getCode());
            if (wechatResponse == null || !wechatResponse.containsKey("openid")) {
                log.error("微信登录失败，响应: {}", wechatResponse);
                return Result.fail(ResultCode.WECHAT_API_ERROR);
            }

            String openid = (String) wechatResponse.get("openid");
            String sessionKey = (String) wechatResponse.get("session_key");

            // 2. 调用带有事务的数据库处理方法（通过AOP代理确保事务生效）
            UserInfoService proxy = (UserInfoService) AopContext.currentProxy();
            UserInfo userInfo = proxy.processUserDatabaseLogic(openid, loginDTO);

            // 生成JWT token
            String token = jwtUtils.generateToken(userInfo.getId().toString());

            // 返回登录结果
            Map<String, Object> result = new HashMap<>();
            result.put("token", token);
            result.put("user", userInfo);
            result.put("expiresIn", jwtUtils.getExpiration());

            return Result.success("登录成功", result);

        } catch (Exception e) {
            log.error("微信登录异常", e);
            return Result.error(ResultCode.ERROR);
        }
    }

    @Override
    public Optional<UserInfo> getUserByOpenid(String openid) {
        // 先从Redis缓存获取
        String cacheKey = REDIS_USER_KEY_PREFIX + openid;
        String cachedUser = stringRedisTemplate.opsForValue().get(cacheKey);

        if (StringUtils.isNotBlank(cachedUser)) {
            return Optional.of(JSONObject.parseObject(cachedUser, UserInfo.class));
        }

        // 缓存未命中，查询数据库
        Optional<UserInfo> userInfo = userInfoRepository.findByOpenid(openid);
        userInfo.ifPresent(this::cacheUserInfo);

        return userInfo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserInfo processUserDatabaseLogic(String openid, UserLoginDTO loginDTO) {
        // 使用分布式锁防止高并发下的重复创建
        RLock lock = redissonClient.getLock("user:register:" + openid);

        try {
            if (lock.tryLock(3, 10, TimeUnit.SECONDS)) {
                // 双重检查，防止在等待锁的过程中其他线程已创建用户
                Optional<UserInfo> existingUser = getUserByOpenid(openid);
                UserInfo userInfo;

                if (existingUser.isPresent()) {
                    // 更新现有用户
                    userInfo = existingUser.get();
                    updateUserInfo(userInfo, loginDTO);
                    userInfoRepository.updateById(userInfo);
                } else {
                    // 创建新用户
                    userInfo = createNewUser(openid, loginDTO);
                }

                // 缓存用户信息
                cacheUserInfo(userInfo);

                return userInfo;
            } else {
                throw new RuntimeException(ResultCode.REQUEST_FREQUENT.getMessage());
            }
        } catch (SQLIntegrityConstraintViolationException e) {
            // 处理唯一约束冲突（极端情况下的并发安全兜底）
            log.warn("检测到重复用户创建，openid: {}, 错误: {}", openid, e.getMessage());

            // 重新查询用户信息
            Optional<UserInfo> existingUser = getUserByOpenid(openid);
            if (existingUser.isPresent()) {
                UserInfo userInfo = existingUser.get();
                updateUserInfo(userInfo, loginDTO);
                userInfoRepository.updateById(userInfo);
                cacheUserInfo(userInfo);
                return userInfo;
            } else {
                throw new RuntimeException("用户创建失败，请重试", e);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException(ResultCode.REQUEST_FREQUENT.getMessage());
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UserInfo createOrUpdateUser(UserInfo userInfo) {
        if (userInfo.getId() == null) {
            // 创建新用户
            userInfo.setStatus(1);
            userInfo.setCreatedAt(LocalDateTime.now());
            userInfo.setUpdatedAt(LocalDateTime.now());
            userInfoRepository.insert(userInfo);
        } else {
            // 更新用户
            userInfo.setUpdatedAt(LocalDateTime.now());
            userInfoRepository.updateById(userInfo);
        }

        // 更新缓存
        cacheUserInfo(userInfo);

        return userInfo;
    }

    @Override
    public Optional<UserInfo> getUserById(Long userId) {
        return Optional.ofNullable(userInfoRepository.selectById(userId));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean updateUser(UserInfo userInfo) {
        userInfo.setUpdatedAt(LocalDateTime.now());
        boolean result = userInfoRepository.updateById(userInfo) > 0;

        if (result) {
            // 更新缓存
            cacheUserInfo(userInfo);
        }

        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean disableUser(Long userId) {
        UserInfo userInfo = new UserInfo();
        userInfo.setId(userId);
        userInfo.setStatus(0);
        userInfo.setUpdatedAt(LocalDateTime.now());

        boolean result = userInfoRepository.updateById(userInfo) > 0;

        if (result) {
            // 清除缓存
            clearUserCache(userId);
        }

        return result;
    }

    /**
     * 调用微信API获取session
     */
    private Map<String, Object> getWechatSession(String code) {
        try {
            String url = WECHAT_LOGIN_URL + "?appid=" + wechatAppId +
                    "&secret=" + wechatAppSecret +
                    "&js_code=" + code +
                    "&grant_type=authorization_code";

            ResponseEntity<String> response = restTemplate.getForEntity(url, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                return JSONObject.parseObject(response.getBody(), Map.class);
            }
        } catch (Exception e) {
            log.error("调用微信API异常", e);
        }
        return null;
    }

    /**
     * 创建新用户
     */
    private UserInfo createNewUser(String openid, UserLoginDTO loginDTO) {
        UserInfo userInfo = new UserInfo();
        userInfo.setOpenid(openid);
        updateUserInfo(userInfo, loginDTO);
        userInfo.setStatus(1);
        userInfo.setCreatedAt(LocalDateTime.now());
        userInfo.setUpdatedAt(LocalDateTime.now());
        userInfoRepository.insert(userInfo);
        return userInfo;
    }

    /**
     * 更新用户信息
     */
    private void updateUserInfo(UserInfo userInfo, UserLoginDTO loginDTO) {
        if (StringUtils.isNotBlank(loginDTO.getNickname())) {
            userInfo.setNickname(loginDTO.getNickname());
        }
        if (StringUtils.isNotBlank(loginDTO.getAvatarUrl())) {
            userInfo.setAvatarUrl(loginDTO.getAvatarUrl());
        }
        if (StringUtils.isNotBlank(loginDTO.getPhone())) {
            userInfo.setPhone(loginDTO.getPhone());
        }
        userInfo.setUpdatedAt(LocalDateTime.now());
    }

    /**
     * 缓存用户信息
     */
    private void cacheUserInfo(UserInfo userInfo) {
        if (userInfo.getOpenid() != null && userInfo.getId() != null) {
            // 缓存用户信息
            String cacheKey = REDIS_USER_KEY_PREFIX + userInfo.getOpenid();
            String userJson = JSONObject.toJSONString(userInfo);
            stringRedisTemplate.opsForValue().set(cacheKey, userJson, REDIS_USER_EXPIRE, TimeUnit.DAYS);

            // 缓存ID到openid的映射，便于反向查找
            String idToOpenidKey = REDIS_ID_TO_OPENID_KEY_PREFIX + userInfo.getId();
            stringRedisTemplate.opsForValue().set(idToOpenidKey, userInfo.getOpenid(), REDIS_USER_EXPIRE, TimeUnit.DAYS);

            log.debug("用户信息缓存成功，userId: {}, openid: {}", userInfo.getId(), userInfo.getOpenid());
        }
    }

    /**
     * 清除用户缓存
     */
    private void clearUserCache(Long userId) {
        try {
            // 根据用户ID查询用户信息获取openid
            Optional<UserInfo> userInfo = getUserById(userId);
            if (userInfo.isPresent() && userInfo.get().getOpenid() != null) {
                String openid = userInfo.get().getOpenid();
                String cacheKey = REDIS_USER_KEY_PREFIX + openid;

                // 删除Redis缓存
                Boolean deleted = stringRedisTemplate.delete(cacheKey);
                if (Boolean.TRUE.equals(deleted)) {
                    log.info("清除用户缓存成功，userId: {}, openid: {}", userId, openid);
                } else {
                    log.warn("用户缓存不存在或删除失败，userId: {}", userId);
                }

                // 同时维护ID到openid的反向映射缓存（可选优化）
                String idToOpenidKey = "user:id:openid:" + userId;
                stringRedisTemplate.delete(idToOpenidKey);
            }
        } catch (Exception e) {
            log.error("清除用户缓存失败，userId: {}", userId, e);
            // 缓存清理失败不应影响主流程，仅记录日志
        }
    }
}