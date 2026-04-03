# InsightWeaver Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying InsightWeaver in various environments, from local development to production.

## Prerequisites

### System Requirements
- **Docker**: 20.10+
- **Docker Compose**: 2.10+
- **RAM**: Minimum 8GB, Recommended 16GB+
- **Storage**: Minimum 20GB free space
- **CPU**: 4+ cores recommended for production

### External Dependencies
- **OpenAI API Key** (for GPT models)
- **Anthropic API Key** (for Claude models)
- **Google Search API Key** (for web search)
- **Domain name** (for production HTTPS)

## Quick Start (Development)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/insightweaver.git
cd insightweaver

# Copy environment files
cp .env.example .env
cp ai-engine/.env.example ai-engine/.env

# Edit environment variables with your API keys
nano .env
```

### 2. Configure Environment Variables

#### Main Environment (.env)
```env
# Application Configuration
APP_NAME=InsightWeaver
ENVIRONMENT=development

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_DB=insightweaver
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest

# AI Engine Configuration
AI_ENGINE_HOST=ai-engine
AI_ENGINE_PORT=8000

# API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_CX=your_google_search_cx
```

#### AI Engine Environment (ai-engine/.env)
```env
# AI Engine Configuration
ENVIRONMENT=development
DEBUG=true

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-4

# Search APIs
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_SEARCH_CX=your_google_search_cx

# Memory Configuration
REDIS_HOST=redis
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### 3. Start with Docker Compose
```bash
# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access Services
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080/api/v1
- **AI Engine**: http://localhost:8000
- **Backend Swagger**: http://localhost:8080/api/v1/swagger-ui.html
- **AI Engine Docs**: http://localhost:8000/docs

## Production Deployment

### Docker Compose (Production)

#### 1. Production Environment Variables
Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      target: production
    ports:
      - "80:80"
      - "443:443"
    environment:
      - NODE_ENV=production
      - VUE_APP_API_BASE_URL=/api/v1
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=production
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - RABBITMQ_HOST=rabbitmq
    depends_on:
      - postgres
      - redis
      - rabbitmq

  ai-engine:
    build:
      context: ./ai-engine
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - REDIS_HOST=redis
    depends_on:
      - redis

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=insightweaver
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      - RABBITMQ_DEFAULT_USER=${RABBITMQ_USERNAME}
      - RABBITMQ_DEFAULT_PASS=${RABBITMQ_PASSWORD}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  rabbitmq_data:
```

#### 2. Production Environment File
Create `.env.production`:

```env
# Security
POSTGRES_PASSWORD=your_secure_postgres_password
REDIS_PASSWORD=your_secure_redis_password
RABBITMQ_USERNAME=insightweaver
RABBITMQ_PASSWORD=your_secure_rabbitmq_password
JWT_SECRET_KEY=your_very_long_jwt_secret_key_here

# External APIs
OPENAI_API_KEY=your_production_openai_key
ANTHROPIC_API_KEY=your_production_anthropic_key
GOOGLE_SEARCH_API_KEY=your_production_google_key
GOOGLE_SEARCH_CX=your_production_google_cx
```

#### 3. Deploy Production
```bash
# Start production services
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Scale services as needed
docker-compose -f docker-compose.prod.yml up -d --scale ai-engine=3
```

### Kubernetes Deployment

#### 1. Kubernetes Manifests
Create `k8s/` directory with manifests:

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: insightweaver
```

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: insightweaver-config
  namespace: insightweaver
data:
  APP_NAME: "InsightWeaver"
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
```

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: insightweaver-secrets
  namespace: insightweaver
type: Opaque
stringData:
  POSTGRES_PASSWORD: "your_postgres_password"
  REDIS_PASSWORD: "your_redis_password"
  OPENAI_API_KEY: "your_openai_key"
  ANTHROPIC_API_KEY: "your_anthropic_key"
```

```yaml
# k8s/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: insightweaver
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: insightweaver/frontend:latest
        ports:
        - containerPort: 80
        envFrom:
        - configMapRef:
            name: insightweaver-config
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

#### 2. Deploy to Kubernetes
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy applications
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/ai-engine-deployment.yaml

# Expose services
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/ingress.yaml
```

## Environment-Specific Configurations

### Development
```bash
# docker-compose.dev.yml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      target: development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development

  backend:
    build:
      context: ./backend
    volumes:
      - ./backend:/app
    ports:
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=development

  ai-engine:
    build:
      context: ./ai-engine
    volumes:
      - ./ai-engine:/app
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
```

### Staging
```bash
# docker-compose.staging.yml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      target: production
    environment:
      - NODE_ENV=production

  backend:
    build:
      context: ./backend
    environment:
      - SPRING_PROFILES_ACTIVE=staging

  ai-engine:
    build:
      context: ./ai-engine
    environment:
      - ENVIRONMENT=staging
      - DEBUG=false
```

## Monitoring and Logging

### 1. Health Checks
```bash
# Check service health
curl http://localhost:8080/api/v1/actuator/health
curl http://localhost:8000/health

# Monitor logs
docker-compose logs -f frontend
docker-compose logs -f backend
docker-compose logs -f ai-engine
```

### 2. Performance Monitoring
```bash
# Resource usage
docker stats

# Application metrics (if Prometheus is configured)
curl http://localhost:8080/api/v1/actuator/prometheus
```

### 3. Log Aggregation
```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    volumes:
      - ./logs:/usr/share/filebeat/logs
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml
```

## Backup and Recovery

### 1. Database Backup
```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U postgres insightweaver > backup_$(date +%Y%m%d).sql

# Backup Redis
docker-compose exec redis redis-cli SAVE
cp $(docker-compose exec redis redis-cli CONFIG GET dir | head -1)/dump.rdb ./backup_redis_$(date +%Y%m%d).rdb

# Backup ChromaDB
cp -r ./ai-engine/chroma_db ./backup_chroma_$(date +%Y%m%d)
```

### 2. Restore from Backup
```bash
# Restore PostgreSQL
cat backup_20240101.sql | docker-compose exec -T postgres psql -U postgres insightweaver

# Restore Redis
cp backup_redis_20240101.rdb ./redis_data/dump.rdb
docker-compose restart redis

# Restore ChromaDB
cp -r ./backup_chroma_20240101/* ./ai-engine/chroma_db/
docker-compose restart ai-engine
```

## Security Hardening

### 1. Network Security
```yaml
# docker-compose.security.yml
version: '3.8'

services:
  frontend:
    networks:
      - frontend
      - backend

  backend:
    networks:
      - backend
      - data

  ai-engine:
    networks:
      - backend
      - data

  postgres:
    networks:
      - data

  redis:
    networks:
      - data

networks:
  frontend:
    internal: false
  backend:
    internal: true
  data:
    internal: true
```

### 2. SSL/TLS Configuration
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name insightweaver.example.com;

    ssl_certificate /etc/ssl/certs/insightweaver.crt;
    ssl_certificate_key /etc/ssl/private/insightweaver.key;

    location / {
        proxy_pass http://frontend:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://backend:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start
```bash
# Check logs
docker-compose logs [service_name]

# Check resource usage
docker system df
docker system prune

# Check port conflicts
netstat -tulpn | grep :8080
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker-compose exec backend nc -zv postgres 5432

# Check database logs
docker-compose logs postgres

# Reset database (development only)
docker-compose down -v
docker-compose up -d
```

#### 3. AI Engine Performance Issues
```bash
# Check memory usage
docker stats ai-engine

# Check API key validity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Monitor queue length
docker-compose exec rabbitmq rabbitmqctl list_queues
```

#### 4. Frontend Build Issues
```bash
# Clear npm cache
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Check Vue CLI version
vue --version
```

### Performance Tuning

#### 1. JVM Tuning (Backend)
```bash
# Add to backend Dockerfile
ENV JAVA_OPTS="-Xms512m -Xmx2048m -XX:+UseG1GC -XX:MaxGCPauseMillis=200"
```

#### 2. Python Tuning (AI Engine)
```python
# Add to ai-engine requirements
uvloop==0.17.0  # Faster event loop
orjson==3.8.5   # Faster JSON processing
```

#### 3. Database Tuning
```sql
-- Add to postgres initialization
ALTER SYSTEM SET shared_buffers = '512MB';
ALTER SYSTEM SET effective_cache_size = '1536MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
SELECT pg_reload_conf();
```

## CI/CD Pipeline

### GitHub Actions Example
```yaml
# .github/workflows/deploy.yml
name: Deploy InsightWeaver

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker
        uses: docker/setup-qemu-action@v2
      
      - name: Build and test
        run: |
          docker-compose -f docker-compose.test.yml up --build --exit-code-from tests

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.prod.yml up -d --build
```

## Conclusion

This deployment guide covers the essential steps for running InsightWeaver in various environments. For production deployments, ensure you:

1. Use strong, unique passwords for all services
2. Enable HTTPS with valid certificates
3. Implement proper monitoring and alerting
4. Set up regular backup procedures
5. Follow security best practices
6. Test thoroughly in staging before production deployment

For additional support, refer to the individual service documentation or contact the development team.