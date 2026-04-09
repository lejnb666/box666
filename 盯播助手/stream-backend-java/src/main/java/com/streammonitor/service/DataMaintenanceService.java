package com.streammonitor.service;

import com.streammonitor.repository.PushLogRepository;
import com.streammonitor.repository.mongo.BarrageRepository;
import com.streammonitor.repository.mongo.LiveStatusRepository;
import com.streammonitor.repository.mongo.ProductMonitorRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 数据维护服务 - 定时清理和维护任务
 * 使用@Scheduled实现定时任务，也可替换为XXL-JOB等企业级调度框架
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DataMaintenanceService {

    private final PushLogRepository pushLogRepository;
    private final BarrageRepository barrageRepository;
    private final LiveStatusRepository liveStatusRepository;
    private final ProductMonitorRepository productMonitorRepository;

    /**
     * 每日凌晨清理过期的推送历史记录
     * 清理30天前的已读推送记录
     */
    @Scheduled(cron = "0 0 2 * * ?") // 每天凌晨2点执行
    @Transactional
    public void cleanupExpiredPushLogs() {
        try {
            LocalDateTime cutoffDate = LocalDateTime.now().minusDays(30);
            int deletedCount = pushLogRepository.deleteByStatusAndSentAtBefore(1, cutoffDate);
            log.info("清理过期推送历史记录完成，删除 {} 条记录，截止日期: {}", deletedCount, cutoffDate);
        } catch (Exception e) {
            log.error("清理推送历史记录失败", e);
        }
    }

    /**
     * 每日清理未读但过期的推送记录
     * 清理7天前的未读推送记录（用户长时间未查看）
     */
    @Scheduled(cron = "0 30 2 * * ?") // 每天凌晨2:30执行
    @Transactional
    public void cleanupExpiredUnreadPushLogs() {
        try {
            LocalDateTime cutoffDate = LocalDateTime.now().minusDays(7);
            int deletedCount = pushLogRepository.deleteByStatusAndSentAtBefore(2, cutoffDate);
            log.info("清理过期未读推送记录完成，删除 {} 条记录，截止日期: {}", deletedCount, cutoffDate);
        } catch (Exception e) {
            log.error("清理未读推送记录失败", e);
        }
    }

    /**
     * 每周清理MongoDB中的过期数据
     * MongoDB虽然有TTL索引，但这里做二次保障
     */
    @Scheduled(cron = "0 0 3 ? * SUN") // 每周日凌晨3点执行
    public void cleanupMongoDBExpiredData() {
        try {
            LocalDateTime cutoffDate = LocalDateTime.now().minusDays(7);

            // 清理过期的弹幕数据（虽然MongoDB有TTL，但做二次保障）
            barrageRepository.deleteByTimestampBefore(cutoffDate)
                    .subscribe(deletedCount ->
                            log.info("清理MongoDB弹幕数据完成，删除 {} 条记录", deletedCount));

            // 清理过期的直播状态数据
            liveStatusRepository.deleteByTimestampBefore(cutoffDate)
                    .subscribe(deletedCount ->
                            log.info("清理MongoDB直播状态数据完成，删除 {} 条记录", deletedCount));

            // 清理过期的商品监控数据
            productMonitorRepository.deleteByDetectedAtBefore(cutoffDate)
                    .subscribe(deletedCount ->
                            log.info("清理MongoDB商品监控数据完成，删除 {} 条记录", deletedCount));

            log.info("MongoDB数据清理任务启动完成");
        } catch (Exception e) {
            log.error("清理MongoDB数据失败", e);
        }
    }

    /**
     * 每月数据归档任务
     * 将旧数据从热存储迁移到冷存储或进行压缩
     */
    @Scheduled(cron = "0 0 4 1 * ?") // 每月1日凌晨4点执行
    public void monthlyDataArchiving() {
        try {
            LocalDateTime archiveDate = LocalDateTime.now().minusMonths(3);

            // 归档3个月前的推送历史数据
            archiveOldPushLogs(archiveDate);

            // 生成月度统计报告
            generateMonthlyReport();

            log.info("月度数据归档任务完成，归档截止日期: {}", archiveDate);
        } catch (Exception e) {
            log.error("月度数据归档失败", e);
        }
    }

    /**
     * 每日数据完整性检查
     * 检查数据一致性和完整性
     */
    @Scheduled(cron = "0 0 5 * * ?") // 每天凌晨5点执行
    public void dailyDataIntegrityCheck() {
        try {
            // 检查推送历史记录的数据完整性
            long totalPushLogs = pushLogRepository.count();
            long validPushLogs = pushLogRepository.countByUserIdIsNotNull();

            if (totalPushLogs > 0) {
                double integrity = (double) validPushLogs / totalPushLogs * 100;
                log.info("推送历史数据完整性检查: {}/{} ({:.2f}%)", validPushLogs, totalPushLogs, integrity);

                if (integrity < 95.0) {
                    log.warn("推送历史数据完整性低于95%，需要检查数据源");
                }
            }

            // 检查MongoDB数据量
            barrageRepository.count()
                    .subscribe(count -> log.info("当前弹幕数据量: {} 条", count));

            liveStatusRepository.count()
                    .subscribe(count -> log.info("当前直播状态数据量: {} 条", count));

            productMonitorRepository.count()
                    .subscribe(count -> log.info("当前商品监控数据量: {} 条", count));

            log.info("数据完整性检查完成");
        } catch (Exception e) {
            log.error("数据完整性检查失败", e);
        }
    }

    /**
     * 每小时系统性能监控
     * 记录系统运行状态和性能指标
     */
    @Scheduled(cron = "0 0 * * * ?") // 每小时执行
    public void hourlyPerformanceMonitoring() {
        try {
            // 记录当前时间窗口的数据统计
            LocalDateTime oneHourAgo = LocalDateTime.now().minusHours(1);

            // 统计过去一小时的弹幕数量
            barrageRepository.countByTimestampBetween(oneHourAgo, LocalDateTime.now())
                    .subscribe(count -> {
                        log.info("过去一小时弹幕数量: {} 条", count);
                        // 这里可以将统计数据写入性能监控集合
                    });

            // 统计过去一小时的推送数量
            long pushCount = pushLogRepository.countBySentAtAfter(oneHourAgo);
            log.info("过去一小时推送数量: {} 条", pushCount);

            // 记录系统负载信息
            log.info("系统性能监控 - 时间窗口: {} 到 {}", oneHourAgo, LocalDateTime.now());
        } catch (Exception e) {
            log.error("性能监控失败", e);
        }
    }

    /**
     * 归档旧的推送日志数据
     */
    private void archiveOldPushLogs(LocalDateTime cutoffDate) {
        // 这里可以实现数据归档逻辑
        // 例如：将旧数据导出到文件、迁移到其他数据库等
        log.info("开始归档 {} 之前的推送日志数据", cutoffDate);
        // 实际实现中可能需要批量处理和进度跟踪
    }

    /**
     * 生成月度报告
     */
    private void generateMonthlyReport() {
        // 生成月度统计报告
        log.info("开始生成月度统计报告");

        // 统计各类数据量
        // 生成用户活跃度报告
        // 生成平台监控报告
        // 生成AI分析效果报告

        // 实际实现中可以生成PDF报告、发送邮件等
    }
}