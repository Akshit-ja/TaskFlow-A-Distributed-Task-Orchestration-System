# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Architecture

This is a distributed task queue system with a clear separation of concerns:

- **`src/api/`** - REST API endpoints and HTTP handlers for task submission, monitoring, and management
- **`src/core/`** - Core business logic, task orchestration, queue management, and scheduling algorithms  
- **`src/models/`** - Data models for tasks, workers, queues, and system entities
- **`src/schemas/`** - Data validation schemas, API contracts, and serialization formats
- **`src/worker/`** - Worker processes that consume and execute tasks from queues

### System Components

The architecture follows a producer-consumer pattern:
1. **API Layer** receives task requests and provides status endpoints
2. **Core Engine** manages task queuing, routing, and worker coordination
3. **Worker Nodes** pull tasks from queues and execute them
4. **Models & Schemas** ensure data consistency across the system

## Development Setup

This is a Python-based distributed task queue using FastAPI, Celery, Redis, and PostgreSQL.

### Quick Start with Docker (Recommended)
```bash
# Start all services (PostgreSQL, Redis, API, Worker, Scheduler)
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs api
docker-compose logs worker

# Stop all services
docker-compose down
```

### Local Development Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start external services only
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head
```

### Running Services Locally
```bash
# Terminal 1: FastAPI Server
uvicorn src.main:app --reload --port 8000
# or
python -m src.main

# Terminal 2: Celery Worker
celery -A src.worker.main worker --loglevel=info --concurrency=4

# Terminal 3: Celery Beat Scheduler (for periodic tasks)
celery -A src.worker.main beat --loglevel=info

# Terminal 4: Celery Flower (task monitoring)
celery -A src.worker.main flower --port=5555
```

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api/test_tasks.py -v

# Run specific test by name
pytest -k "test_create_task"

# Run tests with verbose output
pytest -v -s
```

### Code Quality
```bash
# Format code with black
black src/ tests/

# Sort imports with isort
isort src/ tests/

# Lint code with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Show migration history
alembic history

# Show current revision
alembic current
```

### API Testing
```bash
# Test API endpoints (ensure server is running)
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{"name": "example_task", "payload": {"message": "Hello World"}}'

# Check task status
curl "http://localhost:8000/api/v1/tasks/{task_id}"

# Get queue statistics
curl "http://localhost:8000/api/v1/monitoring/queues"

# Health checks
curl "http://localhost:8000/health"
curl "http://localhost:8000/health/db"
curl "http://localhost:8000/health/redis"
```

## Key Development Patterns

### Task Management
- Tasks are stored in PostgreSQL with metadata and status tracking
- Celery handles task queuing and execution via Redis broker
- Task schemas defined in `src/schemas/task.py` using Pydantic
- Task handlers implemented in `src/worker/task_handlers.py`

### Worker Architecture  
- Celery workers are stateless and horizontally scalable
- Workers register with database for monitoring in `workers` table
- Graceful shutdown implemented with signal handlers
- Health checks via worker heartbeat mechanism

### API Design
- RESTful endpoints in `src/api/routers/` using FastAPI
- Database sessions managed via dependency injection
- Custom exception handling with structured error responses
- Request/response validation with Pydantic schemas

### Queue Management
- Redis stores task queues and acts as Celery broker
- PostgreSQL stores task metadata, results, and execution history
- Supports priority queues, retry policies, and scheduled execution
- Queue statistics automatically maintained via database triggers

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies (databases, message brokers)
- Focus on business logic in `core/` and data validation in `schemas/`

### Integration Tests  
- Test API endpoints with real database connections
- Worker task execution end-to-end
- Queue persistence and retrieval operations

### Load Testing
- Simulate high task submission rates
- Test worker scaling under load
- Validate queue performance with large backlogs

## Configuration Management

Distributed task queues typically require configuration for:
- Database/storage connections (Redis, PostgreSQL, etc.)
- Message broker settings (RabbitMQ, Apache Kafka, etc.)
- Worker concurrency and resource limits
- Task timeout and retry policies
- Monitoring and logging settings

Environment-specific configs should be in separate files or environment variables.

## Monitoring and Observability

Key metrics to track:
- Task throughput (tasks/second)
- Queue depth and processing latency
- Worker utilization and error rates
- System resource usage (CPU, memory, network)

Consider implementing structured logging and distributed tracing for debugging across services.