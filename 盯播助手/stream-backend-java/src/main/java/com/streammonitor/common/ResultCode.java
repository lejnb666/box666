package com.streammonitor.common;

/**
 * 结果状态码枚举
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public enum ResultCode {

    /**
     * 操作成功
     */
    SUCCESS(200, "操作成功"),

    /**
     * 操作失败
     */
    FAIL(400, "操作失败"),

    /**
     * 系统异常
     */
    ERROR(500, "系统异常"),

    /**
     * 参数校验失败
     */
    VALIDATE_FAILED(40001, "参数校验失败"),

    /**
     * 未认证
     */
    UNAUTHORIZED(401, "未认证或token已过期"),

    /**
     * 未授权
     */
    FORBIDDEN(403, "未授权"),

    /**
     * 资源不存在
     */
    NOT_FOUND(404, "资源不存在"),

    /**
     * 请求方法不支持
     */
    METHOD_NOT_ALLOWED(405, "请求方法不支持"),

    /**
     * 请求频繁
     */
    REQUEST_FREQUENT(429, "请求过于频繁，请稍后再试"),

    /**
     * 用户相关错误
     */
    USER_NOT_EXIST(10001, "用户不存在"),
    USER_ALREADY_EXIST(10002, "用户已存在"),
    USER_PASSWORD_ERROR(10003, "密码错误"),
    USER_DISABLED(10004, "用户已被禁用"),

    /**
     * 监控任务相关错误
     */
    TASK_NOT_EXIST(20001, "监控任务不存在"),
    TASK_ALREADY_EXIST(20002, "监控任务已存在"),
    TASK_INVALID_CONFIG(20003, "监控任务配置无效"),
    TASK_PLATFORM_NOT_SUPPORTED(20004, "暂不支持该平台"),

    /**
     * 主播相关错误
     */
    STREAMER_NOT_EXIST(30001, "主播不存在"),
    STREAMER_INVALID_ROOM_ID(30002, "无效的房间ID"),

    /**
     * 微信相关错误
     */
    WECHAT_API_ERROR(40001, "微信API调用失败"),
    WECHAT_TEMPLATE_NOT_FOUND(40002, "微信模板不存在"),
    WECHAT_SUBSCRIBE_FAILED(40003, "微信订阅消息发送失败"),

    /**
     * AI服务相关错误
     */
    AI_SERVICE_ERROR(50001, "AI服务调用失败"),
    AI_SERVICE_TIMEOUT(50002, "AI服务响应超时"),
    AI_SERVICE_UNAVAILABLE(50003, "AI服务暂时不可用"),

    /**
     * 爬虫相关错误
     */
    CRAWLER_ERROR(60001, "数据抓取失败"),
    CRAWLER_PLATFORM_BLOCKED(60002, "平台访问被限制"),
    CRAWLER_WEBSOCKET_ERROR(60003, "WebSocket连接失败"),

    /**
     * 消息队列相关错误
     */
    MQ_ERROR(70001, "消息队列操作失败"),
    MQ_CONNECTION_ERROR(70002, "消息队列连接失败");

    private final int code;
    private final String message;

    ResultCode(int code, String message) {
        this.code = code;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public String getMessage() {
        return message;
    }

    /**
     * 根据code获取枚举
     */
    public static ResultCode getByCode(int code) {
        for (ResultCode resultCode : ResultCode.values()) {
            if (resultCode.getCode() == code) {
                return resultCode;
            }
        }
        return null;
    }

    /**
     * 根据message获取枚举
     */
    public static ResultCode getByMessage(String message) {
        for (ResultCode resultCode : ResultCode.values()) {
            if (resultCode.getMessage().equals(message)) {
                return resultCode;
            }
        }
        return null;
    }
}