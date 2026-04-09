package com.streammonitor.service;

import com.streammonitor.model.document.BarrageDocument;
import com.streammonitor.model.entity.BarrageData;
import com.streammonitor.repository.BarrageDataRepository;
import com.streammonitor.repository.mongo.BarrageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.CompletableFuture;

/**
 * 数据迁移服务 - 将现有MySQL数据迁移到MongoDB
 * 一次性迁移任务，用于架构升级
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DataMigrationService {

    private final BarrageDataRepository barrageDataRepository;
    private final BarrageRepository barrageMongoRepository;

    /**
     * 异步迁移弹幕数据从MySQL到MongoDB
     */
    @Async
    @Transactional
    public CompletableFuture<Long> migrateBarrageDataToMongoDB() {
        try {
            log.info("开始迁移弹幕数据从MySQL到MongoDB");

            long totalMigrated = 0;
            int pageSize = 1000;
            int page = 0;
            boolean hasMore = true;

            while (hasMore) {
                Pageable pageable = PageRequest.of(page, pageSize);
                List<BarrageData> barrageList = barrageDataRepository.findAll(pageable).getContent();

                if (barrageList.isEmpty()) {
                    hasMore = false;
                } else {
                    // 转换并保存到MongoDB
                    List<BarrageDocument> documents = barrageList.stream()
                            .map(this::convertToDocument)
                            .toList();

                    barrageMongoRepository.saveAll(documents).subscribe();
                    totalMigrated += documents.size();

                    log.info("已迁移 {} 条弹幕数据 (第 {} 页)", documents.size(), page + 1);

                    // 避免过快请求，适当休眠
                    Thread.sleep(100);
                    page++;
                }
            }

            log.info("弹幕数据迁移完成，总共迁移 {} 条记录", totalMigrated);
            return CompletableFuture.completedFuture(totalMigrated);

        } catch (Exception e) {
            log.error("弹幕数据迁移失败", e);
            return CompletableFuture.failedFuture(e);
        }
    }

    /**
     * 迁移指定时间范围内的弹幕数据
     */
    @Async
    @Transactional
    public CompletableFuture<Long> migrateBarrageDataByDateRange(
            LocalDateTime startDate, LocalDateTime endDate) {
        try {
            log.info("开始迁移指定时间范围的弹幕数据: {} 到 {}", startDate, endDate);

            long totalMigrated = 0;
            int pageSize = 1000;
            int page = 0;
            boolean hasMore = true;

            while (hasMore) {
                Pageable pageable = PageRequest.of(page, pageSize);
                List<BarrageData> barrageList = barrageDataRepository
                        .findByTimestampBetweenOrderByTimestampAsc(startDate, endDate, pageable)
                        .getContent();

                if (barrageList.isEmpty()) {
                    hasMore = false;
                } else {
                    List<BarrageDocument> documents = barrageList.stream()
                            .map(this::convertToDocument)
                            .toList();

                    barrageMongoRepository.saveAll(documents).subscribe();
                    totalMigrated += documents.size();

                    log.info("已迁移 {} 条弹幕数据 (第 {} 页)", documents.size(), page + 1);

                    Thread.sleep(100);
                    page++;
                }
            }

            log.info("指定时间范围弹幕数据迁移完成，总共迁移 {} 条记录", totalMigrated);
            return CompletableFuture.completedFuture(totalMigrated);

        } catch (Exception e) {
            log.error("指定时间范围弹幕数据迁移失败", e);
            return CompletableFuture.failedFuture(e);
        }
    }

    /**
     * 验证数据迁移的完整性
     */
    public boolean verifyMigrationIntegrity(LocalDateTime startDate, LocalDateTime endDate) {
        try {
            // 比较MySQL和MongoDB中的数据量
            long mysqlCount = barrageDataRepository.countByTimestampBetween(startDate, endDate);
            long mongoCount = barrageMongoRepository
                    .countByTimestampBetween(startDate, endDate)
                    .block();

            log.info("数据完整性验证 - MySQL: {} 条, MongoDB: {} 条", mysqlCount, mongoCount);

            // 允许有小的差异（由于并发写入）
            double difference = Math.abs(mysqlCount - mongoCount);
            double tolerance = mysqlCount * 0.01; // 1%容错率

            return difference <= tolerance;

        } catch (Exception e) {
            log.error("数据完整性验证失败", e);
            return false;
        }
    }

    /**
     * 将MySQL实体转换为MongoDB文档
     */
    private BarrageDocument convertToDocument(BarrageData entity) {
        BarrageDocument document = new BarrageDocument(
                entity.getPlatform(),
                entity.getRoomId(),
                entity.getUserId(),
                entity.getUsername(),
                entity.getContent(),
                "danmu", // 默认类型
                entity.getTimestamp()
        );

        document.setId(String.valueOf(entity.getId()));
        document.setStreamerConfigId(entity.getStreamerConfigId());
        document.setUserLevel(1); // 默认等级
        document.setIsAdmin(false);
        document.setIsVip(false);

        return document;
    }

    /**
     * 清理已迁移的MySQL数据（谨慎使用）
     */
    @Transactional
    public long cleanupMigratedData(LocalDateTime beforeDate) {
        try {
            log.warn("开始清理 {} 之前的已迁移弹幕数据", beforeDate);
            long deletedCount = barrageDataRepository.deleteByTimestampBefore(beforeDate);
            log.info("已清理 {} 条MySQL弹幕数据", deletedCount);
            return deletedCount;
        } catch (Exception e) {
            log.error("清理已迁移数据失败", e);
            throw e;
        }
    }
}