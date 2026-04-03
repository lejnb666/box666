package com.insightweaver;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Main application class for InsightWeaver Backend
 *
 * This microservice handles:
 * - User authentication and authorization
 * - Task queue management with RabbitMQ
 * - History storage and billing control
 * - SSE communication bridge to frontend
 * - Integration with AI Engine microservice
 */
@SpringBootApplication
@ConfigurationPropertiesScan
@EnableJpaAuditing
@EnableAsync
@EnableScheduling
public class InsightWeaverBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(InsightWeaverBackendApplication.class, args);
    }
}