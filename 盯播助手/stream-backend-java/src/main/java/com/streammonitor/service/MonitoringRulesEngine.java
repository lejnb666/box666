package com.streammonitor.service;

import com.alibaba.fastjson2.JSONObject;
import com.streammonitor.dto.MonitoringRule;

import java.util.List;

/**
 * 监控规则引擎接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface MonitoringRulesEngine {

    /**
     * 评估多个规则
     *
     * @param content 待评估内容
     * @param rules 规则列表
     * @return 是否匹配任意规则
     */
    boolean evaluateRules(String content, List<MonitoringRule> rules);

    /**
     * 评估单个规则
     *
     * @param content 待评估内容
     * @param rule 规则
     * @return 是否匹配规则
     */
    boolean evaluateRule(String content, MonitoringRule rule);

    /**
     * 评估复杂规则（支持AND/OR逻辑）
     *
     * @param content 待评估内容
     * @param complexRules 复杂规则JSON
     * @return 是否匹配规则
     */
    boolean evaluateComplexRules(String content, JSONObject complexRules);

    /**
     * 构建复杂规则
     *
     * @param logic 逻辑操作符 (AND/OR)
     * @param conditions 条件列表
     * @return 复杂规则JSON
     */
    JSONObject buildComplexRule(String logic, List<JSONObject> conditions);

    /**
     * 验证规则有效性
     *
     * @param rule 规则
     * @return 是否有效
     */
    boolean validateRule(MonitoringRule rule);

    /**
     * 导出规则为JSON字符串
     *
     * @param rules 规则列表
     * @return JSON字符串
     */
    String exportRules(List<MonitoringRule> rules);

    /**
     * 从JSON字符串导入规则
     *
     * @param rulesJson 规则JSON字符串
     * @return 规则列表
     */
    List<MonitoringRule> importRules(String rulesJson);
}