package com.streammonitor.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 应用配置类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
@Component
@ConfigurationProperties(prefix = "app.config")
public class AppConfig {

    /**
     * JWT配置
     */
    private JwtConfig jwt = new JwtConfig();

    /**
     * 微信配置
     */
    private WechatConfig wechat = new WechatConfig();

    /**
     * AI服务配置
     */
    private AiConfig ai = new AiConfig();

    /**
     * 爬虫配置
     */
    private CrawlerConfig crawler = new CrawlerConfig();

    /**
     * 通知配置
     */
    private NotificationConfig notification = new NotificationConfig();

    @Data
    public static class JwtConfig {
        private String secret;
        private long expiration;
        private long refreshExpiration;
    }

    @Data
    public static class WechatConfig {
        private String appId;
        private String appSecret;
        private TemplateIds templateIds = new TemplateIds();

        @Data
        public static class TemplateIds {
            private String liveStart;
            private String productLaunch;
            private String keywordMatch;
        }
    }

    @Data
    public static class AiConfig {
        private String apiBaseUrl;
        private String apiKey;
        private String modelName;
        private int timeout;
    }

    @Data
    public static class CrawlerConfig {
        private int interval;
        private int barrageBufferSize;
        private int maxConcurrentTasks;
    }

    @Data
    public static class NotificationConfig {
        private int rateLimit;
        private int retryCount;
        private int retryInterval;
    }
}