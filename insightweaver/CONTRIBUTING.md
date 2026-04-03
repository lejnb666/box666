# Contributing to InsightWeaver

Thank you for your interest in contributing to InsightWeaver! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

### Prerequisites

- Node.js 18+ (for frontend development)
- Java 17+ (for backend development)
- Python 3.11+ (for AI engine development)
- Docker and Docker Compose
- Git

### Initial Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/insightweaver.git
   cd insightweaver
   ```
3. **Set up upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-owner/insightweaver.git
   ```
4. **Install dependencies**:
   ```bash
   # Frontend
   cd frontend && npm install
   
   # Backend
   cd ../backend && ./mvnw clean install
   
   # AI Engine
   cd ../ai-engine && pip install -r requirements.txt
   ```

## Development Setup

### Local Development Environment

1. **Start development services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **Run individual services**:
   ```bash
   # Frontend (hot reload)
   cd frontend && npm run dev
   
   # Backend
   cd backend && ./mvnw spring-boot:run
   
   # AI Engine
   cd ai-engine && python src/main.py
   ```

### Environment Configuration

Copy the example environment files and customize them:

```bash
cp .env.example .env
cp ai-engine/.env.example ai-engine/.env
```

## Project Structure

```
insightweaver/
├── backend/                 # Spring Boot microservice
│   ├── src/main/java/      # Java source code
│   ├── src/main/resources/ # Configuration files
│   └── pom.xml            # Maven dependencies
├── ai-engine/             # Python FastAPI service
│   ├── src/               # Core AI logic
│   ├── agents/            # Multi-agent implementations
│   ├── tools/             # External tool integrations
│   └── requirements.txt   # Python dependencies
├── frontend/              # Vue 3 application
│   ├── src/               # Vue source code
│   ├── components/        # Reusable components
│   └── views/             # Page components
├── infrastructure/        # Deployment configurations
│   ├── docker/            # Docker configurations
│   └── scripts/           # Deployment scripts
├── tests/                 # Test suites
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
└── docs/                  # Documentation
    ├── api/               # API documentation
    └── architecture/      # System architecture docs
```

## Coding Standards

### General Guidelines

- **Write clear, maintainable code** with meaningful variable and function names
- **Add comments** for complex logic and algorithms
- **Follow the existing code style** in each language
- **Keep functions small and focused** on a single responsibility
- **Use TypeScript** for frontend development
- **Write comprehensive tests** for new features

### Frontend (Vue 3 + TypeScript)

#### Code Style
- Use **Composition API** with `<script setup>` syntax
- Follow **Vue 3 Style Guide** best practices
- Use **TypeScript strict mode**
- Implement **proper typing** for all components and stores

#### Component Guidelines
```vue
<!-- Good component structure -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import type { PropType } from 'vue'

// Props with TypeScript
const props = defineProps({
  title: {
    type: String as PropType<string>,
    required: true
  },
  items: {
    type: Array as PropType<string[]>,
    default: () => []
  }
})

// Reactive state
const count = ref(0)

// Computed properties
const doubledCount = computed(() => count.value * 2)

// Methods
const increment = () => {
  count.value++
}
</script>

<template>
  <div class="component">
    <h3>{{ title }}</h3>
    <p>Count: {{ count }} (doubled: {{ doubledCount }})</p>
    <button @click="increment">Increment</button>
  </div>
</template>

<style scoped>
.component {
  padding: 1rem;
}
</style>
```

#### Store Guidelines (Pinia)
```typescript
// stores/example.ts
import { defineStore } from 'pinia'

interface State {
  count: number
  items: string[]
}

export const useExampleStore = defineStore('example', {
  state: (): State => ({
    count: 0,
    items: []
  }),
  
  getters: {
    doubledCount: (state) => state.count * 2,
    itemCount: (state) => state.items.length
  },
  
  actions: {
    increment() {
      this.count++
    },
    
    addItem(item: string) {
      this.items.push(item)
    },
    
    async fetchItems() {
      // Async actions for API calls
      try {
        const response = await fetch('/api/items')
        this.items = await response.json()
      } catch (error) {
        console.error('Failed to fetch items:', error)
      }
    }
  }
})
```

### Backend (Java Spring Boot)

#### Code Style
- Follow **Google Java Style Guide**
- Use **Lombok** for reducing boilerplate code
- Implement **proper exception handling**
- Use **Spring Boot best practices**

#### Service Guidelines
```java
@Service
@RequiredArgsConstructor
@Slf4j
public class ResearchService {

    private final ResearchRepository repository;
    private final SseService sseService;
    
    @Transactional
    public ResearchTask createTask(CreateTaskRequest request, String userId) {
        log.info("Creating research task for user: {}", userId);
        
        // Validation
        validateRequest(request);
        
        // Business logic
        ResearchTask task = ResearchTask.builder()
            .title(request.getTitle())
            .description(request.getDescription())
            .userId(userId)
            .status(TaskStatus.PENDING)
            .build();
            
        ResearchTask savedTask = repository.save(task);
        
        // Send real-time update
        sseService.sendTaskCreation(savedTask, userId);
        
        return savedTask;
    }
    
    private void validateRequest(CreateTaskRequest request) {
        if (request.getTitle() == null || request.getTitle().trim().isEmpty()) {
            throw new ValidationException("Title is required");
        }
        
        if (request.getTitle().length() > 500) {
            throw new ValidationException("Title must not exceed 500 characters");
        }
    }
}
```

#### Controller Guidelines
```java
@RestController
@RequestMapping("/api/v1/research")
@RequiredArgsConstructor
@Slf4j
public class ResearchController {

    private final ResearchService service;
    
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ResponseEntity<ResearchResponse> createTask(
            @Valid @RequestBody CreateTaskRequest request,
            Authentication authentication) {
        
        log.info("Received task creation request: {}", request.getTitle());
        
        try {
            String userId = authentication.getName();
            ResearchResponse response = service.createTask(request, userId);
            
            return ResponseEntity.ok(response);
            
        } catch (ValidationException e) {
            log.warn("Validation error: {}", e.getMessage());
            return ResponseEntity.badRequest().build();
        } catch (Exception e) {
            log.error("Unexpected error creating task", e);
            return ResponseEntity.internalServerError().build();
        }
    }
}
```

### AI Engine (Python FastAPI)

#### Code Style
- Follow **PEP 8** guidelines
- Use **type hints** throughout
- Implement **async/await** for I/O operations
- Use **dataclasses** for data structures

#### Agent Guidelines
```python
class BaseAgent:
    """Abstract base class for all InsightWeaver agents."""
    
    def __init__(self, llm: BaseLanguageModel, redis_service: RedisService):
        self.llm = llm
        self.redis_service = redis_service
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def execute(self, context: AgentContext) -> AgentResponse:
        """Execute the agent's main logic."""
        try:
            self.logger.info(f"Starting execution for task {context.task_id}")
            
            # Core agent logic here
            result = await self._execute_core(context)
            
            # Store results in memory
            await self._store_results(context, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {str(e)}")
            return AgentResponse.error(str(e))
    
    @abstractmethod
    async def _execute_core(self, context: AgentContext) -> AgentResponse:
        """Core execution logic to be implemented by subclasses."""
        pass
```

#### Service Guidelines
```python
class RedisService:
    """Service for Redis operations."""
    
    async def set_value(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis with optional TTL."""
        try:
            # Serialize complex objects
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set value for key {key}: {str(e)}")
            return False
```

## Testing

### Frontend Testing

#### Unit Tests
```bash
cd frontend
npm run test:unit
```

#### Component Tests
```typescript
// tests/components/TaskCard.spec.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@testing-library/vue'
import TaskCard from '@/components/TaskCard.vue'

describe('TaskCard', () => {
  it('displays task title correctly', () => {
    const task = {
      id: '123',
      title: 'Test Research Task',
      status: 'COMPLETED'
    }
    
    const { getByText } = mount(TaskCard, {
      props: { task }
    })
    
    expect(getByText('Test Research Task')).toBeTruthy()
  })
})
```

### Backend Testing

#### Unit Tests
```bash
cd backend
./mvnw test
```

#### Integration Tests
```java
@SpringBootTest
@AutoConfigureTestDatabase
class ResearchServiceIntegrationTest {

    @Autowired
    private ResearchService service;
    
    @Test
    void shouldCreateTaskSuccessfully() {
        // Given
        CreateTaskRequest request = CreateTaskRequest.builder()
            .title("Test Task")
            .description("Test Description")
            .build();
        
        // When
        ResearchTask task = service.createTask(request, "test-user");
        
        // Then
        assertThat(task).isNotNull();
        assertThat(task.getTitle()).isEqualTo("Test Task");
        assertThat(task.getStatus()).isEqualTo(TaskStatus.PENDING);
    }
}
```

### AI Engine Testing

#### Unit Tests
```bash
cd ai-engine
pytest tests/unit/ -v
```

#### Integration Tests
```python
# tests/integration/test_agents.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_planning_agent_execution():
    # Arrange
    mock_llm = Mock()
    mock_redis = AsyncMock()
    agent = PlanningAgent(llm=mock_llm, redis_service=mock_redis)
    
    context = AgentContext(
        task_id="test-123",
        user_id="user-456",
        research_topic="Test research topic"
    )
    
    # Act
    result = await agent.execute(context)
    
    # Assert
    assert result.success is True
    assert "planning" in result.data
    assert len(result.data["planning"]["sub_tasks"]) > 0
```

## Pull Request Process

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
git push origin feature/your-feature-name
```

### 2. Make Changes
- Follow the coding standards above
- Add or update tests
- Update documentation if needed
- Ensure all tests pass

### 3. Commit Messages
Use conventional commits format:
```
feat: add new research agent
fix: resolve SSE connection timeout
docs: update deployment guide
style: format code according to standards
refactor: improve agent workflow logic
test: add unit tests for planning agent
```

### 4. Submit Pull Request
- Fill out the PR template
- Link related issues
- Add screenshots for UI changes
- Request review from maintainers

### 5. Code Review
- Address feedback and make changes
- Ensure CI/CD pipeline passes
- Update documentation if requested

## Release Process

### Versioning
We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] Release notes prepared
- [ ] Docker images built and tagged
- [ ] Deployment tested in staging

## Community

### Getting Help
- **Documentation**: Check the README and docs folder
- **Issues**: Search existing issues or create new ones
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our community chat (link in README)

### Reporting Bugs
1. **Search existing issues** to avoid duplicates
2. **Create a minimal reproduction** if possible
3. **Include environment details** (OS, versions, etc.)
4. **Provide clear steps** to reproduce the issue

### Feature Requests
1. **Check existing requests** in issues or discussions
2. **Provide detailed use cases** and benefits
3. **Consider implementation complexity**
4. **Be open to discussion** about the best approach

## License

By contributing to InsightWeaver, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

We value all contributions and will recognize significant contributions in:
- Project documentation
- Release notes
- Community showcases
- Contributor hall of fame

Thank you for contributing to InsightWeaver! 🚀