package com.streammonitor.service.impl;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.streammonitor.dto.MonitoringRule;
import com.streammonitor.service.MonitoringRulesEngine;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.regex.Pattern;

/**
 * 监控规则引擎实现类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
public class MonitoringRulesEngineImpl implements MonitoringRulesEngine {

    @Override
    public boolean evaluateRules(String content, List<MonitoringRule> rules) {
        if (rules == null || rules.isEmpty()) {
            return false;
        }

        for (MonitoringRule rule : rules) {
            if (evaluateRule(content, rule)) {
                return true;
            }
        }

        return false;
    }

    @Override
    public boolean evaluateRule(String content, MonitoringRule rule) {
        if (content == null || content.trim().isEmpty()) {
            return false;
        }

        try {
            String operator = rule.getOperator();
            String value = rule.getValue();
            boolean caseSensitive = rule.isCaseSensitive();

            // 根据操作符类型进行匹配
            switch (operator) {
                case "contains":
                    return evaluateContains(content, value, caseSensitive);
                case "not_contains":
                    return !evaluateContains(content, value, caseSensitive);
                case "equals":
                    return evaluateEquals(content, value, caseSensitive);
                case "starts_with":
                    return evaluateStartsWith(content, value, caseSensitive);
                case "ends_with":
                    return evaluateEndsWith(content, value, caseSensitive);
                case "regex":
                    return evaluateRegex(content, value);
                case "length_greater":
                    return evaluateLengthGreater(content, Integer.parseInt(value));
                case "length_less":
                    return evaluateLengthLess(content, Integer.parseInt(value));
                default:
                    log.warn("不支持的操作符: {}", operator);
                    return false;
            }
        } catch (Exception e) {
            log.error("规则评估异常", e);
            return false;
        }
    }

    @Override
    public boolean evaluateComplexRules(String content, JSONObject complexRules) {
        if (complexRules == null || content == null) {
            return false;
        }

        try {
            String logic = complexRules.getString("logic"); // AND, OR
            JSONArray conditions = complexRules.getJSONArray("conditions");

            if (conditions == null || conditions.isEmpty()) {
                return false;
            }

            if ("AND".equalsIgnoreCase(logic)) {
                return evaluateAndConditions(content, conditions);
            } else if ("OR".equalsIgnoreCase(logic)) {
                return evaluateOrConditions(content, conditions);
            } else {
                log.warn("不支持的逻辑操作符: {}", logic);
                return false;
            }

        } catch (Exception e) {
            log.error("复杂规则评估异常", e);
            return false;
        }
    }

    /**
     * 评估包含关系
     */
    private boolean evaluateContains(String content, String value, boolean caseSensitive) {
        if (!caseSensitive) {
            return content.toLowerCase().contains(value.toLowerCase());
        } else {
            return content.contains(value);
        }
    }

    /**
     * 评估相等关系
     */
    private boolean evaluateEquals(String content, String value, boolean caseSensitive) {
        if (!caseSensitive) {
            return content.toLowerCase().equals(value.toLowerCase());
        } else {
            return content.equals(value);
        }
    }

    /**
     * 评估开头匹配
     */
    private boolean evaluateStartsWith(String content, String value, boolean caseSensitive) {
        if (!caseSensitive) {
            return content.toLowerCase().startsWith(value.toLowerCase());
        } else {
            return content.startsWith(value);
        }
    }

    /**
     * 评估结尾匹配
     */
    private boolean evaluateEndsWith(String content, String value, boolean caseSensitive) {
        if (!caseSensitive) {
            return content.toLowerCase().endsWith(value.toLowerCase());
        } else {
            return content.endsWith(value);
        }
    }

    /**
     * 评估正则表达式
     */
    private boolean evaluateRegex(String content, String pattern) {
        try {
            return Pattern.compile(pattern).matcher(content).find();
        } catch (Exception e) {
            log.error("正则表达式匹配失败: {}", pattern, e);
            return false;
        }
    }

    /**
     * 评估长度大于
     */
    private boolean evaluateLengthGreater(String content, int length) {
        return content.length() > length;
    }

    /**
     * 评估长度小于
     */
    private boolean evaluateLengthLess(String content, int length) {
        return content.length() < length;
    }

    /**
     * 评估AND条件
     */
    private boolean evaluateAndConditions(String content, JSONArray conditions) {
        for (int i = 0; i < conditions.size(); i++) {
            JSONObject condition = conditions.getJSONObject(i);

            if (condition.containsKey("logic")) {
                // 嵌套条件
                if (!evaluateComplexRules(content, condition)) {
                    return false;
                }
            } else {
                // 简单条件
                MonitoringRule rule = parseConditionToRule(condition);
                if (!evaluateRule(content, rule)) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * 评估OR条件
     */
    private boolean evaluateOrConditions(String content, JSONArray conditions) {
        for (int i = 0; i < conditions.size(); i++) {
            JSONObject condition = conditions.getJSONObject(i);

            if (condition.containsKey("logic")) {
                // 嵌套条件
                if (evaluateComplexRules(content, condition)) {
                    return true;
                }
            } else {
                // 简单条件
                MonitoringRule rule = parseConditionToRule(condition);
                if (evaluateRule(content, rule)) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * 将条件JSON转换为MonitoringRule对象
     */
    private MonitoringRule parseConditionToRule(JSONObject condition) {
        MonitoringRule rule = new MonitoringRule();
        rule.setField(condition.getString("field"));
        rule.setOperator(condition.getString("operator"));
        rule.setValue(condition.getString("value"));
        rule.setCaseSensitive(condition.getBooleanValue("caseSensitive", false));
        return rule;
    }

    @Override
    public JSONObject buildComplexRule(String logic, List<JSONObject> conditions) {
        JSONObject complexRule = new JSONObject();
        complexRule.put("logic", logic.toUpperCase());
        complexRule.put("conditions", conditions);
        return complexRule;
    }

    @Override
    public boolean validateRule(MonitoringRule rule) {
        if (rule == null) {
            return false;
        }

        String operator = rule.getOperator();
        String value = rule.getValue();

        if (operator == null || operator.trim().isEmpty()) {
            return false;
        }

        if (value == null || value.trim().isEmpty()) {
            return false;
        }

        // 验证特定操作符的参数
        switch (operator) {
            case "regex":
                try {
                    Pattern.compile(value);
                } catch (Exception e) {
                    log.error("无效的正则表达式: {}", value);
                    return false;
                }
                break;
            case "length_greater":
            case "length_less":
                try {
                    Integer.parseInt(value);
                } catch (NumberFormatException e) {
                    log.error("无效的数字参数: {}", value);
                    return false;
                }
                break;
        }

        return true;
    }

    @Override
    public String exportRules(List<MonitoringRule> rules) {
        try {
            return JSON.toJSONString(rules);
        } catch (Exception e) {
            log.error("规则导出失败", e);
            return "[]";
        }
    }

    @Override
    public List<MonitoringRule> importRules(String rulesJson) {
        try {
            return JSON.parseArray(rulesJson, MonitoringRule.class);
        } catch (Exception e) {
            log.error("规则导入失败", e);
            return null;
        }
    }
}