# Testing Guide for Digital Person System v2.1

## Automated Tests

### Backend Tests
The following test classes should be created to ensure system reliability:

#### 1. Authentication Tests
```java
@SpringBootTest
class AuthServiceTest {
    // Test user registration
    // Test user login
    // Test invalid credentials
    // Test duplicate username
}
```

#### 2. Session Tests
```java
@SpringBootTest
class SessionServiceTest {
    // Test session creation
    // Test session retrieval by user
    // Test session deletion
    // Test unauthorized access prevention
}
```

#### 3. Chat Tests
```java
@SpringBootTest
class ChatServiceTest {
    // Test message processing
    // Test context handling
    // Test RAG integration
    // Test error handling
}
```

## Manual Testing Checklist

### 1. Database Setup ✅
- [ ] MySQL server running
- [ ] Database created: `digital_person`
- [ ] Tables created: `sys_user`, `chat_session`, `chat_message`
- [ ] Sample data inserted

### 2. Redis Setup ✅
- [ ] Redis server running on localhost:6379
- [ ] Redis connection test successful
- [ ] Token management working
- [ ] Session context storage working

### 3. Backend Startup ✅
- [ ] Spring Boot application starts without errors
- [ ] Database connection established
- [ ] Redis connection established
- [ ] Security configuration loaded
- [ ] All endpoints accessible

### 4. Authentication Testing ✅

#### Registration
- [ ] Register new user with valid credentials
- [ ] Registration fails with existing username
- [ ] Registration fails with short password (< 6 chars)
- [ ] Registration fails with empty username
- [ ] Password is properly hashed in database

#### Login
- [ ] Login succeeds with correct credentials
- [ ] Login fails with incorrect password
- [ ] Login fails with non-existent username
- [ ] JWT token is returned on successful login
- [ ] Token contains user_id in payload

### 5. Session Management Testing ✅

#### Session Creation
- [ ] Create session with authenticated user
- [ ] Session creation fails without authentication
- [ ] Session name is properly stored
- [ ] User ID is correctly associated

#### Session Retrieval
- [ ] Get user sessions returns only user's sessions
- [ ] Sessions are ordered by creation date (descending)
- [ ] Empty list returned for user with no sessions

#### Session Deletion
- [ ] Delete session succeeds with valid session ID
- [ ] Delete session fails with non-existent session ID
- [ ] Delete session fails for session belonging to another user
- [ ] Associated messages are also deleted (cascade)

### 6. Chat Functionality Testing ✅

#### Message Sending
- [ ] Send message with existing session
- [ ] Send message without session (auto-create)
- [ ] Message is saved to database
- [ ] AI response is generated and saved
- [ ] Session ID is returned in response

#### Message Retrieval
- [ ] Get session messages returns correct messages
- [ ] Messages are ordered by timestamp
- [ ] Only messages from authorized session are returned
- [ ] Both user and AI messages are included

#### Context Handling
- [ ] Recent messages are used as context
- [ ] Context is limited to last 10 messages
- [ ] System prompt is properly integrated
- [ ] RAG enhancement is applied

### 7. Security Testing ✅

#### JWT Validation
- [ ] Requests without token are rejected
- [ ] Requests with invalid token are rejected
- [ ] Requests with expired token are rejected
- [ ] Token is validated for each protected endpoint

#### Data Isolation
- [ ] User A cannot access User B's sessions
- [ ] User A cannot access User B's messages
- [ ] User A cannot delete User B's sessions
- [ ] Session ownership is properly validated

#### Input Validation
- [ ] Empty messages are rejected
- [ ] SQL injection attempts are blocked
- [ ] XSS prevention is in place
- [ ] Input length limits are enforced

### 8. Redis Integration Testing ✅

#### Token Management
- [ ] Valid tokens are stored in whitelist
- [ ] Expired tokens are automatically removed
- [ ] Blacklist functionality works for logout
- [ ] Token validation uses Redis cache

#### Session Context
- [ ] Messages are stored in session context
- [ ] Context is limited to 10 messages
- [ ] Context expires after 24 hours
- [ ] Context is retrieved for chat processing

#### User Status
- [ ] Online users are tracked
- [ ] User status expires after 30 minutes
- [ ] Status is cleared on logout

### 9. Error Handling Testing ✅

#### API Error Responses
- [ ] 400 Bad Request for invalid input
- [ ] 401 Unauthorized for missing/invalid token
- [ ] 403 Forbidden for unauthorized access
- [ ] 404 Not Found for non-existent resources
- [ ] 500 Internal Server Error for unexpected issues

#### Graceful Degradation
- [ ] System works without RAG service
- [ ] System works without Redis (fallback)
- [ ] Database errors are handled gracefully
- [ ] Network timeouts are handled

### 10. Performance Testing ✅

#### Response Times
- [ ] Authentication requests < 500ms
- [ ] Session operations < 200ms
- [ ] Chat responses < 3 seconds (including AI)
- [ ] Message retrieval < 300ms

#### Concurrent Users
- [ ] System handles 10 concurrent users
- [ ] System handles 50 concurrent users
- [ ] Database connection pool handles load
- [ ] Redis handles concurrent operations

## Test Data

### Sample Users
```sql
-- Test users for manual testing
INSERT INTO sys_user (username, password, avatar) VALUES
('alice', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'alice-avatar.png'),
('bob', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'bob-avatar.png'),
('charlie', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'charlie-avatar.png');
```

### Sample Sessions
```sql
-- Sample sessions for testing
INSERT INTO chat_session (user_id, session_name, created_at) VALUES
(1, 'Alice General Chat', NOW() - INTERVAL 2 DAY),
(1, 'Alice Technical Discussion', NOW() - INTERVAL 1 DAY),
(2, 'Bob Project Planning', NOW() - INTERVAL 3 HOUR),
(3, 'Charlie Research', NOW() - INTERVAL 30 MINUTE);
```

### Sample Messages
```sql
-- Sample messages for context testing
INSERT INTO chat_message (session_id, sender_type, content, tokens_used, created_at) VALUES
(1, 'USER', 'Hello, can you help me with my project?', 10, NOW() - INTERVAL 2 DAY),
(1, 'AI', 'Of course! I\'d be happy to help. What kind of project are you working on?', 15, NOW() - INTERVAL 2 DAY),
(1, 'USER', 'I\'m building a chatbot application.', 8, NOW() - INTERVAL 2 DAY),
(1, 'AI', 'That sounds interesting! What features are you planning to include?', 12, NOW() - INTERVAL 2 DAY);
```

## Testing Tools

### API Testing
- **Postman**: Import collection for endpoint testing
- **curl**: Command-line testing
- **Swagger/OpenAPI**: API documentation and testing

### Database Testing
- **MySQL Workbench**: Visual database management
- **DBeaver**: Database client
- **Command line**: Direct SQL queries

### Redis Testing
- **redis-cli**: Command-line interface
- **Redis Desktop Manager**: GUI tool
- **Telnet**: Connection testing

### Load Testing
- **JMeter**: Performance and load testing
- **Artillery**: API load testing
- **k6**: Modern load testing tool

## Test Environment Setup

### Development Environment
```bash
# Start services
docker-compose up -d mysql redis

# Run backend
cd digital-person-backend
mvn spring-boot:run

# Test endpoints
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}'
```

### Production Testing
- Use staging environment that mirrors production
- Test with production-like data volumes
- Verify all security measures are in place
- Test backup and recovery procedures

## Monitoring and Logging

### Application Logs
- Check Spring Boot application logs for errors
- Monitor authentication attempts
- Track API response times
- Log security-related events

### Database Monitoring
- Monitor query performance
- Check connection pool usage
- Track table growth
- Monitor index usage

### Redis Monitoring
- Monitor memory usage
- Track hit/miss ratios
- Monitor connection count
- Check key expiration

## Reporting Issues

When reporting issues, include:
1. Steps to reproduce
2. Expected behavior
3. Actual behavior
4. Environment details (OS, Java version, etc.)
5. Relevant log entries
6. Screenshots (if applicable)

## Test Results Template

```markdown
## Test Execution Report

**Date**: [Date]
**Environment**: [Development/Staging/Production]
**Version**: v2.1

### Passed Tests
- [ ] Authentication
- [ ] Session Management
- [ ] Chat Functionality
- [ ] Security
- [ ] Redis Integration
- [ ] Error Handling
- [ ] Performance

### Failed Tests
- [ ] Test Name: [Description]
  - Issue: [Details]
  - Priority: [High/Medium/Low]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]

### Next Steps
- [Action Item 1]
- [Action Item 2]
```

---

*This testing guide ensures comprehensive validation of the Digital Person System v2.1. All tests should pass before proceeding to production deployment.*