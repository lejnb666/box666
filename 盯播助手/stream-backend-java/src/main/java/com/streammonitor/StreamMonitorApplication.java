package com.streammonitor;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.amqp.rabbit.annotation.EnableRabbit;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.transaction.annotation.EnableTransactionManagement;

/**
 * 盯播助手后端应用主启动类
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@SpringBootApplication
@MapperScan("com.streammonitor.repository")
@EnableTransactionManagement
@EnableAspectJAutoProxy(exposeProxy = true)
@EnableCaching
@EnableAsync
@EnableScheduling
@EnableRabbit
public class StreamMonitorApplication {

    public static void main(String[] args) {
        SpringApplication.run(StreamMonitorApplication.class, args);
        System.out.println("\n" +
                "  ____  _                            _   _   _       _        \n" +
                " / ___|| |__   _____   _____ _ __   | | | | | | __ _| |_ __ _ \n" +
                " \___ \| '_ \ / _ \ \ / / _ \ '__|  | |_| | | |/ _` | __/ _` |\n" +
                "  ___) | | | |  __/\ V /  __/ |     |  _  | | | (_| | || (_| |\n" +
                " |____/|_| |_|\___| \_/ \___|_|     |_| |_|_|_|\__,_|\__\__,_|\n" +
                "                                                               \n" +
                "盯播助手后端服务启动成功！" +
                "\n访问地址: http://localhost:8080/api\n");
    }
}