package com.streammonitor.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.streammonitor.model.entity.MonitoringTask;
import org.apache.ibatis.annotations.Mapper;

/**
 * 监控任务Mapper接口
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Mapper
public interface MonitoringTaskMapper extends BaseMapper<MonitoringTask> {
}