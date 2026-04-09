package com.streammonitor.config;

import com.mongodb.ConnectionString;
import com.mongodb.MongoClientSettings;
import com.mongodb.reactivestreams.client.MongoClient;
import com.mongodb.reactivestreams.client.MongoClients;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.mongodb.config.AbstractReactiveMongoConfiguration;
import org.springframework.data.mongodb.core.ReactiveMongoTemplate;
import org.springframework.data.mongodb.core.WriteResultChecking;
import org.springframework.data.mongodb.repository.config.EnableReactiveMongoRepositories;

/**
 * MongoDB配置类
 * 配置Reactive MongoDB连接和模板
 *
 * @author exbox0403-cmd
 * @since 2026/4/8
 */
@Configuration
@EnableReactiveMongoRepositories(basePackages = "com.streammonitor.repository.mongo")
public class MongoDBConfig extends AbstractReactiveMongoConfiguration {

    @Value("${spring.data.mongodb.host:localhost}")
    private String mongoHost;

    @Value("${spring.data.mongodb.port:27017}")
    private int mongoPort;

    @Value("${spring.data.mongodb.database:stream_monitor}")
    private String databaseName;

    @Value("${spring.data.mongodb.username:mongo_admin}")
    private String username;

    @Value("${spring.data.mongodb.password:mongo_password}")
    private String password;

    @Value("${spring.data.mongodb.authentication-database:admin}")
    private String authDatabase;

    @Override
    protected String getDatabaseName() {
        return databaseName;
    }

    @Bean
    @Override
    public MongoClient reactiveMongoClient() {
        // 构建连接字符串
        String connectionString = String.format(
                "mongodb://%s:%s@%s:%d/%s?authSource=%s&authMechanism=SCRAM-SHA-256",
                username, password, mongoHost, mongoPort, databaseName, authDatabase
        );

        ConnectionString connString = new ConnectionString(connectionString);

        // 配置MongoDB客户端设置
        MongoClientSettings settings = MongoClientSettings.builder()
                .applyConnectionString(connString)
                .applyToConnectionPoolSettings(builder ->
                        builder.maxSize(20)
                                .minSize(5)
                                .maxWaitTime(60000)
                                .maxConnectionLifeTime(120000))
                .applyToSocketSettings(builder ->
                        builder.connectTimeout(30000)
                                .readTimeout(60000))
                .applyToSslSettings(builder ->
                        builder.enabled(false)) // 生产环境应启用SSL
                .build();

        return MongoClients.create(settings);
    }

    @Bean
    public ReactiveMongoTemplate reactiveMongoTemplate() {
        ReactiveMongoTemplate template = new ReactiveMongoTemplate(reactiveMongoClient(), getDatabaseName());
        template.setWriteResultChecking(WriteResultChecking.EXCEPTION);
        return template;
    }

    @Override
    protected boolean autoIndexCreation() {
        return true; // 启用自动索引创建
    }
}