# Developer Onboarding Guide

Welcome to the Alloy team! This guide will help you get started with local development and understand the codebase architecture.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Database Setup](#database-setup)
3. [Running the Application](#running-the-application)
4. [Code Architecture](#code-architecture)
5. [Development Workflows](#development-workflows)
6. [Testing](#testing)
7. [Debugging](#debugging)
8. [Deployment](#deployment)
9. [Contribution Process](#contribution-process)

## Local Development Setup

### Prerequisites

- **Python**: 3.11 or higher
- **PostgreSQL**: 14 or higher
- **Redis**: 6 or higher (for caching)
- **Node.js**: 18 or higher (for frontend development)
- **Git**: Latest version

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/alloy.git
cd alloy
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://alloy:password@localhost:5432/alloy_dev
READ_REPLICA_ENABLED=false
READ_REPLICA_URLS=

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=300

# Application
APP_NAME=Alloy
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# OpenTelemetry (Optional)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Performance Monitoring
ENABLE_PERFORMANCE_MONITORING=true
```

### 5. Install Pre-commit Hooks

```bash
pre-commit install
```

## Database Setup

### 1. Start PostgreSQL

**Using Docker (Recommended)**:
```bash
docker run --name alloy-postgres \
  -e POSTGRES_USER=alloy \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=alloy_dev \
  -p 5432:5432 \
  -d postgres:14
```

**Local Installation**:
Follow the PostgreSQL installation guide for your OS.

### 2. Start Redis

**Using Docker**:
```bash
docker run --name alloy-redis \
  -p 6379:6379 \
  -d redis:6-alpine
```

### 3. Run Database Migrations

```bash
# Create migration (if needed)
alembic revision --autogenerate -m "Description"

# Apply all migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### 4. Seed Database (Optional)

```bash
# Seed with test data
python scripts/seed_database.py
```

## Running the Application

### Development Server

```bash
# Run API server
uvicorn app.main:app --reload --host 0.0.0.0.0 --port 8000

# Or using the Makefile
make dev
```

The API will be available at `http://localhost:8000`

### Accessing Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Health Checks

```bash
# Overall health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Redis health
curl http://localhost:8000/health/redis

# Replica health (if enabled)
curl http://localhost:8000/health/database/replicas
```

## Code Architecture

### Directory Structure

```
alloy/
├── app/
│   ├── api/
│   │   ├── routes/          # API route handlers
│   │   └── dependencies/     # FastAPI dependencies
│   ├── config/              # Configuration settings
│   ├── core/
│   │   ├── exceptions.py     # Domain exception hierarchy
│   │   ├── logging.py        # Structured logging
│   │   ├── metrics.py        # Prometheus metrics
│   │   ├── performance.py    # Performance monitoring
│   │   ├── tracing.py       # Distributed tracing
│   │   ├── password.py       # Password validation
│   │   └── transactions.py  # Transaction decorators
│   ├── db/
│   │   ├── database.py       # Database connection and sessions
│   │   └── models.py       # SQLAlchemy models
│   ├── middleware/           # Custom middleware
│   ├── models/              # Domain models
│   ├── repositories/         # Data access layer
│   ├── schemas/             # Pydantic schemas (request/response)
│   ├── security/            # Security utilities (JWT, password hashing)
│   └── services/            # Business logic layer
├── alembic/              # Database migrations
├── scripts/               # Utility scripts
├── tests/                 # Test files
└── docs/                  # Documentation
```

### Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│                 API Routes Layer                 │
│         (FastAPI, request/response)              │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│              Service Layer                        │
│         (Business logic, orchestration)            │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           Repository Layer                         │
│       (Data access, queries, CRUD)                 │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│           Database Layer                          │
│    (PostgreSQL, read replicas, caching)               │
└────────────────────────────────────────────────────┘
```

### Key Patterns

#### Repository Pattern

All data access goes through repositories:

```python
from app.repositories.program_repository import ProgramRepository
from app.db.database import get_db

class ProgramService:
    def __init__(self, program_repo: ProgramRepository):
        self._program_repo = program_repo
    
    async def get_program(self, program_id: int):
        return await self._program_repo.get(program_id)
```

#### Domain Exception Pattern

Use domain exceptions instead of HTTPException:

```python
from app.core.exceptions import NotFoundError

async def get_program(program_id: int):
    program = await program_repo.get(program_id)
    if not program:
        raise NotFoundError("Program", details={"id": program_id})
    return program
```

#### Transaction Decorator

Use the `@transactional` decorator for write operations:

```python
from app.core.transactions import transactional

@transactional()
async def create_program(data: ProgramCreate):
    program = Program(**data)
    program_repo.create(program)
    return program
```

## Development Workflows

### Adding a New Feature

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write the code** following the architecture patterns

3. **Write tests** (see [Testing](#testing))

4. **Run tests and linters**:
   ```bash
   make test
   make lint
   make typecheck
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

6. **Push and create a PR**:
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Fixing a Bug

1. **Create a bugfix branch**:
   ```bash
   git checkout -b fix/bug-description
   ```

2. **Reproduce the bug** in your local environment

3. **Write a test** that fails with the bug

4. **Fix the bug**

5. **Verify the fix** by running the test

6. **Commit and PR** (same as feature workflow)

### Making API Changes

1. **Update the schema** in `app/schemas/`
2. **Update the repository** if data access changes
3. **Update the service** if business logic changes
4. **Update the route** in `app/api/routes/`
5. **Write tests** for the new endpoint
6. **Update documentation** in code comments

### Database Changes

1. **Update the model** in `app/models/`
2. **Create a migration**:
   ```bash
   alembic revision --autogenerate -m "Description of change"
   ```
3. **Review the migration** in `alembic/versions/`
4. **Test the migration** up and down:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   ```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_program_service.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v
```

### Test Structure

```python
import pytest
from app.services.program import ProgramService
from app.repositories.program_repository import ProgramRepository

@pytest.fixture
def program_service(mock_program_repo):
    return ProgramService(mock_program_repo)

class TestProgramService:
    async def test_create_program(self, program_service):
        result = await program_service.create_program({...})
        assert result.id is not None
    
    async def test_get_program_not_found(self, program_service):
        with pytest.raises(NotFoundError):
            await program_service.get_program(99999)
```

### Writing Good Tests

1. **Test one thing per test**
2. **Use descriptive test names**
3. **Use fixtures for setup**
4. **Mock external dependencies**
5. **Test both success and error cases**
6. **Use assertions that verify behavior, not implementation**

## Debugging

### Using VS Code

1. **Install Python extension**
2. **Configure launch settings**:
   ```json
   {
     "name": "Python: FastAPI",
     "type": "debugpy",
     "request": "launch",
     "program": "${workspaceFolder}/.venv/bin/python",
     "args": ["-m", "uvicorn", "app.main:app", "--reload"],
     "console": "integratedTerminal",
     "justMyCode": true
   }
   ```

3. **Set breakpoints** and start debugging

### Using Logs

Logs are structured JSON output:

```bash
# View logs
tail -f logs/app.log | jq

# Filter by request_id
tail -f logs/app.log | jq 'select(.request_id == "uuid-here")'

# Filter by level
tail -f logs/app.log | jq 'select(.level == "ERROR")'
```

### Using the Debugger

```python
import pdb; pdb.set_trace()

# Or use ipdb
import ipdb; ipdb.set_trace()
```

## Deployment

### Local Build

```bash
# Build Docker image
docker build -t alloy:latest .

# Run container
docker run -p 8000:8000 --env-file .env alloy:latest
```

### Production Checklist

- [ ] All tests pass
- [ ] No linting errors
- [ ] No type errors
- [ ] Database migrations tested
- [ ] Environment variables configured
- [ ] Security headers verified
- [ ] Rate limiting configured
- [ ] Caching enabled
- [ ] Monitoring configured
- [ ] Logging configured
- [ ] Documentation updated

## Contribution Process

### Code Review Checklist

- [ ] Code follows naming conventions
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] No new linting errors
- [ ] No new type errors
- [ ] Sensitive data is not logged
- [ ] Database transactions are properly handled
- [ ] Error handling is complete
- [ ] Performance impact is considered

### Commit Message Format

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(program): add program cloning feature

fix(auth): resolve token refresh issue on expiration

docs(readme): update onboarding guide

test(program): add tests for program deletion
```

### Getting Help

- **Slack**: #alloy-dev channel
- **Email**: dev-team@alloy.io
- **Documentation**: /docs folder
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

## Quick Reference

### Common Commands

```bash
# Development
make dev              # Start dev server
make test             # Run tests
make lint             # Run linting
make typecheck        # Run type checking
make format           # Format code

# Database
make db-migrate       # Run migrations
make db-rollback       # Rollback last migration
make db-seed          # Seed database

# Docker
make docker-up         # Start Docker services
make docker-down       # Stop Docker services
make docker-logs       # View Docker logs
```

### Useful URLs

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Admin Dashboard**: http://localhost:8000/admin

---

Welcome aboard! If you have questions, don't hesitate to ask in #alloy-dev or reach out to a team member.
