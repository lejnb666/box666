package com.streammonitor.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.streammonitor.mapper.MonitoringTaskMapper;
import com.streammonitor.model.entity.MonitoringTask;
import com.streammonitor.service.MonitoringTaskService;
import com.streammonitor.common.BusinessException;
import com.streammonitor.common.ResultCode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 监控任务服务实现类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MonitoringTaskServiceImpl implements MonitoringTaskService {

    private final MonitoringTaskMapper taskMapper;

    // 状态常量定义，避免魔法值
    private static final int STATUS_ACTIVE = 1;
    private static final int STATUS_STOPPED = 0;
    private static final int STATUS_ARCHIVED = -1; // 新增：归档/逻辑删除状态

    @Override
    public List<MonitoringTask> getTaskList(Long userId, String keyword, Integer status, Boolean todayTrigger) {
        try {
            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(MonitoringTask::getUserId, userId)
                        .ne(MonitoringTask::getStatus, STATUS_ARCHIVED); // 过滤已归档任务

            if (keyword != null && !keyword.trim().isEmpty()) {
                queryWrapper.and(wrapper -> wrapper
                    .like(MonitoringTask::getStreamerName, keyword)
                    .or()
                    .like(MonitoringTask::getPlatform, keyword)
                    .or()
                    .like(MonitoringTask::getRoomId, keyword)
                );
            }

            if (status != null) {
                queryWrapper.eq(MonitoringTask::getStatus, status);
            }

            if (todayTrigger != null && todayTrigger) {
                LocalDateTime startOfDay = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
                LocalDateTime endOfDay = LocalDateTime.of(LocalDate.now(), LocalTime.MAX);
                queryWrapper.ge(MonitoringTask::getLastTriggeredAt, startOfDay)
                           .le(MonitoringTask::getLastTriggeredAt, endOfDay);
            }

            queryWrapper.orderByDesc(MonitoringTask::getCreatedAt);
            return taskMapper.selectList(queryWrapper);
        } catch (Exception e) {
            log.error("获取任务列表失败，用户ID: {}", userId, e);
            throw new BusinessException(ResultCode.SYSTEM_ERROR, "获取任务列表失败", e);
        }
    }

    @Override
    public MonitoringTask getTaskById(Long taskId) {
        return taskMapper.selectById(taskId);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean createTask(MonitoringTask task) {
        log.info("创建监控任务: {}", task);
        task.setCreatedAt(LocalDateTime.now());
        task.setUpdatedAt(LocalDateTime.now());
        task.setStatus(STATUS_STOPPED); // 默认创建为停止状态
        if (task.getTriggerCount() == null) {
            task.setTriggerCount(0);
        }
        return taskMapper.insert(task) > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean updateTask(MonitoringTask task) {
        log.info("更新监控任务: {}", task.getId());
        task.setUpdatedAt(LocalDateTime.now());
        return taskMapper.updateById(task) > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deleteTask(Long taskId) {
        log.info("请求删除监控任务，任务ID: {}", taskId);
        MonitoringTask existingTask = taskMapper.selectById(taskId);
        if (existingTask == null) {
            return true;
        }
        // 🚨 修复1：防止删除运行中的任务，避免出现爬虫端无法停止的"幽灵任务"
        if (existingTask.getStatus() == STATUS_ACTIVE) {
            throw new BusinessException(ResultCode.VALIDATION_ERROR, "任务正在运行中，请先停止后再删除");
        }
        
        // 执行逻辑删除或物理删除
        int result = taskMapper.deleteById(taskId);
        return result > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean startTask(Long taskId) {
        log.info("启动监控任务，任务ID: {}", taskId);
        LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(MonitoringTask::getId, taskId)
                    .set(MonitoringTask::getStatus, STATUS_ACTIVE)
                    .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

        // 注意：实际项目中这里应结合 MQ 发送启动指令，并使用 Publisher Confirms 确保一致性
        return taskMapper.update(null, updateWrapper) > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean stopTask(Long taskId) {
        log.info("停止监控任务，任务ID: {}", taskId);
        LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(MonitoringTask::getId, taskId)
                    .set(MonitoringTask::getStatus, STATUS_STOPPED)
                    .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

        return taskMapper.update(null, updateWrapper) > 0;
    }

    @Override
    public boolean isTaskOwnedByUser(Long taskId, Long userId) {
        LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(MonitoringTask::getId, taskId)
                   .eq(MonitoringTask::getUserId, userId);
        return taskMapper.selectCount(queryWrapper) > 0;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean incrementTriggerCount(Long taskId) {
        LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(MonitoringTask::getId, taskId)
                    .setSql("trigger_count = trigger_count + 1")
                    .set(MonitoringTask::getLastTriggeredAt, LocalDateTime.now())
                    .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());
        return taskMapper.update(null, updateWrapper) > 0;
    }

    @Override
    public int getActiveTaskCount(Long userId) {
        LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(MonitoringTask::getUserId, userId)
                   .eq(MonitoringTask::getStatus, STATUS_ACTIVE);
        return taskMapper.selectCount(queryWrapper).intValue();
    }

    @Override
    public int getTaskCountByPlatform(String platform) {
        LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(MonitoringTask::getPlatform, platform)
                   .ne(MonitoringTask::getStatus, STATUS_ARCHIVED);
        return taskMapper.selectCount(queryWrapper).intValue();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchStopTasks(List<Long> taskIds) {
        if (taskIds == null || taskIds.isEmpty()) {
            return 0;
        }
        log.info("批量停止任务，总数量: {}", taskIds.size());
        int totalUpdated = 0;
        int batchSize = 500; // 🚨 修复2：分批处理，防止 SQL 的 IN 条件超长导致数据库报错

        for (int i = 0; i < taskIds.size(); i += batchSize) {
            List<Long> batchList = taskIds.subList(i, Math.min(i + batchSize, taskIds.size()));
            
            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.in(MonitoringTask::getId, batchList)
                        .set(MonitoringTask::getStatus, STATUS_STOPPED)
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());
            
            totalUpdated += taskMapper.update(null, updateWrapper);
        }
        return totalUpdated;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int cleanupExpiredTasks() {
        log.info("开始清理过期任务");
        // 清理30天未更新的停止任务
        LocalDateTime expireTime = LocalDateTime.now().minusDays(30);

        LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(MonitoringTask::getStatus, STATUS_STOPPED)
                   .lt(MonitoringTask::getUpdatedAt, expireTime);

        List<MonitoringTask> expiredTasks = taskMapper.selectList(queryWrapper);

        if (!expiredTasks.isEmpty()) {
            List<Long> taskIds = expiredTasks.stream()
                .map(MonitoringTask::getId)
                .collect(Collectors.toList());

            // 🚨 修复3：将物理删除(deleteBatchIds)改为归档状态，防止破坏大数据与MongoDB的历史外键关联
            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.in(MonitoringTask::getId, taskIds)
                        .set(MonitoringTask::getStatus, STATUS_ARCHIVED)
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

            int result = taskMapper.update(null, updateWrapper);
            log.info("清理过期任务完成，归档数量: {}", result);
            return result;
        }
        return 0;
    }
}
