# InsightWeaver System Architecture

## Overview

InsightWeaver is a multi-agent automated research and report generation system built with a microservices architecture. The system leverages AI agents working collaboratively to transform complex research requests into comprehensive, well-structured reports.

## System Components

### 1. Frontend (Vue 3 + Element Plus)
- **Purpose**: User interface for research task management and real-time monitoring
- **Key Features**:
  - Streamlined conversation interface
  - Real-time agent workflow visualization
  - Live progress tracking with SSE
  - Responsive design with dark/light theme support
- **Technology Stack**:
  - Vue 3 (Composition API)
  - Element Plus UI Framework
  - Pinia for state management
  - Axios for HTTP requests
  - Server-Sent Events for real-time updates

### 2. Backend Gateway (Java Spring Boot)
- **Purpose**: Central orchestration layer for user management, task routing, and API gateway
- **Key Features**:
  - JWT-based authentication and authorization
  - Task queue management with RabbitMQ
  - SSE communication bridge to frontend
  - Integration with AI Engine microservice
  - Rate limiting and billing control
- **Technology Stack**:
  - Spring Boot 3.x
  - Spring Security
  - Spring Data JPA
  - RabbitMQ for message queuing
  - Redis for caching and sessions
  - PostgreSQL for persistent storage

### 3. AI Engine (Python FastAPI + LangGraph)
- **Purpose**: Core AI processing with multi-agent collaboration
- **Key Features**:
  - Multi-agent workflow orchestration
  - LLM integration (OpenAI, Anthropic)
  - Vector database operations
  - Tool integration and external API calls
  - Memory management system
- **Technology Stack**:
  - FastAPI for async web framework
  - LangChain/LangGraph for agent workflows
  - ChromaDB for vector storage
  - Redis for short-term memory
  - Various search APIs and web scraping tools

## Multi-Agent Architecture

### Agent Types

#### 1. Planning Agent
- **Responsibility**: Task decomposition and workflow planning
- **Key Functions**:
  - Analyze research requirements
  - Break down complex tasks into sub-tasks
  - Create execution plans with dependencies
  - Estimate resource requirements and timeline
- **Tools**: LLM reasoning, task decomposition algorithms

#### 2. Research Agent
- **Responsibility**: Information gathering from various sources
- **Key Functions**:
  - Execute web searches
  - Query academic databases (ArXiv)
  - Scrape and parse web content
  - Validate source quality and relevance
  - Implement self-reflection for failed searches
- **Tools**: Google Search API, ArXiv API, web scrapers, content parsers

#### 3. Analysis Agent
- **Responsibility**: Data processing, validation, and insight extraction
- **Key Functions**:
  - Cross-validate information across sources
  - Remove duplicates and contradictions
  - Extract key data points and insights
  - Identify patterns and relationships
  - Generate structured data summaries
- **Tools**: Data processing libraries, validation algorithms, pattern recognition

#### 4. Writing Agent
- **Responsibility**: Report generation and formatting
- **Key Functions**:
  - Synthesize information into coherent narrative
  - Apply user-specified tone and style
  - Generate citations and references
  - Format output in requested format (Markdown, HTML, etc.)
  - Ensure consistency and readability
- **Tools**: LLM text generation, template systems, formatting libraries

## Data Flow

### 1. Task Creation Flow
```
User → Frontend → Backend Gateway → RabbitMQ → AI Engine → Workflow Manager → Planning Agent
```

### 2. Research Execution Flow
```nPlanning Agent → Research Agent → Analysis Agent → Writing Agent → Backend Gateway → Frontend (via SSE)
```

### 3. Real-time Updates Flow
```nAI Engine → Redis Pub/Sub → Backend Gateway → SSE → Frontend
```

## Communication Patterns

### 1. Synchronous Communication
- **Frontend ↔ Backend Gateway**: REST API over HTTP/HTTPS
- **Backend Gateway ↔ AI Engine**: HTTP requests for task initiation

### 2. Asynchronous Communication
- **Task Processing**: RabbitMQ message queues
- **Real-time Updates**: Server-Sent Events (SSE)
- **Inter-agent Communication**: Redis pub/sub and shared state

### 3. Data Persistence
- **Short-term Memory**: Redis (conversation history, session data, agent states)
- **Long-term Memory**: ChromaDB (research results, user preferences, learned patterns)
- **Persistent Storage**: PostgreSQL (user accounts, task metadata, billing)

## Memory Management

### Hierarchical Memory System

#### Short-term Memory (Redis)
- **Purpose**: Active conversation context and real-time state
- **Data Types**:
  - Conversation history (last 50 messages)
  - Agent execution states
  - Task progress information
  - User session data
- **TTL**: 1 hour to 24 hours
- **Access Pattern**: High-frequency, low-latency reads/writes

#### Long-term Memory (ChromaDB)
- **Purpose**: Persistent knowledge and learned patterns
- **Data Types**:
  - Research results and reports
  - User preferences and behavior patterns
  - Agent performance metrics
  - Successful strategies and templates
- **Access Pattern**: Semantic similarity search, periodic updates

### Memory Operations

#### Writing to Memory
```python
# Short-term memory (Redis)
await redis_service.set_hash(f"task:{task_id}:agent_state:{agent_name}", state_data, ttl=3600)

# Long-term memory (ChromaDB)
await chroma_service.add_document(
    collection_name="research_memories",
    document_id=document_id,
    content=content,
    metadata=metadata
)
```

#### Reading from Memory
```python
# Short-term memory retrieval
conversation_history = await redis_service.get_conversation_history(task_id, limit=10)

# Long-term memory retrieval (semantic search)
similar_research = await chroma_service.find_similar_research(query, n_results=5)
```

## Scalability Considerations

### Horizontal Scaling
- **Frontend**: Stateless, can be scaled horizontally with load balancer
- **Backend Gateway**: Stateless services, session data in Redis
- **AI Engine**: Agent instances can be scaled independently
- **Message Queue**: RabbitMQ supports clustering and mirrored queues

### Vertical Scaling
- **Redis**: Can be scaled with Redis Cluster for larger datasets
- **ChromaDB**: Supports distributed deployment for larger vector collections
- **PostgreSQL**: Can be scaled with read replicas and connection pooling

### Performance Optimizations
- **Caching**: Multi-level caching (Redis, browser cache, CDN)
- **Connection Pooling**: Database and external API connections
- **Async Processing**: Non-blocking I/O operations throughout
- **Batch Processing**: Bulk operations for memory updates

## Security Architecture

### Authentication & Authorization
- **JWT-based authentication** with refresh tokens
- **Role-based access control** for different user types
- **API key management** for external service integrations
- **Rate limiting** to prevent abuse

### Data Security
- **Encryption at rest**: Database encryption
- **Encryption in transit**: TLS for all communications
- **Data anonymization**: For training and analytics
- **Access logging**: Comprehensive audit trails

### Infrastructure Security
- **Network segmentation**: Microservices in private subnets
- **API gateway**: Single entry point with security controls
- **Container security**: Docker image scanning and runtime protection
- **Secret management**: Environment variables and secret stores

## Monitoring and Observability

### Metrics Collection
- **Application metrics**: Request rates, error rates, latency
- **Business metrics**: Task completion rates, user engagement
- **System metrics**: CPU, memory, disk usage, queue lengths
- **AI metrics**: Token usage, model performance, agent success rates

### Logging Strategy
- **Structured logging**: JSON format for machine parsing
- **Log levels**: DEBUG, INFO, WARNING, ERROR with appropriate filtering
- **Distributed tracing**: Request correlation across services
- **Error tracking**: Centralized error collection and alerting

### Alerting
- **Performance alerts**: Response time degradation, error rate spikes
- **Business alerts**: Unusual usage patterns, task failures
- **System alerts**: Resource exhaustion, service unavailability
- **Security alerts**: Suspicious activities, failed authentication attempts

## Deployment Architecture

### Development Environment
- **Local development**: Docker Compose for all services
- **Hot reloading**: For frontend and AI engine development
- **Mock services**: For testing without external dependencies

### Production Environment
- **Container orchestration**: Kubernetes or Docker Swarm
- **Load balancing**: Nginx or cloud load balancers
- **Auto-scaling**: Based on CPU, memory, and request metrics
- **Blue-green deployment**: Zero-downtime deployments

### Infrastructure as Code
- **Docker**: Container definitions for all services
- **Terraform**: Infrastructure provisioning
- **Ansible**: Configuration management
- **CI/CD**: Automated testing and deployment pipelines

## Future Architecture Considerations

### Planned Enhancements
1. **Distributed Agent Execution**: Run agents across multiple nodes
2. **Model Fine-tuning**: Domain-specific model training
3. **Advanced Caching**: Predictive caching for common queries
4. **Federated Learning**: Improve models without centralizing data
5. **Edge Computing**: Local processing for privacy-sensitive tasks

### Scalability Roadmap
1. **Micro-batching**: Process multiple tasks in parallel
2. **Agent Specialization**: Domain-specific agent variants
3. **Caching Strategies**: Multi-level intelligent caching
4. **Database Sharding**: Scale data storage horizontally
5. **CDN Integration**: Global content distribution

## Conclusion

The InsightWeaver architecture provides a robust, scalable foundation for multi-agent AI systems. The separation of concerns between frontend, backend, and AI engine allows for independent scaling and development. The hierarchical memory system ensures both real-time responsiveness and long-term learning capabilities, while the comprehensive monitoring and security measures provide enterprise-grade reliability and safety.

This architecture successfully addresses the key challenges of AI agent systems: coordination, memory management, real-time communication, and scalable deployment, making it suitable for both current needs and future growth.