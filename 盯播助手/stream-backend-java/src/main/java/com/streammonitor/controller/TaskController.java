package com.streammonitor.controller;

import com.streammonitor.common.Result;
import com.streammonitor.dto.MonitoringRule;
import com.streammonitor.model.entity.MonitoringTask;
import com.streammonitor.service.MonitoringTaskService;
import com.streammonitor.service.MonitoringRulesEngine;
import com.streammonitor.service.RabbitMQService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;
import java.util.Map;

/**
 * 监控任务控制器
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@RestController
@RequestMapping("/tasks")
@RequiredArgsConstructor
@Validated
public class TaskController {

    private final MonitoringTaskService taskService;
    private final MonitoringRulesEngine rulesEngine;
    private final RabbitMQService rabbitMQService;

    /**
     * 获取任务列表
     */
    @GetMapping
    public Result<?> getTaskList(
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) Boolean todayTrigger,
            @RequestAttribute("userId") Long userId) {
        try {
            List<MonitoringTask> tasks = taskService.getTaskList(userId, keyword, status, todayTrigger);
            return Result.success("获取成功", Map.of("records", tasks));
        } catch (Exception e) {
            log.error("获取任务列表异常", e);
            return Result.error("获取任务列表失败");
        }
    }

    /**
     * 创建监控任务
     */
    @PostMapping
    public Result<?> createTask(@Valid @RequestBody MonitoringTask task, @RequestAttribute("userId") Long userId) {
        try {
            log.info("创建监控任务，用户ID: {}, 任务类型: {}", userId, task.getTaskType());

            // 设置用户ID
            task.setUserId(userId);
            task.setStatus(1); // 默认启用

            // 验证任务数据
            if (!validateTaskData(task)) {
                return Result.fail("任务数据验证失败");
            }

            // 保存任务
            boolean success = taskService.createTask(task);
            if (success) {
                // 发送任务到消息队列
                sendTaskToQueue(task);

                log.info("任务创建成功，任务ID: {}", task.getId());
                return Result.success("任务创建成功", task);
            } else {
                return Result.fail("任务创建失败");
            }
        } catch (Exception e) {
            log.error("创建任务异常", e);
            return Result.error("创建任务失败");
        }
    }

    /**
     * 更新任务
     */
    @PutMapping("/{id}")
    public Result<?> updateTask(@PathVariable Long id, @Valid @RequestBody MonitoringTask task,
                               @RequestAttribute("userId") Long userId) {
        try {
            log.info("更新监控任务，任务ID: {}, 用户ID: {}", id, userId);

            // 验证任务归属
            if (!taskService.isTaskOwnedByUser(id, userId)) {
                return Result.fail("无权操作此任务");
            }

            // 更新任务
            task.setId(id);
            boolean success = taskService.updateTask(task);
            if (success) {
                // 重新发送任务到队列
                sendTaskToQueue(task);

                log.info("任务更新成功，任务ID: {}", id);
                return Result.success("任务更新成功", task);
            } else {
                return Result.fail("任务更新失败");
            }
        } catch (Exception e) {
            log.error("更新任务异常", e);
            return Result.error("更新任务失败");
        }
    }

    /**
     * 删除任务
     */
    @DeleteMapping("/{id}")
    public Result<?> deleteTask(@PathVariable Long id, @RequestAttribute("userId") Long userId) {
        try {
            log.info("删除监控任务，任务ID: {}, 用户ID: {}", id, userId);

            // 验证任务归属
            if (!taskService.isTaskOwnedByUser(id, userId)) {
                return Result.fail("无权操作此任务");
            }

            // 停止任务并删除
            boolean success = taskService.deleteTask(id);
            if (success) {
                // 发送停止消息到队列
                sendTaskStopMessage(id);

                log.info("任务删除成功，任务ID: {}", id);
                return Result.success("任务删除成功");
            } else {
                return Result.fail("任务删除失败");
            }
        } catch (Exception e) {
            log.error("删除任务异常", e);
            return Result.error("删除任务失败");
        }
    }

    /**
     * 启动任务
     */
    @PostMapping("/{id}/start")
    public Result<?> startTask(@PathVariable Long id, @RequestAttribute("userId") Long userId) {
        try {
            log.info("启动监控任务，任务ID: {}, 用户ID: {}", id, userId);

            // 验证任务归属
            if (!taskService.isTaskOwnedByUser(id, userId)) {
                return Result.fail("无权操作此任务");
            }

            // 启动任务
            boolean success = taskService.startTask(id);
            if (success) {
                // 获取任务详情并发送到队列
                MonitoringTask task = taskService.getTaskById(id);
                if (task != null) {
                    sendTaskToQueue(task);
                }

                log.info("任务启动成功，任务ID: {}", id);
                return Result.success("任务启动成功");
            } else {
                return Result.fail("任务启动失败");
            }
        } catch (Exception e) {
            log.error("启动任务异常", e);
            return Result.error("启动任务失败");
        }
    }

    /**
     * 停止任务
     */
    @PostMapping("/{id}/stop")
    public Result<?> stopTask(@PathVariable Long id, @RequestAttribute("userId") Long userId) {
        try {
            log.info("停止监控任务，任务ID: {}, 用户ID: {}", id, userId);

            // 验证任务归属
            if (!taskService.isTaskOwnedByUser(id, userId)) {
                return Result.fail("无权操作此任务");
            }

            // 停止任务
            boolean success = taskService.stopTask(id);
            if (success) {
                // 发送停止消息到队列
                sendTaskStopMessage(id);

                log.info("任务停止成功，任务ID: {}", id);
                return Result.success("任务停止成功");
            } else {
                return Result.fail("任务停止失败");
            }
        } catch (Exception e) {
            log.error("停止任务异常", e);
            return Result.error("停止任务失败");
        }
    }

    /**
     * 验证任务数据
     */
    private boolean validateTaskData(MonitoringTask task) {
        // 验证必要字段
        if (task.getPlatform() == null || task.getPlatform().isEmpty()) {
            return false;
        }
        if (task.getRoomId() == null || task.getRoomId().isEmpty()) {
            return false;
        }
        if (task.getTaskType() == null || task.getTaskType().isEmpty()) {
            return false;
        }

        // 验证关键词任务
        if ("keyword_match".equals(task.getTaskType())) {
            if (task.getKeywords() == null || task.getKeywords().isEmpty()) {
                return false;
            }
        }

        return true;
    }

    /**
     * 发送任务到消息队列
     */
    private void sendTaskToQueue(MonitoringTask task) {
        try {
            // 构建任务消息
            Map<String, Object> taskMessage = Map.of(
                "taskId", task.getId(),
                "platform", task.getPlatform(),
                "roomId", task.getRoomId(),
                "taskType", task.getTaskType(),
                "keywords", task.getKeywords(),
                "aiAnalysis", task.getAiAnalysis(),
                "userId", task.getUserId(),
                "action", "start"
            );

            // 发送到爬虫任务队列
            rabbitMQService.sendToCrawlerQueue(taskMessage);
            log.info("任务消息已发送到队列，任务ID: {}", task.getId());
        } catch (Exception e) {
            log.error("发送任务消息到队列失败", e);
        }
    }

    /**
     * 发送任务停止消息
     */
    private void sendTaskStopMessage(Long taskId) {
        try {
            Map<String, Object> stopMessage = Map.of(
                "taskId", taskId,
                "action", "stop"
            );

            rabbitMQService.sendToCrawlerQueue(stopMessage);
            log.info("任务停止消息已发送到队列，任务ID: {}", taskId);
        } catch (Exception e) {
            log.error("发送任务停止消息失败", e);
        }
    }
}