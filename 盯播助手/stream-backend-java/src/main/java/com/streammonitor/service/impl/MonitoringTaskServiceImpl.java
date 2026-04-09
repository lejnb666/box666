package com.streammonitor.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.streammonitor.mapper.MonitoringTaskMapper;
import com.streammonitor.model.entity.MonitoringTask;
import com.streammonitor.service.MonitoringTaskService;
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

    @Override
    public List<MonitoringTask> getTaskList(Long userId, String keyword, Integer status, Boolean todayTrigger) {
        try {
            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();

            // 用户过滤
            queryWrapper.eq(MonitoringTask::getUserId, userId);

            // 关键词搜索
            if (keyword != null && !keyword.trim().isEmpty()) {
                queryWrapper.and(wrapper -> wrapper
                    .like(MonitoringTask::getStreamerName, keyword)
                    .or()
                    .like(MonitoringTask::getPlatform, keyword)
                    .or()
                    .like(MonitoringTask::getRoomId, keyword)
                );
            }

            // 状态过滤
            if (status != null) {
                queryWrapper.eq(MonitoringTask::getStatus, status);
            }

            // 今日触发过滤
            if (todayTrigger != null && todayTrigger) {
                LocalDateTime startOfDay = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
                LocalDateTime endOfDay = LocalDateTime.of(LocalDate.now(), LocalTime.MAX);
                queryWrapper.ge(MonitoringTask::getLastTriggeredAt, startOfDay)
                           .le(MonitoringTask::getLastTriggeredAt, endOfDay);
            }

            // 按创建时间倒序
            queryWrapper.orderByDesc(MonitoringTask::getCreatedAt);

            return taskMapper.selectList(queryWrapper);
        } catch (Exception e) {
            log.error("获取任务列表失败，用户ID: {}", userId, e);
            throw e;
        }
    }

    @Override
    public MonitoringTask getTaskById(Long taskId) {
        try {
            return taskMapper.selectById(taskId);
        } catch (Exception e) {
            log.error("获取任务失败，任务ID: {}", taskId, e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean createTask(MonitoringTask task) {
        try {
            log.info("创建监控任务: {}", task);

            // 设置创建时间
            task.setCreatedAt(LocalDateTime.now());
            task.setUpdatedAt(LocalDateTime.now());

            // 初始化触发次数
            if (task.getTriggerCount() == null) {
                task.setTriggerCount(0);
            }

            int result = taskMapper.insert(task);

            if (result > 0) {
                log.info("任务创建成功，任务ID: {}", task.getId());
                return true;
            } else {
                log.warn("任务创建失败，插入结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("创建任务异常", e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean updateTask(MonitoringTask task) {
        try {
            log.info("更新监控任务: {}", task.getId());

            // 设置更新时间
            task.setUpdatedAt(LocalDateTime.now());

            int result = taskMapper.updateById(task);

            if (result > 0) {
                log.info("任务更新成功，任务ID: {}", task.getId());
                return true;
            } else {
                log.warn("任务更新失败，更新结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("更新任务异常，任务ID: {}", task.getId(), e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean deleteTask(Long taskId) {
        try {
            log.info("删除监控任务，任务ID: {}", taskId);

            int result = taskMapper.deleteById(taskId);

            if (result > 0) {
                log.info("任务删除成功，任务ID: {}", taskId);
                return true;
            } else {
                log.warn("任务删除失败，删除结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("删除任务异常，任务ID: {}", taskId, e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean startTask(Long taskId) {
        try {
            log.info("启动监控任务，任务ID: {}", taskId);

            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.eq(MonitoringTask::getId, taskId)
                        .set(MonitoringTask::getStatus, 1)
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

            int result = taskMapper.update(updateWrapper);

            if (result > 0) {
                log.info("任务启动成功，任务ID: {}", taskId);
                return true;
            } else {
                log.warn("任务启动失败，更新结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("启动任务异常，任务ID: {}", taskId, e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean stopTask(Long taskId) {
        try {
            log.info("停止监控任务，任务ID: {}", taskId);

            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.eq(MonitoringTask::getId, taskId)
                        .set(MonitoringTask::getStatus, 0)
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

            int result = taskMapper.update(updateWrapper);

            if (result > 0) {
                log.info("任务停止成功，任务ID: {}", taskId);
                return true;
            } else {
                log.warn("任务停止失败，更新结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("停止任务异常，任务ID: {}", taskId, e);
            throw e;
        }
    }

    @Override
    public boolean isTaskOwnedByUser(Long taskId, Long userId) {
        try {
            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(MonitoringTask::getId, taskId)
                       .eq(MonitoringTask::getUserId, userId);

            return taskMapper.selectCount(queryWrapper) > 0;
        } catch (Exception e) {
            log.error("验证任务归属异常，任务ID: {}, 用户ID: {}", taskId, userId, e);
            return false;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean incrementTriggerCount(Long taskId) {
        try {
            log.info("增加任务触发次数，任务ID: {}", taskId);

            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.eq(MonitoringTask::getId, taskId)
                        .setSql("trigger_count = trigger_count + 1")
                        .set(MonitoringTask::getLastTriggeredAt, LocalDateTime.now())
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

            int result = taskMapper.update(updateWrapper);

            if (result > 0) {
                log.info("任务触发次数增加成功，任务ID: {}", taskId);
                return true;
            } else {
                log.warn("任务触发次数增加失败，更新结果: {}", result);
                return false;
            }
        } catch (Exception e) {
            log.error("增加任务触发次数异常，任务ID: {}", taskId, e);
            throw e;
        }
    }

    @Override
    public int getActiveTaskCount(Long userId) {
        try {
            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(MonitoringTask::getUserId, userId)
                       .eq(MonitoringTask::getStatus, 1);

            return taskMapper.selectCount(queryWrapper).intValue();
        } catch (Exception e) {
            log.error("获取活跃任务数量失败，用户ID: {}", userId, e);
            return 0;
        }
    }

    @Override
    public int getTaskCountByPlatform(String platform) {
        try {
            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(MonitoringTask::getPlatform, platform);

            return taskMapper.selectCount(queryWrapper).intValue();
        } catch (Exception e) {
            log.error("获取平台任务数量失败，平台: {}", platform, e);
            return 0;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchStopTasks(List<Long> taskIds) {
        try {
            if (taskIds == null || taskIds.isEmpty()) {
                return 0;
            }

            log.info("批量停止任务，任务数量: {}", taskIds.size());

            LambdaUpdateWrapper<MonitoringTask> updateWrapper = new LambdaUpdateWrapper<>();
            updateWrapper.in(MonitoringTask::getId, taskIds)
                        .set(MonitoringTask::getStatus, 0)
                        .set(MonitoringTask::getUpdatedAt, LocalDateTime.now());

            return taskMapper.update(updateWrapper);
        } catch (Exception e) {
            log.error("批量停止任务异常", e);
            throw e;
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int cleanupExpiredTasks() {
        try {
            log.info("开始清理过期任务");

            // 清理30天未更新的停止任务
            LocalDateTime expireTime = LocalDateTime.now().minusDays(30);

            LambdaQueryWrapper<MonitoringTask> queryWrapper = new LambdaQueryWrapper<>();
            queryWrapper.eq(MonitoringTask::getStatus, 0)
                       .lt(MonitoringTask::getUpdatedAt, expireTime);

            List<MonitoringTask> expiredTasks = taskMapper.selectList(queryWrapper);

            if (!expiredTasks.isEmpty()) {
                List<Long> taskIds = expiredTasks.stream()
                    .map(MonitoringTask::getId)
                    .collect(Collectors.toList());

                int result = taskMapper.deleteBatchIds(taskIds);
                log.info("清理过期任务完成，清理数量: {}", result);
                return result;
            }

            return 0;
        } catch (Exception e) {
            log.error("清理过期任务异常", e);
            throw e;
        }
    }
}