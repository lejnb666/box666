package com.streammonitor.repository;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.streammonitor.model.entity.MonitorTask;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 监控任务数据访问层
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Mapper
public interface MonitorTaskRepository extends BaseMapper<MonitorTask> {

    /**
     * 根据用户ID查询监控任务列表
     *
     * @param page 分页参数
     * @param userId 用户ID
     * @return 分页结果
     */
    IPage<MonitorTask> findByUserId(Page<MonitorTask> page, @Param("userId") Long userId);

    /**
     * 根据用户ID和状态查询监控任务
     *
     * @param userId 用户ID
     * @param status 状态
     * @return 监控任务列表
     */
    @Select("SELECT mt.*, sc.streamer_name, sc.platform " +
            "FROM monitor_task mt " +
            "LEFT JOIN streamer_config sc ON mt.streamer_config_id = sc.id " +
            "WHERE mt.user_id = #{userId} AND mt.status = #{status}")
    List<MonitorTask> findByUserIdAndStatus(@Param("userId") Long userId, @Param("status") Integer status);

    /**
     * 根据主播配置ID查询监控任务
     *
     * @param streamerConfigId 主播配置ID
     * @return 监控任务列表
     */
    @Select("SELECT * FROM monitor_task WHERE streamer_config_id = #{streamerConfigId} AND status = 1")
    List<MonitorTask> findByStreamerConfigId(@Param("streamerConfigId") Long streamerConfigId);

    /**
     * 统计用户的监控任务数
     *
     * @param userId 用户ID
     * @return 任务数
     */
    @Select("SELECT COUNT(*) FROM monitor_task WHERE user_id = #{userId}")
    Long countByUserId(@Param("userId") Long userId);

    /**
     * 更新任务状态
     *
     * @param id 任务ID
     * @param status 新状态
     * @return 更新结果
     */
    int updateStatus(@Param("id") Long id, @Param("status") Integer status);

    /**
     * 增加触发次数
     *
     * @param id 任务ID
     * @return 更新结果
     */
    @Select("UPDATE monitor_task SET trigger_count = trigger_count + 1, last_triggered_at = NOW() WHERE id = #{id}")
    int incrementTriggerCount(@Param("id") Long id);
}