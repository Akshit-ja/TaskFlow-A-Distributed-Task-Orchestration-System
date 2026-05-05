# Distributed Task Queue

A scalable distributed task queue system built with FastAPI, Celery, Redis, and PostgreSQL. This system provides reliable asynchronous task execution with monitoring, retry mechanisms, and horizontal scaling capabilities.

## Features

- **RESTful API** - Submit, monitor, and manage tasks via HTTP endpoints
- **Asynchronous Processing** - Background task execution with Celery workers
- **Reliable Message Broker** - Redis for task queuing and result storage
- **Persistent Storage** - PostgreSQL for task metadata and results
- **Horizontal Scaling** - Multiple worker processes and API instances
- **Retry Logic** - Configurable retry policies for failed tasks
- **Task Monitoring** - Real-time task status and queue statistics
- **Priority Queues** - Support for different task priorities
- **Scheduled Tasks** - Cron-like scheduling with Celery Beat
- **Health Checks** - Service health monitoring endpoints
- **Containerized** - Docker and Docker Compose support

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI API   │    │  Celery Worker  │    │  Celery Worker  │
│                 │    │                 │    │                 │
│  - Task Submit  │    │ - Task Execute  │    │ - Task Execute  │
│  - Task Status  │    │ - Result Store  │    │ - Result Store  │
│  - Monitoring   │    │                 │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴───────────┐
                    │      Redis Broker       │
                    │                         │
                    │  - Task Queues          │
                    │  - Result Backend       │
                    │  - Worker Coordination  │
                    └─────────────┬───────────┘
                                  │
                    ┌─────────────┴───────────┐
                    │    PostgreSQL DB        │
                    │                         │
                    │  - Task Metadata        │
                    │  - Execution History    │
                    │  - Queue Statistics     │
                    └─────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Using Docker Compose (Recommended)

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd distributed-task-queue
   cp .env.example .env
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Check service health:**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Access the services:**
   - API: http://localhost:8000
   - Demo Dashboard: http://localhost:8000/dashboard
   - API Documentation: http://localhost:8000/docs
   - Task Monitor (Flower): http://localhost:5555

### Local Development Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start external services:**
   ```bash
   docker-compose up -d postgres redis
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the services:**
   ```bash
   # Terminal 1: API Server
   uvicorn src.main:app --reload --port 8000

   # Terminal 2: Celery Worker
   celery -A src.worker.main worker --loglevel=info

   # Terminal 3: Celery Beat (for scheduled tasks)
   celery -A src.worker.main beat --loglevel=info

   # Terminal 4: Task Monitor (optional)
   celery -A src.worker.main flower
   ```

## API Usage

### Submit a Task

```bash
curl -X POST "http://localhost:8000/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "example_task",
    "payload": {"message": "Hello, World!"},
    "priority": "normal",
    "queue_name": "default"
  }'
```

### Get Task Status

```bash
curl "http://localhost:8000/api/v1/tasks/{task_id}"
```

### List Tasks

```bash
curl "http://localhost:8000/api/v1/tasks/?status=pending&limit=10"
```

### Get Queue Statistics

```bash
curl "http://localhost:8000/api/v1/monitoring/queues"
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_api/test_tasks.py -v

# Run specific test
pytest -k "test_create_task"
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

### Adding New Task Types

1. Create task handler in `src/worker/task_handlers.py`
2. Register task with Celery in `src/worker/main.py`
3. Add task schema in `src/schemas/task.py`
4. Update API endpoint if needed

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `API_PORT` - API server port (default: 8000)
- `WORKER_CONCURRENCY` - Number of worker processes
- `DEFAULT_TASK_TIMEOUT` - Task execution timeout
- `MAX_RETRY_ATTEMPTS` - Maximum retry attempts for failed tasks

## Monitoring

### Health Checks

- API Health: `GET /health`
- Database Health: `GET /health/db`
- Redis Health: `GET /health/redis`

### Metrics

The system provides metrics for monitoring:

- Task throughput and latency
- Queue depths and processing rates
- Worker utilization and status
- Error rates and retry statistics

Access metrics at: `GET /api/v1/monitoring/metrics`

### Task Monitoring

Use Celery Flower for real-time task monitoring:
- Web UI: http://localhost:5555
- Worker status, task history, and performance metrics

## Production Deployment

For production deployment:

1. Use environment-specific `.env` files
2. Set up proper logging and monitoring
3. Configure load balancing for API instances
4. Set up database backups and replication
5. Monitor resource usage and scale workers accordingly
6. Implement proper security measures (authentication, HTTPS)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.