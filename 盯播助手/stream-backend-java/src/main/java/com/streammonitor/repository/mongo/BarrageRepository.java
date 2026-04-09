package com.streammonitor.repository.mongo;

import com.streammonitor.model.document.BarrageDocument;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.ReactiveMongoRepository;
import org.springframework.data.mongodb.repository.Query;
import org.springframework.stereotype.Repository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;

/**
 * 弹幕数据MongoDB仓库
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Repository
public interface BarrageRepository extends ReactiveMongoRepository<BarrageDocument, String> {

    /**
     * 根据平台和房间ID查询弹幕
     */
    Flux<BarrageDocument> findByPlatformAndRoomIdOrderByTimestampDesc(String platform, String roomId);

    /**
     * 根据平台和房间ID查询指定时间范围内的弹幕
     */
    Flux<BarrageDocument> findByPlatformAndRoomIdAndTimestampBetweenOrderByTimestampDesc(
            String platform, String roomId, LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 根据用户ID查询弹幕
     */
    Flux<BarrageDocument> findByUserIdOrderByTimestampDesc(String userId, Pageable pageable);

    /**
     * 根据弹幕类型查询
     */
    Flux<BarrageDocument> findByTypeOrderByTimestampDesc(String type);

    /**
     * 根据主播配置ID查询弹幕
     */
    Flux<BarrageDocument> findByStreamerConfigIdOrderByTimestampDesc(Long streamerConfigId);

    /**
     * 统计指定时间范围内的弹幕数量
     */
    Mono<Long> countByPlatformAndRoomIdAndTimestampBetween(
            String platform, String roomId, LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 统计指定主播的弹幕数量
     */
    Mono<Long> countByStreamerConfigId(Long streamerConfigId);

    /**
     * 根据关键词搜索弹幕内容（使用全文索引）
     */
    @Query("{$text: {$search: ?0}}")
    Flux<BarrageDocument> findByContentContainingOrderByTimestampDesc(String keyword);

    /**
     * 根据关键词和平台搜索弹幕
     */
    @Query("{$text: {$search: ?0}, platform: ?1}")
    Flux<BarrageDocument> findByContentContainingAndPlatformOrderByTimestampDesc(String keyword, String platform);

    /**
     * 删除指定时间之前的弹幕数据（用于手动清理）
     */
    Mono<Long> deleteByTimestampBefore(LocalDateTime timestamp);

    /**
     * 删除指定主播的所有弹幕数据
     */
    Mono<Long> deleteByStreamerConfigId(Long streamerConfigId);

    /**
     * 获取指定时间范围内各平台的弹幕统计
     */
    @Query(value = "{timestamp: {$gte: ?0, $lte: ?1}}",
           fields = "{platform: 1, _id: 0}")
    Flux<BarrageDocument> findPlatformStatsByTimestampBetween(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 获取热门弹幕用户（按弹幕数量排序）
     */
    @Query(value = "{}",
           fields = "{userId: 1, username: 1, _id: 0}")
    Flux<BarrageDocument> findActiveUsers(Pageable pageable);
}