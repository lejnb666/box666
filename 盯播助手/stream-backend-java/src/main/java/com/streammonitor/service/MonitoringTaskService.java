package com.streammonitor.service;

import com.streammonitor.model.entity.MonitoringTask;

import java.util.List;

/**
 * 监控任务服务接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
public interface MonitoringTaskService {

    /**
     * 获取任务列表
     *
     * @param userId 用户ID
     * @param keyword 搜索关键词
     * @param status 任务状态
     * @param todayTrigger 今日是否触发
     * @return 任务列表
     */
    List<MonitoringTask> getTaskList(Long userId, String keyword, Integer status, Boolean todayTrigger);

    /**
     * 根据ID获取任务
     *
     * @param taskId 任务ID
     * @return 任务信息
     */
    MonitoringTask getTaskById(Long taskId);

    /**
     * 创建任务
     *
     * @param task 任务信息
     * @return 是否成功
     */
    boolean createTask(MonitoringTask task);

    /**
     * 更新任务
     *
     * @param task 任务信息
     * @return 是否成功
     */
    boolean updateTask(MonitoringTask task);

    /**
     * 删除任务
     *
     * @param taskId 任务ID
     * @return 是否成功
     */
    boolean deleteTask(Long taskId);

    /**
     * 启动任务
     *
     * @param taskId 任务ID
     * @return 是否成功
     */
    boolean startTask(Long taskId);

    /**
     * 停止任务
     *
     * @param taskId 任务ID
     * @return 是否成功
     */
    boolean stopTask(Long taskId);

    /**
     * 验证任务是否属于指定用户
     *
     * @param taskId 任务ID
     * @param userId 用户ID
     * @return 是否属于
     */
    boolean isTaskOwnedByUser(Long taskId, Long userId);

    /**
     * 增加任务触发次数
     *
     * @param taskId 任务ID
     * @return 是否成功
     */
    boolean incrementTriggerCount(Long taskId);

    /**
     * 获取用户的活跃任务数量
     *
     * @param userId 用户ID
     * @return 活跃任务数量
     */
    int getActiveTaskCount(Long userId);

    /**
     * 获取平台任务统计
     *
     * @param platform 平台
     * @return 任务数量
     */
    int getTaskCountByPlatform(String platform);

    /**
     * 批量停止任务
     *
     * @param taskIds 任务ID列表
     * @return 成功数量
     */
    int batchStopTasks(List<Long> taskIds);

    /**
     * 清理过期任务
     *
     * @return 清理数量
     */
    int cleanupExpiredTasks();
}