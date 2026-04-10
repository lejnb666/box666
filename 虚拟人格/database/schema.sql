-- MySQL Database Schema for Digital Person System
-- Version: 2.1

-- Create database
CREATE DATABASE IF NOT EXISTS digital_person CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE digital_person;

-- Users table
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    avatar VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_session (
    session_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    session_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_message (
    message_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    sender_type ENUM('USER', 'AI') NOT NULL,
    content TEXT,
    tokens_used INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_sender_type (sender_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert sample data
INSERT INTO sys_user (username, password, avatar) VALUES
('testuser', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'default-avatar.png'),
('admin', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin-avatar.png');

-- Note: The password above is BCrypt hash for 'password'

-- Optional: Create views for analytics
CREATE VIEW IF NOT EXISTS daily_active_users AS
SELECT
    DATE(created_at) as date,
    COUNT(DISTINCT user_id) as active_users
FROM chat_session
WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY DATE(created_at);

CREATE VIEW IF NOT EXISTS message_stats AS
SELECT
    session_id,
    COUNT(*) as total_messages,
    SUM(CASE WHEN sender_type = 'USER' THEN 1 ELSE 0 END) as user_messages,
    SUM(CASE WHEN sender_type = 'AI' THEN 1 ELSE 0 END) as ai_messages,
    SUM(tokens_used) as total_tokens
FROM chat_message
GROUP BY session_id;