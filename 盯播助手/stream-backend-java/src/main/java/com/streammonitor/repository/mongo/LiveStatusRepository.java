package com.streammonitor.repository.mongo;

import com.streammonitor.model.document.LiveStatusDocument;
import org.springframework.data.mongodb.repository.ReactiveMongoRepository;
import org.springframework.stereotype.Repository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;

/**
 * 直播状态MongoDB仓库
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Repository
public interface LiveStatusRepository extends ReactiveMongoRepository<LiveStatusDocument, String> {

    /**
     * 根据平台和房间ID查询直播状态
     */
    Flux<LiveStatusDocument> findByPlatformAndRoomIdOrderByTimestampDesc(String platform, String roomId);

    /**
     * 查询指定主播的最新直播状态
     */
    Mono<LiveStatusDocument> findFirstByStreamerConfigIdOrderByTimestampDesc(Long streamerConfigId);

    /**
     * 查询指定时间范围内的直播状态记录
     */
    Flux<LiveStatusDocument> findByTimestampBetweenOrderByTimestampDesc(
            LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 查询指定平台的直播状态记录
     */
    Flux<LiveStatusDocument> findByPlatformOrderByTimestampDesc(String platform);

    /**
     * 查询正在直播的房间
     */
    Flux<LiveStatusDocument> findByStatusOrderByTimestampDesc(Integer status);

    /**
     * 查询指定主播的直播历史
     */
    Flux<LiveStatusDocument> findByStreamerConfigIdOrderByTimestampDesc(Long streamerConfigId);

    /**
     * 统计指定时间范围内的直播时长
     */
    Flux<LiveStatusDocument> findByStreamerConfigIdAndStatusAndTimestampBetween(
            Long streamerConfigId, Integer status, LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 删除指定时间之前的直播状态数据
     */
    Mono<Long> deleteByTimestampBefore(LocalDateTime timestamp);

    /**
     * 删除指定主播的所有直播状态数据
     */
    Mono<Long> deleteByStreamerConfigId(Long streamerConfigId);

    /**
     * 获取最新的直播状态快照
     */
    Flux<LiveStatusDocument> findByTimestampGreaterThanOrderByTimestampDesc(LocalDateTime timestamp);
}