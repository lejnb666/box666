package com.streammonitor.service;

import com.streammonitor.dto.NotificationDTO;

/**
 * 通知服务接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface NotificationService {

    /**
     * 发送微信模板消息
     *
     * @param notification 通知数据
     * @return 是否发送成功
     */
    boolean sendWeChatTemplateMessage(NotificationDTO notification);

    /**
     * 发送微信订阅消息
     *
     * @param notification 通知数据
     * @return 是否发送成功
     */
    boolean sendWeChatSubscribeMessage(NotificationDTO notification);

    /**
     * 发送短信消息
     *
     * @param notification 通知数据
     * @return 是否发送成功
     */
    boolean sendSMSMessage(NotificationDTO notification);

    /**
     * 发送邮件消息
     *
     * @param notification 通知数据
     * @return 是否发送成功
     */
    boolean sendEmailMessage(NotificationDTO notification);

    /**
     * 发送通知（多渠道）
     *
     * @param notification 通知数据
     * @return 是否至少有一个渠道发送成功
     */
    boolean sendNotification(NotificationDTO notification);
}