package com.streammonitor.service.impl;

import com.streammonitor.service.BarrageAggregationService;
import com.streammonitor.model.document.BarrageDocument;
import com.streammonitor.model.dto.BarrageMinuteSummary;
import com.streammonitor.model.dto.BarrageHourlySummary;
import com.streammonitor.model.dto.BarrageDailySummary;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.AggregationResults;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;

/**
 * 弹幕聚合服务实现类
 * 负责实时聚合MongoDB中的弹幕数据并保存到MySQL
 */
@Service
@Slf4j
@Data
public class BarrageAggregationServiceImpl implements BarrageAggregationService {

    @Autowired
    private MongoTemplate mongoTemplate;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    private static final String BARRAGE_COLLECTION = "barrage";
    private static final String HOURLY_AGGREGATION_COLLECTION = "barrage_hourly_aggregation";
    private static final String DAILY_AGGREGATION_COLLECTION = "barrage_daily_aggregation";

    /**
     * 每分钟执行一次聚合 - 实时聚合
     */
    @Override
    @Scheduled(cron = "0 * * * * ?")
    public void aggregateMinuteData() {
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime minuteStart = now.withSecond(0).withNano(0);
            LocalDateTime minuteEnd = minuteStart.plusMinutes(1);

            log.info("开始执行分钟级聚合: {} - {}", minuteStart, minuteEnd);

            // 聚合MongoDB中的原始数据
            Aggregation aggregation = Aggregation.newAggregation(
                Aggregation.match(Criteria.where("timestamp")
                    .gte(Date.from(minuteStart.atZone(ZoneId.systemDefault()).toInstant()))
                    .lt(Date.from(minuteEnd.atZone(ZoneId.systemDefault()).toInstant()))),
                Aggregation.group("streamerId", "streamerName")
                    .count().as("barrageCount")
                    .sum("giftValue").as("totalGiftValue")
                    .addToSet("userId").as("uniqueUsers")
                    .avg("contentLength").as("avgContentLength"),
                Aggregation.project()
                    .andExpression("_id.streamerId").as("streamerId")
                    .andExpression("_id.streamerName").as("streamerName")
                    .and("barrageCount").as("barrageCount")
                    .and("totalGiftValue").as("totalGiftValue")
                    .andArraySize("uniqueUsers").as("uniqueUserCount")
                    .and("avgContentLength").as("avgContentLength")
                    .and(Date.from(minuteStart.atZone(ZoneId.systemDefault()).toInstant())).as("minuteTime")
            );

            AggregationResults<BarrageMinuteSummary> results =
                mongoTemplate.aggregate(aggregation, BARRAGE_COLLECTION, BarrageMinuteSummary.class);

            // 保存到MySQL
            for (BarrageMinuteSummary summary : results.getMappedResults()) {
                saveMinuteSummaryToMySQL(summary, minuteStart);
            }

            log.info("分钟级聚合完成，处理了 {} 个主播的数据", results.getMappedResults().size());

        } catch (Exception e) {
            log.error("分钟级聚合执行失败", e);
        }
    }

    /**
     * 每小时执行一次聚合
     */
    @Override
    @Scheduled(cron = "0 0 * * * ?")
    public void aggregateHourlyData() {
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime hourStart = now.minusHours(1).withMinute(0).withSecond(0).withNano(0);
            LocalDateTime hourEnd = hourStart.plusHours(1);

            log.info("开始执行小时级聚合: {} - {}", hourStart, hourEnd);

            // 聚合MySQL中的分钟数据
            String sql = """
                SELECT
                    streamer_id,
                    streamer_name,
                    SUM(barrage_count) as total_barrage_count,
                    SUM(unique_user_count) as total_unique_users,
                    SUM(total_gift_value) as total_gift_value,
                    AVG(avg_content_length) as avg_content_length,
                    COUNT(*) as minute_count
                FROM barrage_summary
                WHERE minute_time >= ? AND minute_time < ?
                GROUP BY streamer_id, streamer_name
                """;

            List<BarrageHourlySummary> hourlySummaries = jdbcTemplate.query(sql,
                (rs, rowNum) -> {
                    BarrageHourlySummary summary = new BarrageHourlySummary();
                    summary.setStreamerId(rs.getString("streamer_id"));
                    summary.setStreamerName(rs.getString("streamer_name"));
                    summary.setTotalBarrageCount(rs.getInt("total_barrage_count"));
                    summary.setTotalUniqueUsers(rs.getInt("total_unique_users"));
                    summary.setTotalGiftValue(rs.getDouble("total_gift_value"));
                    summary.setAvgContentLength(rs.getDouble("avg_content_length"));
                    summary.setMinuteCount(rs.getInt("minute_count"));
                    summary.setHourTime(hourStart);
                    return summary;
                },
                hourStart,
                hourEnd
            );

            // 保存小时聚合数据到MongoDB
            for (BarrageHourlySummary summary : hourlySummaries) {
                saveHourlySummaryToMongoDB(summary);
            }

            log.info("小时级聚合完成，处理了 {} 个主播的数据", hourlySummaries.size());

        } catch (Exception e) {
            log.error("小时级聚合执行失败", e);
        }
    }

    /**
     * 每日执行一次聚合
     */
    @Override
    @Scheduled(cron = "0 0 1 * * ?")
    public void aggregateDailyData() {
        try {
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime dayStart = now.minusDays(1).withHour(0).withMinute(0).withSecond(0).withNano(0);
            LocalDateTime dayEnd = dayStart.plusDays(1);

            log.info("开始执行日级聚合: {} - {}", dayStart, dayEnd);

            // 聚合MongoDB中的小时数据
            Aggregation aggregation = Aggregation.newAggregation(
                Aggregation.match(Criteria.where("hourTime")
                    .gte(Date.from(dayStart.atZone(ZoneId.systemDefault()).toInstant()))
                    .lt(Date.from(dayEnd.atZone(ZoneId.systemDefault()).toInstant()))),
                Aggregation.group("streamerId", "streamerName")
                    .sum("totalBarrageCount").as("totalBarrageCount")
                    .sum("totalUniqueUsers").as("totalUniqueUsers")
                    .sum("totalGiftValue").as("totalGiftValue")
                    .avg("avgContentLength").as("avgContentLength")
                    .count().as("hourCount"),
                Aggregation.project()
                    .andExpression("_id.streamerId").as("streamerId")
                    .andExpression("_id.streamerName").as("streamerName")
                    .and("totalBarrageCount").as("totalBarrageCount")
                    .and("totalUniqueUsers").as("totalUniqueUsers")
                    .and("totalGiftValue").as("totalGiftValue")
                    .and("avgContentLength").as("avgContentLength")
                    .and("hourCount").as("hourCount")
                    .and(Date.from(dayStart.atZone(ZoneId.systemDefault()).toInstant())).as("date")
            );

            AggregationResults<BarrageDailySummary> results =
                mongoTemplate.aggregate(aggregation, HOURLY_AGGREGATION_COLLECTION, BarrageDailySummary.class);

            // 保存日聚合数据到MongoDB
            for (BarrageDailySummary summary : results.getMappedResults()) {
                saveDailySummaryToMongoDB(summary);
            }

            log.info("日级聚合完成，处理了 {} 个主播的数据", results.getMappedResults().size());

        } catch (Exception e) {
            log.error("日级聚合执行失败", e);
        }
    }

    /**
     * 保存分钟聚合数据到MySQL
     */
    @Transactional
    public void saveMinuteSummaryToMySQL(BarrageMinuteSummary summary, LocalDateTime minuteTime) {
        String sql = """
            INSERT INTO barrage_summary
            (streamer_id, streamer_name, minute_time, barrage_count,
             unique_user_count, total_gift_value, avg_content_length, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
            ON DUPLICATE KEY UPDATE
            barrage_count = VALUES(barrage_count),
            unique_user_count = VALUES(unique_user_count),
            total_gift_value = VALUES(total_gift_value),
            avg_content_length = VALUES(avg_content_length),
            updated_at = NOW()
            """;

        jdbcTemplate.update(sql,
            summary.getStreamerId(),
            summary.getStreamerName(),
            minuteTime,
            summary.getBarrageCount(),
            summary.getUniqueUserCount(),
            summary.getTotalGiftValue(),
            summary.getAvgContentLength()
        );
    }

    /**
     * 保存小时聚合数据到MongoDB
     */
    public void saveHourlySummaryToMongoDB(BarrageHourlySummary summary) {
        try {
            // 检查是否已存在
            Criteria criteria = Criteria.where("streamerId").is(summary.getStreamerId())
                .and("hourTime").is(summary.getHourTime());

            if (mongoTemplate.exists(Query.query(criteria), HOURLY_AGGREGATION_COLLECTION)) {
                // 更新现有记录
                Update update = new Update()
                    .set("totalBarrageCount", summary.getTotalBarrageCount())
                    .set("totalUniqueUsers", summary.getTotalUniqueUsers())
                    .set("totalGiftValue", summary.getTotalGiftValue())
                    .set("avgContentLength", summary.getAvgContentLength())
                    .set("minuteCount", summary.getMinuteCount())
                    .set("updatedAt", new Date());

                mongoTemplate.updateFirst(Query.query(criteria), update, HOURLY_AGGREGATION_COLLECTION);
            } else {
                // 插入新记录
                mongoTemplate.save(summary, HOURLY_AGGREGATION_COLLECTION);
            }

        } catch (Exception e) {
            log.error("保存小时聚合数据到MongoDB失败", e);
        }
    }

    /**
     * 保存日聚合数据到MongoDB
     */
    public void saveDailySummaryToMongoDB(BarrageDailySummary summary) {
        try {
            // 检查是否已存在
            Criteria criteria = Criteria.where("streamerId").is(summary.getStreamerId())
                .and("date").is(summary.getDate());

            if (mongoTemplate.exists(Query.query(criteria), DAILY_AGGREGATION_COLLECTION)) {
                // 更新现有记录
                Update update = new Update()
                    .set("totalBarrageCount", summary.getTotalBarrageCount())
                    .set("totalUniqueUsers", summary.getTotalUniqueUsers())
                    .set("totalGiftValue", summary.getTotalGiftValue())
                    .set("avgContentLength", summary.getAvgContentLength())
                    .set("hourCount", summary.getHourCount())
                    .set("updatedAt", new Date());

                mongoTemplate.updateFirst(Query.query(criteria), update, DAILY_AGGREGATION_COLLECTION);
            } else {
                // 插入新记录
                mongoTemplate.save(summary, DAILY_AGGREGATION_COLLECTION);
            }

        } catch (Exception e) {
            log.error("保存日聚合数据到MongoDB失败", e);
        }
    }

    /**
     * 获取指定主播的聚合数据
     */
    @Override
    public List<BarrageMinuteSummary> getStreamerAggregatedData(String streamerId, LocalDateTime startTime, LocalDateTime endTime) {
        String sql = """
            SELECT
                streamer_id,
                streamer_name,
                minute_time,
                barrage_count,
                unique_user_count,
                total_gift_value,
                avg_content_length
            FROM barrage_summary
            WHERE streamer_id = ?
              AND minute_time >= ?
              AND minute_time <= ?
            ORDER BY minute_time
            """;

        return jdbcTemplate.query(sql,
            (rs, rowNum) -> {
                BarrageMinuteSummary summary = new BarrageMinuteSummary();
                summary.setStreamerId(rs.getString("streamer_id"));
                summary.setStreamerName(rs.getString("streamer_name"));
                summary.setMinuteTime(rs.getObject("minute_time", LocalDateTime.class));
                summary.setBarrageCount(rs.getInt("barrage_count"));
                summary.setUniqueUserCount(rs.getInt("unique_user_count"));
                summary.setTotalGiftValue(rs.getDouble("total_gift_value"));
                summary.setAvgContentLength(rs.getDouble("avg_content_length"));
                return summary;
            },
            streamerId, startTime, endTime
        );
    }

    /**
     * 清理过期的聚合数据
     */
    @Override
    @Scheduled(cron = "0 0 2 * * ?") // 每天凌晨2点执行
    public void cleanupExpiredData() {
        try {
            LocalDateTime thirtyDaysAgo = LocalDateTime.now().minusDays(30);

            // 清理MySQL中30天前的分钟聚合数据
            String deleteSql = "DELETE FROM barrage_summary WHERE minute_time < ?";
            int deletedCount = jdbcTemplate.update(deleteSql, thirtyDaysAgo);

            log.info("清理过期数据完成，删除了 {} 条记录", deletedCount);

        } catch (Exception e) {
            log.error("清理过期数据失败", e);
        }
    }
}