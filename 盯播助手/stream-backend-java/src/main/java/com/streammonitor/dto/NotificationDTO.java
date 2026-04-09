package com.streammonitor.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * 通知数据传输对象
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Data
public class NotificationDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 任务ID
     */
    private Long taskId;

    /**
     * 主播配置ID
     */
    private Long streamerConfigId;

    /**
     * 微信OpenID
     */
    private String openid;

    /**
     * 触发类型
     */
    private String triggerType;

    /**
     * 主播名称
     */
    private String streamerName;

    /**
     * 通知方式
     */
    private String notificationMethod;

    /**
     * 消息标题
     */
    private String title;

    /**
     * 消息内容
     */
    private String content;

    /**
     * AI置信度
     */
    private Float aiConfidence;

    /**
     * 跳转URL
     */
    private String url;

    /**
     * 平台
     */
    private String platform;

    /**
     * 房间号
     */
    private String roomId;

    public NotificationDTO() {
    }

    public NotificationDTO(Long userId, String openid, String triggerType, String streamerName) {
        this.userId = userId;
        this.openid = openid;
        this.triggerType = triggerType;
        this.streamerName = streamerName;
    }

    /**
     * 设置开播通知
     */
    public void setLiveStartNotification(String streamerName, String platform, String roomId) {
        this.triggerType = "live_start";
        this.streamerName = streamerName;
        this.platform = platform;
        this.roomId = roomId;
        this.title = "🔴 主播开播啦！";
        this.content = String.format("您关注的主播 %s 已经开始直播了，快来围观吧！", streamerName);
        this.url = String.format("https://live.%s.com/%s", platform, roomId);
    }

    /**
     * 设置商品上架通知
     */
    public void setProductLaunchNotification(String streamerName, String platform, String roomId, String productInfo) {
        this.triggerType = "product_launch";
        this.streamerName = streamerName;
        this.platform = platform;
        this.roomId = roomId;
        this.title = "🛍️ 商品上架提醒";
        this.content = String.format("主播 %s 上架了新商品：%s", streamerName, productInfo);
        this.url = String.format("https://live.%s.com/%s", platform, roomId);
    }

    /**
     * 设置关键词匹配通知
     */
    public void setKeywordMatchNotification(String streamerName, String platform, String roomId, String keyword, String content) {
        this.triggerType = "keyword_match";
        this.streamerName = streamerName;
        this.platform = platform;
        this.roomId = roomId;
        this.title = "🔍 关键词匹配提醒";
        this.content = String.format("检测到关键词「%s」：%s", keyword, content);
        this.url = String.format("https://live.%s.com/%s", platform, roomId);
    }

    /**
     * 设置抽奖活动通知
     */
    public void setLotteryNotification(String streamerName, String platform, String roomId) {
        this.triggerType = "lottery";
        this.streamerName = streamerName;
        this.platform = platform;
        this.roomId = roomId;
        this.title = "🎁 抽奖活动开始啦！";
        this.content = String.format("主播 %s 正在进行抽奖活动，快来参与吧！", streamerName);
        this.url = String.format("https://live.%s.com/%s", platform, roomId);
    }

    /**
     * 设置降价促销通知
     */
    public void setDiscountNotification(String streamerName, String platform, String roomId, String discountInfo) {
        this.triggerType = "discount";
        this.streamerName = streamerName;
        this.platform = platform;
        this.roomId = roomId;
        this.title = "💰 降价促销提醒";
        this.content = String.format("主播 %s 正在进行促销活动：%s", streamerName, discountInfo);
        this.url = String.format("https://live.%s.com/%s", platform, roomId);
    }
}