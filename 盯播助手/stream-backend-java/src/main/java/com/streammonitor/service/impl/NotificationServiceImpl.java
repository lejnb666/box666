package com.streammonitor.service.impl;

import com.alibaba.fastjson2.JSONObject;
import com.streammonitor.config.AppConfig;
import com.streammonitor.dto.NotificationDTO;
import com.streammonitor.model.entity.PushLog;
import com.streammonitor.model.entity.UserInfo;
import com.streammonitor.repository.PushLogRepository;
import com.streammonitor.service.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * 通知服务实现类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationServiceImpl implements NotificationService {

    private final RestTemplate restTemplate;
    private final StringRedisTemplate stringRedisTemplate;
    private final PushLogRepository pushLogRepository;
    private final AppConfig appConfig;

    @Value("${app.config.wechat.app-id}")
    private String wechatAppId;

    @Value("${app.config.wechat.app-secret}")
    private String wechatAppSecret;

    private static final String WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token";
    private static final String WECHAT_TEMPLATE_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send";
    private static final String WECHAT_SUBSCRIBE_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send";
    private static final String REDIS_TOKEN_KEY = "wechat:access_token";
    private static final long TOKEN_EXPIRE_BUFFER = 60L; // 提前60秒刷新

    @Override
    public boolean sendWeChatTemplateMessage(NotificationDTO notification) {
        try {
            // 获取access_token
            String accessToken = getWeChatAccessToken();
            if (accessToken == null) {
                log.error("获取微信access_token失败");
                return false;
            }

            // 构建模板消息数据
            Map<String, Object> messageData = buildTemplateMessageData(notification);

            // 发送模板消息
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(messageData, headers);

            String url = WECHAT_TEMPLATE_URL + "?access_token=" + accessToken;

            var response = restTemplate.postForEntity(url, request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                JSONObject jsonResponse = JSONObject.parseObject(responseBody);

                if (jsonResponse.getInteger("errcode") == 0) {
                    log.info("微信模板消息发送成功: {}", notification.getOpenid());

                    // 记录发送日志
                    savePushLog(notification, true, "发送成功");
                    return true;
                } else {
                    String errorMsg = jsonResponse.getString("errmsg");
                    log.error("微信模板消息发送失败: {} - {}", jsonResponse.getInteger("errcode"), errorMsg);

                    // 记录发送日志
                    savePushLog(notification, false, errorMsg);
                    return false;
                }
            } else {
                log.error("微信模板消息请求失败: {}", response.getStatusCode());
                savePushLog(notification, false, "HTTP请求失败");
                return false;
            }

        } catch (Exception e) {
            log.error("发送微信模板消息异常", e);
            savePushLog(notification, false, e.getMessage());
            return false;
        }
    }

    @Override
    public boolean sendWeChatSubscribeMessage(NotificationDTO notification) {
        try {
            // 获取access_token
            String accessToken = getWeChatAccessToken();
            if (accessToken == null) {
                log.error("获取微信access_token失败");
                return false;
            }

            // 构建订阅消息数据
            Map<String, Object> messageData = buildSubscribeMessageData(notification);

            // 发送订阅消息
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(messageData, headers);

            String url = WECHAT_SUBSCRIBE_URL + "?access_token=" + accessToken;

            var response = restTemplate.postForEntity(url, request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                JSONObject jsonResponse = JSONObject.parseObject(responseBody);

                if (jsonResponse.getInteger("errcode") == 0) {
                    log.info("微信订阅消息发送成功: {}", notification.getOpenid());

                    // 记录发送日志
                    savePushLog(notification, true, "发送成功");
                    return true;
                } else {
                    String errorMsg = jsonResponse.getString("errmsg");
                    log.error("微信订阅消息发送失败: {} - {}", jsonResponse.getInteger("errcode"), errorMsg);

                    // 记录发送日志
                    savePushLog(notification, false, errorMsg);
                    return false;
                }
            } else {
                log.error("微信订阅消息请求失败: {}", response.getStatusCode());
                savePushLog(notification, false, "HTTP请求失败");
                return false;
            }

        } catch (Exception e) {
            log.error("发送微信订阅消息异常", e);
            savePushLog(notification, false, e.getMessage());
            return false;
        }
    }

    @Override
    public boolean sendSMSMessage(NotificationDTO notification) {
        // TODO: 实现短信发送逻辑
        // 这里可以集成阿里云短信、腾讯云短信等第三方服务
        log.warn("短信发送功能尚未实现");
        savePushLog(notification, false, "短信发送功能未实现");
        return false;
    }

    @Override
    public boolean sendEmailMessage(NotificationDTO notification) {
        // TODO: 实现邮件发送逻辑
        // 这里可以集成JavaMail、阿里云邮件等第三方服务
        log.warn("邮件发送功能尚未实现");
        savePushLog(notification, false, "邮件发送功能未实现");
        return false;
    }

    @Override
    public boolean sendNotification(NotificationDTO notification) {
        boolean success = false;
        String methods = notification.getNotificationMethod();

        if (methods.contains("wechat")) {
            success |= sendWeChatSubscribeMessage(notification);
        }

        if (methods.contains("sms")) {
            success |= sendSMSMessage(notification);
        }

        if (methods.contains("email")) {
            success |= sendEmailMessage(notification);
        }

        return success;
    }

    /**
     * 获取微信access_token
     */
    private String getWeChatAccessToken() {
        try {
            // 先从Redis获取
            String cachedToken = stringRedisTemplate.opsForValue().get(REDIS_TOKEN_KEY);
            if (cachedToken != null) {
                return cachedToken;
            }

            // 调用微信API获取token
            String url = WECHAT_TOKEN_URL + "?grant_type=client_credential&appid=" +
                        wechatAppId + "&secret=" + wechatAppSecret;

            var response = restTemplate.getForEntity(url, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                String responseBody = response.getBody();
                JSONObject jsonResponse = JSONObject.parseObject(responseBody);

                if (jsonResponse.containsKey("access_token")) {
                    String accessToken = jsonResponse.getString("access_token");
                    int expiresIn = jsonResponse.getInteger("expires_in");

                    // 缓存access_token（提前60秒过期）
                    stringRedisTemplate.opsForValue().set(
                        REDIS_TOKEN_KEY,
                        accessToken,
                        expiresIn - TOKEN_EXPIRE_BUFFER,
                        TimeUnit.SECONDS
                    );

                    log.info("获取微信access_token成功");
                    return accessToken;
                } else {
                    String errorMsg = jsonResponse.getString("errmsg");
                    log.error("获取微信access_token失败: {}", errorMsg);
                    return null;
                }
            } else {
                log.error("获取微信access_token请求失败: {}", response.getStatusCode());
                return null;
            }

        } catch (Exception e) {
            log.error("获取微信access_token异常", e);
            return null;
        }
    }

    /**
     * 构建模板消息数据
     */
    private Map<String, Object> buildTemplateMessageData(NotificationDTO notification) {
        Map<String, Object> data = new HashMap<>();

        data.put("touser", notification.getOpenid());
        data.put("template_id", getTemplateId(notification.getTriggerType()));
        data.put("url", notification.getUrl());
        data.put("miniprogram", null); // 小程序跳转参数

        // 构建消息内容
        Map<String, Map<String, String>> messageContent = new HashMap<>();

        // 标题
        Map<String, String> title = new HashMap<>();
        title.put("value", notification.getTitle());
        title.put("color", "#173177");
        messageContent.put("first", title);

        // 关键词1：触发类型
        Map<String, String> keyword1 = new HashMap<>();
        keyword1.put("value", getTriggerTypeName(notification.getTriggerType()));
        keyword1.put("color", "#173177");
        messageContent.put("keyword1", keyword1);

        // 关键词2：主播名称
        Map<String, String> keyword2 = new HashMap<>();
        keyword2.put("value", notification.getStreamerName());
        keyword2.put("color", "#173177");
        messageContent.put("keyword2", keyword2);

        // 关键词3：触发时间
        Map<String, String> keyword3 = new HashMap<>();
        keyword3.put("value", LocalDateTime.now().toString().replace("T", " "));
        keyword3.put("color", "#173177");
        messageContent.put("keyword3", keyword3);

        // 备注
        Map<String, String> remark = new HashMap<>();
        remark.put("value", notification.getContent());
        remark.put("color", "#173177");
        messageContent.put("remark", remark);

        data.put("data", messageContent);

        return data;
    }

    /**
     * 构建订阅消息数据
     */
    private Map<String, Object> buildSubscribeMessageData(NotificationDTO notification) {
        Map<String, Object> data = new HashMap<>();

        data.put("touser", notification.getOpenid());
        data.put("template_id", getTemplateId(notification.getTriggerType()));
        data.put("page", notification.getUrl());

        // 构建消息内容
        Map<String, Object> messageContent = new HashMap<>();

        // 第一行内容
        Map<String, String> first = new HashMap<>();
        first.put("value", notification.getTitle());
        messageContent.put("first", first);

        // 触发类型
        Map<String, String> eventType = new HashMap<>();
        eventType.put("value", getTriggerTypeName(notification.getTriggerType()));
        messageContent.put("eventType", eventType);

        // 主播名称
        Map<String, String> streamerName = new HashMap<>();
        streamerName.put("value", notification.getStreamerName());
        messageContent.put("streamerName", streamerName);

        // 触发时间
        Map<String, String> triggerTime = new HashMap<>();
        triggerTime.put("value", LocalDateTime.now().toString().replace("T", " "));
        messageContent.put("triggerTime", triggerTime);

        // 详细内容
        Map<String, String> content = new HashMap<>();
        content.put("value", notification.getContent());
        messageContent.put("content", content);

        data.put("data", messageContent);

        return data;
    }

    /**
     * 获取模板ID
     */
    private String getTemplateId(String triggerType) {
        switch (triggerType) {
            case "live_start":
                return appConfig.getWechat().getTemplateIds().getLiveStart();
            case "product_launch":
                return appConfig.getWechat().getTemplateIds().getProductLaunch();
            case "keyword_match":
                return appConfig.getWechat().getTemplateIds().getKeywordMatch();
            default:
                return appConfig.getWechat().getTemplateIds().getLiveStart(); // 默认使用开播模板
        }
    }

    /**
     * 获取触发类型名称
     */
    private String getTriggerTypeName(String triggerType) {
        switch (triggerType) {
            case "live_start":
                return "主播开播";
            case "product_launch":
                return "商品上架";
            case "keyword_match":
                return "关键词匹配";
            case "lottery":
                return "抽奖活动";
            case "discount":
                return "降价促销";
            default:
                return "直播监控";
        }
    }

    /**
     * 保存推送日志
     */
    private void savePushLog(NotificationDTO notification, boolean success, String errorMessage) {
        try {
            PushLog pushLog = new PushLog();
            pushLog.setUserId(notification.getUserId());
            pushLog.setTaskId(notification.getTaskId());
            pushLog.setStreamerConfigId(notification.getStreamerConfigId());
            pushLog.setTriggerType(notification.getTriggerType());
            pushLog.setTriggerContent(notification.getContent());
            pushLog.setNotificationMethod(notification.getNotificationMethod());
            pushLog.setMessageTitle(notification.getTitle());
            pushLog.setMessageContent(notification.getContent());
            pushLog.setAiConfidence(notification.getAiConfidence());
            pushLog.setStatus(success ? (byte) 1 : (byte) 0);
            pushLog.setErrorMessage(errorMessage);
            pushLog.setSentAt(LocalDateTime.now());

            pushLogRepository.insert(pushLog);

        } catch (Exception e) {
            log.error("保存推送日志失败", e);
        }
    }
}