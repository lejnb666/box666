package com.streammonitor.config;

import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Redisson配置类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Configuration
public class RedissonConfig {

    @Value("${spring.redis.host:localhost}")
    private String redisHost;

    @Value("${spring.redis.port:6379}")
    private int redisPort;

    @Value("${spring.redis.password:}")
    private String redisPassword;

    @Value("${spring.redis.database:0}")
    private int redisDatabase;

    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();

        // 单节点配置
        if (redisPassword != null && !redisPassword.isEmpty()) {
            config.useSingleServer()
                    .setAddress("redis://" + redisHost + ":" + redisPort)
                    .setPassword(redisPassword)
                    .setDatabase(redisDatabase)
                    .setConnectionPoolSize(64)
                    .setConnectionMinimumIdleSize(10)
                    .setIdleConnectionTimeout(10000)
                    .setConnectTimeout(10000)
                    .setRetryAttempts(3)
                    .setRetryInterval(1500)
                    .setTimeout(3000)
                    .setPingConnectionInterval(30000);
        } else {
            config.useSingleServer()
                    .setAddress("redis://" + redisHost + ":" + redisPort)
                    .setDatabase(redisDatabase)
                    .setConnectionPoolSize(64)
                    .setConnectionMinimumIdleSize(10)
                    .setIdleConnectionTimeout(10000)
                    .setConnectTimeout(10000)
                    .setRetryAttempts(3)
                    .setRetryInterval(1500)
                    .setTimeout(3000)
                    .setPingConnectionInterval(30000);
        }

        return Redisson.create(config);
    }
}