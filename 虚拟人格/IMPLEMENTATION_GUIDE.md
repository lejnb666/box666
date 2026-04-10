# Digital Person System - v2.1 Implementation Guide

## Overview
This document outlines the implementation of the User and Session System (v2.1) for the Digital Person chatbot application. The system now supports multi-user authentication with JWT tokens, session management, and data isolation.

## Architecture

### Backend (Spring Boot)
- **Framework**: Spring Boot 3.2.0 with Java 17
- **Security**: Spring Security + JWT authentication
- **Database**: MySQL with JPA/Hibernate
- **Caching**: Redis for session context and token management
- **API**: RESTful endpoints with CORS support

### Frontend (Uni-app)
- **Framework**: Uni-app with Vue 3
- **State Management**: Pinia (recommended for future implementation)
- **HTTP Client**: uni.request or axios-uniapp

## Database Schema

### Tables

#### 1. `sys_user`
```sql
CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,  -- BCrypt encrypted
    avatar VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `chat_session`
```sql
CREATE TABLE chat_session (
    session_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    session_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES sys_user(id) ON DELETE CASCADE
);
```

#### 3. `chat_message`
```sql
CREATE TABLE chat_message (
    message_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id BIGINT NOT NULL,
    sender_type ENUM('USER', 'AI') NOT NULL,
    content TEXT,
    tokens_used INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_session(session_id) ON DELETE CASCADE
);
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login

### Session Management
- `POST /api/sessions?sessionName={name}` - Create new session
- `GET /api/sessions` - Get user's sessions
- `DELETE /api/sessions/{sessionId}` - Delete session

### Chat
- `POST /api/chat` - Send message
- `GET /api/messages/{sessionId}` - Get session messages

## Security Implementation

### JWT Authentication Flow
1. User registers or logs in
2. Server validates credentials
3. JWT token generated with user_id in payload
4. Token sent to client and stored (localStorage/sessionStorage)
5. All subsequent requests include `Authorization: Bearer {token}` header
6. Server validates token via `JwtRequestFilter`

### Password Security
- BCrypt password encoder with salt
- Minimum 6 characters for password
- Passwords never stored in plain text

### Data Isolation
- All SQL queries include `WHERE user_id = ?` clause
- Users can only access their own sessions and messages
- JWT token contains user_id for validation

## Redis Integration

### Token Management
- **Whitelist**: Valid tokens stored with expiration
- **Blacklist**: Invalidated tokens (for logout functionality)
- **Keys**: `token:whitelist:{token}`, `token:blacklist:{token}`

### Session Context
- **Purpose**: Store conversation history for context-aware responses
- **Structure**: Redis List with max 10 messages per session
- **Key Format**: `session:context:{sessionId}`
- **Expiration**: 24 hours

### User Status
- **Online Tracking**: `user:online:{userId}` with 30-minute expiration
- **Session Info**: Store device/session information

## Frontend Integration Guide

### 1. Authentication
```javascript
// Login
const login = async (username, password) => {
  const response = await uni.request({
    url: 'http://localhost:8080/api/auth/login',
    method: 'POST',
    data: { username, password }
  });

  if (response.data.token) {
    uni.setStorageSync('token', response.data.token);
    uni.setStorageSync('userId', response.data.userId);
    return true;
  }
  return false;
};
```

### 2. API Requests with Token
```javascript
const apiRequest = async (url, method = 'GET', data = null) => {
  const token = uni.getStorageSync('token');

  return await uni.request({
    url: `http://localhost:8080${url}`,
    method,
    data,
    header: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
};
```

### 3. Session Management
```javascript
// Create session
const createSession = async (sessionName) => {
  const response = await apiRequest(`/api/sessions?sessionName=${sessionName}`, 'POST');
  return response.data;
};

// Get sessions
const getSessions = async () => {
  const response = await apiRequest('/api/sessions');
  return response.data;
};
```

### 4. Chat Interface
```javascript
// Send message
const sendMessage = async (message, sessionId = null) => {
  const response = await apiRequest('/api/chat', 'POST', {
    message,
    sessionId
  });
  return response.data;
};

// Get messages
const getMessages = async (sessionId) => {
  const response = await apiRequest(`/api/messages/${sessionId}`);
  return response.data;
};
```

## Configuration

### application.properties
```properties
# Database
spring.datasource.url=jdbc:mysql://localhost:3306/digital_person?useSSL=false&serverTimezone=UTC
spring.datasource.username=root
spring.datasource.password=root

# Redis
spring.redis.host=localhost
spring.redis.port=6379

# JWT
jwt.secret=your-secret-key-here
jwt.expiration=86400

# LLM
llm.api.key=your-api-key
llm.api.url=https://api.deepseek.com/v1/chat/completions
```

## Setup Instructions

### Prerequisites
1. Java 17
2. MySQL 8.0+
3. Redis 6.0+
4. Maven

### Database Setup
```bash
# Create database and tables
mysql -u root -p < database/schema.sql
```

### Backend Setup
```bash
cd digital-person-backend
mvn clean install
mvn spring-boot:run
```

### Redis Setup
```bash
# Start Redis server
redis-server

# Optional: Monitor Redis
redis-cli monitor
```

## Security Best Practices

1. **Environment Variables**: Store sensitive data (API keys, JWT secret) in environment variables
2. **HTTPS**: Use HTTPS in production
3. **CORS**: Configure allowed origins properly
4. **Rate Limiting**: Implement rate limiting for API endpoints
5. **Input Validation**: Validate all user inputs
6. **Error Handling**: Don't expose sensitive information in error messages

## Performance Considerations

1. **Database Indexes**: Proper indexes on frequently queried columns
2. **Connection Pooling**: HikariCP for database connections
3. **Redis Caching**: Session context to reduce database queries
4. **Batch Operations**: For bulk operations
5. **Pagination**: For large datasets

## Future Enhancements (v2.2+)

1. **Admin Dashboard**: Vue 3 + Element Plus management interface
2. **Analytics**: User activity, token usage, performance metrics
3. **Multi-tenant Support**: For SaaS deployment
4. **Billing System**: Token-based usage tracking
5. **Model Switching**: Multiple LLM provider support
6. **Mobile Optimization**: Native app packaging with Uni-app

## Troubleshooting

### Common Issues

1. **Database Connection**: Check MySQL service and credentials
2. **Redis Connection**: Verify Redis server is running
3. **JWT Token**: Ensure token is included in Authorization header
4. **CORS Errors**: Check allowed origins in SecurityConfig

### Debug Mode
Enable debug logging in `application.properties`:
```properties
logging.level.com.digitalperson=DEBUG
logging.level.org.springframework.security=DEBUG
```

## Testing

### Sample Requests

**Register User:**
```bash
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

**Create Session:**
```bash
curl -X POST "http://localhost:8080/api/sessions?sessionName=Test%20Chat" \
  -H "Authorization: Bearer {token}"
```

**Send Message:**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello, how are you?","sessionId":1}'
```

---

*This implementation guide covers v2.1 of the Digital Person System. For subsequent versions (v2.2+), refer to the project roadmap in the main documentation.*