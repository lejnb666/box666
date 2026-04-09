package com.streammonitor.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * 监控规则数据传输对象
 *
 * @author exbox0403-cmd
 * @since: 2026/4/8
 */
@Data
public class MonitoringRule implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 规则ID
     */
    private Long id;

    /**
     * 规则名称
     */
    private String name;

    /**
     * 匹配字段（content, username等）
     */
    private String field;

    /**
     * 操作符：contains, equals, starts_with, ends_with, regex等
     */
    private String operator;

    /**
     * 匹配值
     */
    private String value;

    /**
     * 是否区分大小写
     */
    private boolean caseSensitive = false;

    /**
     * 规则权重（用于优先级排序）
     */
    private int weight = 1;

    /**
     * 是否启用
     */
    private boolean enabled = true;

    /**
     * 规则描述
     */
    private String description;

    public MonitoringRule() {
    }

    public MonitoringRule(String field, String operator, String value) {
        this.field = field;
        this.operator = operator;
        this.value = value;
    }

    public MonitoringRule(String field, String operator, String value, boolean caseSensitive) {
        this.field = field;
        this.operator = operator;
        this.value = value;
        this.caseSensitive = caseSensitive;
    }

    /**
     * 创建包含规则
     */
    public static MonitoringRule contains(String value) {
        return new MonitoringRule("content", "contains", value);
    }

    /**
     * 创建不包含规则
     */
    public static MonitoringRule notContains(String value) {
        return new MonitoringRule("content", "not_contains", value);
    }

    /**
     * 创建正则表达式规则
     */
    public static MonitoringRule regex(String pattern) {
        return new MonitoringRule("content", "regex", pattern);
    }

    /**
     * 创建用户名匹配规则
     */
    public static MonitoringRule usernameContains(String value) {
        return new MonitoringRule("username", "contains", value);
    }

    /**
     * 创建长度限制规则
     */
    public static MonitoringRule lengthGreater(int length) {
        return new MonitoringRule("content", "length_greater", String.valueOf(length));
    }

    /**
     * 创建长度限制规则
     */
    public static MonitoringRule lengthLess(int length) {
        return new MonitoringRule("content", "length_less", String.valueOf(length));
    }

    @Override
    public String toString() {
        return String.format("Rule{field='%s', operator='%s', value='%s', caseSensitive=%s}",
                field, operator, value, caseSensitive);
    }
}