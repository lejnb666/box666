package com.streammonitor.repository.mongo;

import com.streammonitor.model.document.ProductMonitorDocument;
import org.springframework.data.mongodb.repository.ReactiveMongoRepository;
import org.springframework.stereotype.Repository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.LocalDateTime;

/**
 * 商品监控MongoDB仓库
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Repository
public interface ProductMonitorRepository extends ReactiveMongoRepository<ProductMonitorDocument, String> {

    /**
     * 根据平台和房间ID查询商品监控记录
     */
    Flux<ProductMonitorDocument> findByPlatformAndRoomIdOrderByDetectedAtDesc(String platform, String roomId);

    /**
     * 查询指定主播的商品监控记录
     */
    Flux<ProductMonitorDocument> findByStreamerConfigIdOrderByDetectedAtDesc(Long streamerConfigId);

    /**
     * 查询指定时间范围内的商品监控记录
     */
    Flux<ProductMonitorDocument> findByDetectedAtBetweenOrderByDetectedAtDesc(
            LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 根据检测方式查询商品记录
     */
    Flux<ProductMonitorDocument> findByDetectedByOrderByDetectedAtDesc(String detectedBy);

    /**
     * 查询AI检测的商品记录（按置信度排序）
     */
    Flux<ProductMonitorDocument> findByDetectedByAndAiConfidenceIsNotNullOrderByAiConfidenceDesc(
            String detectedBy);

    /**
     * 查询高置信度的商品记录
     */
    Flux<ProductMonitorDocument> findByAiConfidenceGreaterThanEqualOrderByDetectedAtDesc(Double confidence);

    /**
     * 统计指定时间范围内的商品检测数量
     */
    Mono<Long> countByDetectedAtBetween(LocalDateTime startTime, LocalDateTime endTime);

    /**
     * 统计指定主播的商品检测数量
     */
    Mono<Long> countByStreamerConfigId(Long streamerConfigId);

    /**
     * 删除指定时间之前的商品监控数据
     */
    Mono<Long> deleteByDetectedAtBefore(LocalDateTime timestamp);

    /**
     * 删除指定主播的所有商品监控数据
     */
    Mono<Long> deleteByStreamerConfigId(Long streamerConfigId);

    /**
     * 获取热门商品（按检测频次）
     */
    Flux<ProductMonitorDocument> findTop10ByOrderByDetectedAtDesc();

    /**
     * 根据商品名称模糊查询
     */
    Flux<ProductMonitorDocument> findByProductNameContainingOrderByDetectedAtDesc(String productName);
}