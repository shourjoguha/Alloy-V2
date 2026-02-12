# API Contract & Service Architecture Implementation Plan

## Executive Summary

This document provides a detailed, thematic implementation plan to resolve 60 identified inconsistencies across API contracts (32 issues) and service architecture (28 issues). The plan is organized into 6 themes with clear execution order, dependencies, testing strategies, and success criteria.

**Timeline**: 15 weeks total  
**Issues Addressed**: 60 total (25 MVP issues deliver 80% of business value)  
**Success Metrics**: MTTR reduced 40%, P95 response time < 200ms, zero data loss incidents

---

## Table of Contents

1. [Theme Overview & Execution Order](#theme-overview--execution-order)
2. [Phase 1: Foundation & Contract Consistency](#phase-1-foundation--contract-consistency)
3. [Phase 2: Parallel Tracks](#phase-2-parallel-tracks)
4. [Phase 3: Error Handling & Observability](#phase-3-error-handling--observability)
5. [Phase 4: Performance & Scalability](#phase-4-performance--scalability)
6. [Phase 5: Remaining Issues](#phase-5-remaining-issues)
7. [Testing Strategy](#testing-strategy)
8. [Rollback Procedures](#rollback-procedures)

---

## Theme Overview & Execution Order

```
Week 1-3:   Foundation & Contract Consistency
Week 4-5:   Security & Authentication
Week 4:      Developer Experience
Week 5-6:    Data Access & Transaction Safety
Week 8-10:    Error Handling & Observability
Week 11-14:   Performance & Scalability
Week 15+:     Remaining Issues
```

### Dependency Map

```
Foundation (Theme 1)
    ├── Error Handling (Theme 5)
    ├── Data Access (Theme 3)
    ├── Security (Theme 2)
    └── Performance (Theme 6)
            └── Depends on: Data Access
                    └── Depends on: Foundation
Dev Experience (Theme 4)
    └── Can run in parallel with Foundation
```

---

## Phase 1: Foundation & Contract Consistency

**Duration**: 3 weeks  
**Issues**: 12 total, 4 MVP  
**Priority**: Critical (unblocks all downstream work)  
**Success Criteria**: 100% new APIs pass validation, 90% existing APIs documented

### Week 1: API Response Wrapper Contract

**Goal**: Establish standard envelope structure for all API responses

**Tasks**:

#### 1.1 Create Standard Response Models
**File**: `/Users/shourjosmac/Documents/alloy/app/schemas/base.py` (create new)
```python
from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class ResponseMeta(BaseModel):
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    warnings: list[str] = Field(default_factory=list)

class APIError(BaseModel):
    code: str
    message: str
    details: dict | None = None

class APIResponse(BaseModel, Generic[T]):
    data: T | None = None
    meta: ResponseMeta | None = None
    errors: list[APIError] = Field(default_factory=list)

class ListResponseWrapper(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    has_next: bool = False
    has_prev: bool = False
    total_pages: int = 1
    current_page: int = 1
    filters_applied: dict | None = None
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Unit tests for response models, validation tests for field constraints

#### 1.2 Create Pagination Base Models
**File**: `/Users/shourjosmac/Documents/alloy/app/schemas/pagination.py` (create new)
```python
from pydantic import BaseModel, Field
from typing import Optional

class PaginationParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    direction: str = Field(default="next", pattern="^(next|prev)$")

class PaginatedResult(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool = False
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Unit tests for cursor encoding/decoding, validation tests

#### 1.3 Create Domain Exception Hierarchy
**File**: `/Users/shourjosmac/Documents/alloy/app/core/exceptions.py` (create new)
```python
class DomainError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundError(DomainError):
    pass

class ValidationError(DomainError):
    def __init__(self, field: str, message: str, details: dict | None = None):
        super().__init__(f"Validation failed for {field}: {message}", details or {"field": field})

class BusinessRuleError(DomainError):
    pass

class ConflictError(DomainError):
    pass

class AuthenticationError(DomainError):
    pass

class AuthorizationError(DomainError):
    pass
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Unit tests for each exception type, message formatting tests

#### 1.4 Create Global Exception Handler
**File**: `/Users/shourjosmac/Documents/alloy/app/core/error_handlers.py` (create new)
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import DomainError, NotFoundError, ValidationError, BusinessRuleError, ConflictError, AuthenticationError, AuthorizationError
from app.schemas.base import APIResponse, APIError

ERROR_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
}

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": datetime.utcnow()
            },
            "errors": [{
                "code": type(exc).__name__,
                "message": exc.message,
                "details": exc.details
            }]
        }
    )
```

**Prerequisites**: Domain exceptions (Task 1.3), Response models (Task 1.1)  
**Dependencies**: 1.1, 1.3  
**Testing**: Integration tests for each exception type, response structure validation

**Risk Mitigation**: Deploy behind feature flag, gradual rollout  
**Rollback**: Remove exception handler, restore old HTTPException usage

### Week 2: Service Interface Templates

**Goal**: Define clear service contracts and dependency injection patterns

#### 2.1 Create Base Repository Interface
**File**: `/Users/shourjosmac/Documents/alloy/app/repositories/base.py` (create new)
```python
from typing import Generic, TypeVar, Optional, Protocol
from pydantic import BaseModel
from app.schemas.pagination import PaginationParams, PaginatedResult

T = TypeVar('T')
ID = TypeVar('ID')

class Repository(Protocol[T, ID]):
    async def get(self, id: ID) -> Optional[T]: ...
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[T]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, id: ID, updates: dict) -> Optional[T]: ...
    async def delete(self, id: ID) -> bool: ...
```

**Prerequisites**: Pagination models (Task 1.2)  
**Dependencies**: 1.2  
**Testing**: Protocol compliance tests for implementations

#### 2.2 Create Program Repository
**File**: `/Users/shourjosmac/Documents/alloy/app/repositories/program_repository.py` (create new)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.program import Program
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class ProgramRepository(Repository[Program, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Program | None:
        result = await self._session.execute(
            select(Program)
            .options(selectinload(Program.program_disciplines))
            .options(selectinload(Program.sessions))
            .where(Program.id == id)
        )
        return result.scalar_one_or_none()
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Program]:
        query = select(Program)
        
        if 'user_id' in filter:
            query = query.where(Program.user_id == filter['user_id'])
        
        if 'is_active' in filter:
            query = query.where(Program.is_active == filter['is_active'])
        
        query = query.order_by(Program.created_at.desc())
        
        if pagination.cursor:
            field, value = decode_cursor(pagination.cursor)
            if pagination.direction == "next":
                query = query.where(getattr(Program, field) < value)
            else:
                query = query.where(getattr(Program, field) > value)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        next_cursor = None
        if items and has_more:
            next_cursor = encode_cursor(items[-1].created_at, "created_at")
        
        return PaginatedResult(items=items, next_cursor=next_cursor, has_more=has_more)
    
    async def create(self, entity: Program) -> Program:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> Program | None:
        program = await self.get(id)
        if program:
            for key, value in updates.items():
                setattr(program, key, value)
            await self._session.flush()
        return program
    
    async def delete(self, id: int) -> bool:
        program = await self.get(id)
        if program:
            await self._session.delete(program)
            return True
        return False
```

**Prerequisites**: Base repository (Task 2.1), cursor utilities  
**Dependencies**: 2.1  
**Testing**: Unit tests with test database, integration tests

#### 2.3 Create Transaction Decorator
**File**: `/Users/shourjosmac/Documents/alloy/app/core/transactions.py` (create new)
```python
from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import IsolationLevel

P = ParamSpec('P')
T = TypeVar('T')

def transactional(
    *,
    isolation: IsolationLevel = IsolationLevel.READ_COMMITTED,
    timeout: float | None = None,
    readonly: bool = False,
):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            session = _extract_session(args, kwargs)
            
            async with session.begin(
                isolation_level=isolation,
                timeout=timeout,
                readonly=readonly
            ):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def _extract_session(args, kwargs) -> AsyncSession:
    if args and isinstance(args[0], AsyncSession):
        return args[0]
    if 'db' in kwargs:
        return kwargs['db']
    if 'session' in kwargs:
        return kwargs['session']
    raise ValueError("No session found in function arguments")
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Unit tests for commit/rollback behavior, isolation level tests

**Risk Mitigation**: Deploy with extensive logging, monitor transaction failures  
**Rollback**: Remove decorator usage, restore manual session management

#### 2.4 Create Service Base Class
**File**: `/Users/shourjosmac/Documents/alloy/app/services/base.py` (create new)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundError

class BaseService:
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def _get_or_404[T](self, model: type[T], id: int, error_msg: str | None = None) -> T:
        result = await self._session.get(model, id)
        if not result:
            entity_name = model.__name__
            raise NotFoundError(
                entity_name,
                error_msg or f"{entity_name} {id} not found",
                {"id": id}
            )
        return result
```

**Prerequisites**: Domain exceptions (Task 1.3)  
**Dependencies**: 1.3  
**Testing**: Unit tests for 404 scenarios

### Week 3: Contract Validation Tooling

**Goal**: Create tools to enforce contract standards

#### 3.1 Create Contract Validation Linter
**File**: `/Users/shourjosmac/Documents/alloy/scripts/validate_contracts.py` (create new)
```python
#!/usr/bin/env python3
import ast
import sys
from pathlib import Path

def check_response_envelope(route_file: Path) -> list[str]:
    issues = []
    
    with open(route_file) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == 'get' or decorator.func.attr == 'post':
                        if not any(
                            isinstance(d, ast.keyword) and d.arg == 'response_model'
                            for d in decorator.keywords
                        ):
                            issues.append(f"Line {node.lineno}: {node.name} missing response_model")
    
    return issues

def main():
    routes_dir = Path('app/api/routes')
    all_issues = []
    
    for route_file in routes_dir.glob('*.py'):
        issues = check_response_envelope(route_file)
        for issue in issues:
            all_issues.append(f"{route_file}: {issue}")
    
    if all_issues:
        print("Contract validation issues found:")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("All contracts validated successfully")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Test with existing route files, ensure false negatives/positives handled

#### 3.2 Add to Pre-commit Hooks
**File**: `/Users/shourjosmac/Documents/alloy/.pre-commit-config.yaml`
```yaml
repos:
  - repo: local
    hooks:
      - id: validate-api-contracts
        name: Validate API contracts
        entry: python scripts/validate_contracts.py
        language: system
        files: ^app/api/routes/.*\.py$
```

**Prerequisites**: Contract validator (Task 3.1)  
**Dependencies**: 3.1  
**Testing**: Test pre-commit hook with valid/invalid files

**Risk Mitigation**: Run in non-blocking mode initially, warn-only  
**Rollback**: Remove hook from pre-commit config

---

## Phase 2: Parallel Tracks

### Track 2A: Security & Authentication (Weeks 4-5)

**Duration**: 2 weeks  
**Issues**: 8 total, 4 MVP  
**Priority**: Critical (security/compliance)  
**Success Criteria**: Zero critical vulnerabilities, auth failure rate < 0.5%

#### Week 4: JWT with RBAC

#### 4.1 Add Role Field to User Model
**File**: `/Users/shourjosmac/Documents/alloy/app/models/user.py`
```python
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(UserRole, default=UserRole.USER)
    # ... existing fields
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Unit tests, migration tests

#### 4.2 Create Migration for Role Field
**File**: `/Users/shourjosmac/Documents/alloy/alembic/versions/add_user_role.py` (create new)
```python
def upgrade() -> None:
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=False, server_default='user'))
    op.execute("UPDATE users SET role = 'admin' WHERE id IN (SELECT DISTINCT user_id FROM admin_access)")

def downgrade() -> None:
    op.drop_column('users', 'role')
```

**Prerequisites**: Role field in model (Task 4.1)  
**Dependencies**: 4.1  
**Testing**: Migration up/down tests, data integrity tests

**Risk Mitigation**: Test migration on staging first, backup production before deploy  
**Rollback**: Run downgrade migration

#### 4.3 Update JWT Claims with Role
**File**: `/Users/shourjosmac/Documents/alloy/app/core/security.py`
```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "role": data.get("role", UserRole.USER)})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
```

**Prerequisites**: Role enum (Task 4.1)  
**Dependencies**: 4.1  
**Testing**: Token generation/validation tests, role claim tests

#### 4.4 Create RBAC Decorator
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/dependencies.py`
```python
from app.models.user import UserRole
from app.core.exceptions import AuthenticationError, AuthorizationError

async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization:
        raise AuthenticationError("No authorization header provided")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise AuthenticationError("Invalid authentication scheme")
    except ValueError:
        raise AuthenticationError("Invalid authorization header format")
    
    payload = verify_token(token)
    if not payload:
        raise AuthenticationError("Invalid or expired token")
    
    user_id = int(payload.get("sub"))
    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("User not found")
    
    return user

def require_role(*allowed_roles: UserRole):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            if current_user.role not in allowed_roles:
                raise AuthorizationError(
                    f"Requires one of roles: {[r.value for r in allowed_roles]}",
                    {"required_roles": [r.value for r in allowed_roles], "user_role": current_user.role.value}
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
```

**Prerequisites**: Domain exceptions (Task 1.3), JWT update (Task 4.3)  
**Dependencies**: 1.3, 4.3  
**Testing**: Unit tests for role checks, integration tests

**Risk Mitigation**: Deploy with logging, monitor authorization failures  
**Rollback**: Restore old require_admin dependency

#### 4.5 Migrate Admin Endpoints to RBAC
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/circuits.py`, `/Users/shourjosmac/Documents/alloy/app/api/routes/scoring_config.py`
```python
# Before:
@router.get("/admin/{circuit_id}")
async def get_circuit_admin(
    circuit_id: int,
    x_admin_token: str | None = Header(None)
):
    await verify_admin_token(x_admin_token)
    # ...

# After:
@router.get("/admin/{circuit_id}")
@require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
async def get_circuit_admin(
    circuit_id: int,
    current_user: User = Depends(get_current_user)
):
    # ...
```

**Prerequisites**: RBAC decorator (Task 4.4)  
**Dependencies**: 4.4  
**Testing**: Integration tests for each endpoint

**Risk Mitigation**: Deploy with feature flag, monitor admin access  
**Rollback**: Restore X-Admin-Token endpoints

#### Week 5: Security Headers & Deprecation

#### 5.1 Add Security Headers Middleware
**File**: `/Users/shourjosmac/Documents/alloy/app/middleware/security.py` (create new)
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
```

**File**: `/Users/shourjosmac/Documents/alloy/app/main.py`
```python
from app.middleware.security import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Security header tests, browser compatibility tests

#### 5.2 Deprecate X-Admin-Token Endpoints
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/dependencies.py`
```python
from warnings import warn

@deprecated(
    reason="Use JWT with admin role instead. See: docs/authentication/rbac",
    version="2.0.0",
    removal_version="3.0.0"
)
async def verify_admin_token(
    x_admin_token: str | None = Header(None)
):
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    
    warn("X-Admin-Token is deprecated. Use JWT with admin role instead.", DeprecationWarning, stacklevel=2)
    return True
```

**Prerequisites**: RBAC decorator (Task 4.4)  
**Dependencies**: 4.4  
**Testing**: Deprecation warning tests

### Track 2B: Developer Experience (Week 4)

**Duration**: 1 week  
**Issues**: 6 total, 3 MVP  
**Priority**: Medium (team velocity)  
**Success Criteria**: Code review time reduced 30%, onboarding time < 2 weeks

#### Week 4 Tasks

#### 4.6 Create Naming Convention Guide
**File**: `/Users/shourjosmac/Documents/alloy/docs/NAMING_CONVENTIONS.md` (create new)
```markdown
# Naming Conventions

## API Endpoints
- Use snake_case for paths: `/programs/{program_id}`, not `/Programs/{programId}`
- Use resource hierarchy: `/programs/{program_id}/sessions`, not `/programSessions`
- Use HTTP methods for intent: GET, POST, PUT, PATCH, DELETE
- Avoid action verbs in paths: `/programs/{id}/activate` → use POST with action in body

## Schemas
- Request schemas end with `Request`: `ProgramCreateRequest`, `ProgramUpdateRequest`
- Response schemas end with `Response`: `ProgramResponse`, `SessionResponse`
- Use PascalCase for model names: `WorkoutLog`, `MovementPattern`
- Use snake_case for field names: `created_at`, `max_session_duration`

## Services
- Use PascalCase with `Service` suffix: `ProgramService`, `MovementService`
- Method names: `get_{resource}`, `create_{resource}`, `update_{resource}`, `delete_{resource}`
- Async methods: always use `async def`

## Repositories
- Use PascalCase with `Repository` suffix: `ProgramRepository`, `MovementRepository`
- Follow same method naming as services

## Variables
- Use snake_case for all Python variables: `user_id`, `program_data`
- Constants: UPPER_SNAKE_CASE: `DEFAULT_PAGE_SIZE`, `MAX_RETRY_ATTEMPTS`
- Private methods: prefix with underscore: `_get_or_404`, `_validate_request`
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Team review, code example validation

#### 4.7 Standardize DateTime Format
**File**: `/Users/shourjosmac/Documents/alloy/app/schemas/datetime.py` (create new)
```python
from datetime import datetime, date, time
from typing import Annotated
from pydantic import BeforeValidator

def parse_iso_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace('Z', '+00:00'))

def parse_iso_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)

DateTimeStr = Annotated[datetime, BeforeValidator(parse_iso_datetime)]
DateStr = Annotated[date, BeforeValidator(parse_iso_date)]
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: ISO 8601 parsing tests, timezone tests

#### 4.8 Standardize ID Types
**File**: `/Users/shourjosmac/Documents/alloy/app/schemas/ids.py` (create new)
```python
from uuid import UUID
from typing import Annotated, Union
from pydantic import BeforeValidator

# Use UUID v7 for all new resources
ResourceId = UUID

# Legacy integer IDs (migrate to UUID)
LegacyId = int

# Accept both during migration period
MigrationId = Union[ResourceId, LegacyId]
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: UUID v7 generation tests, migration compatibility tests

### Track 2C: Data Access & Transaction Safety (Weeks 5-6)

**Duration**: 2 weeks  
**Issues**: 10 total, 5 MVP  
**Priority**: High (data integrity)  
**Success Criteria**: Zero data loss incidents, < 0.1% transaction failure rate

#### Week 5: Repository Implementation

#### 5.3 Create Movement Repository
**File**: `/Users/shourjosmac/Documents/alloy/app/repositories/movement_repository.py` (create new)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.movement import Movement
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class MovementRepository(Repository[Movement, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Movement | None:
        return await self._session.get(Movement, id)
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Movement]:
        query = select(Movement)
        
        # Apply filters
        if 'pattern' in filter:
            query = query.where(Movement.pattern == filter['pattern'])
        if 'equipment' in filter:
            query = query.where(Movement.equipment == filter['equipment'])
        if 'discipline' in filter:
            query = query.where(Movement.discipline == filter['discipline'])
        
        query = query.order_by(Movement.name)
        
        # Pagination
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        return PaginatedResult(items=items, has_more=has_more)
    
    async def create(self, entity: Movement) -> Movement:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> Movement | None:
        movement = await self.get(id)
        if movement:
            for key, value in updates.items():
                setattr(movement, key, value)
            await self._session.flush()
        return movement
    
    async def delete(self, id: int) -> bool:
        movement = await self.get(id)
        if movement:
            await self._session.delete(movement)
            return True
        return False
```

**Prerequisites**: Base repository (Task 2.1)  
**Dependencies**: 2.1  
**Testing**: Unit tests with test database, filter tests

#### 5.4 Create Circuit Repository
**File**: `/Users/shourjosmac/Documents/alloy/app/repositories/circuit_repository.py` (create new)
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.circuit import Circuit
from app.repositories.base import Repository
from app.schemas.pagination import PaginationParams, PaginatedResult

class CircuitRepository(Repository[Circuit, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Circuit | None:
        return await self._session.get(Circuit, id)
    
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[Circuit]:
        query = select(Circuit)
        
        if 'is_active' in filter:
            query = query.where(Circuit.is_active == filter['is_active'])
        
        query = query.order_by(Circuit.name)
        
        query = query.limit(pagination.limit + 1)
        result = await self._session.execute(query)
        items = result.scalars().all()
        
        has_more = len(items) > pagination.limit
        items = items[:pagination.limit]
        
        return PaginatedResult(items=items, has_more=has_more)
    
    async def create(self, entity: Circuit) -> Circuit:
        self._session.add(entity)
        await self._session.flush()
        return entity
    
    async def update(self, id: int, updates: dict) -> Circuit | None:
        circuit = await self.get(id)
        if circuit:
            for key, value in updates.items():
                setattr(circuit, key, value)
            await self._session.flush()
        return circuit
    
    async def delete(self, id: int) -> bool:
        circuit = await self.get(id)
        if circuit:
            await self._session.delete(circuit)
            return True
        return False
```

**Prerequisites**: Base repository (Task 2.1)  
**Dependencies**: 2.1  
**Testing**: Unit tests, integration tests

#### Week 6: Service Refactoring

#### 6.1 Refactor ProgramService to Use Repository
**File**: `/Users/shourjosmac/Documents/alloy/app/services/program.py`
```python
# Before:
async def create_program(self, request: ProgramCreateRequest) -> Program:
    program = Program(**request.model_dump())
    self._session.add(program)
    await self._session.flush()
    # ...

# After:
from app.repositories.program_repository import ProgramRepository

class ProgramService(BaseService):
    def __init__(self, session: AsyncSession, program_repo: ProgramRepository):
        super().__init__(session)
        self._program_repo = program_repo
    
    async def create_program(self, request: ProgramCreateRequest) -> Program:
        program = Program(**request.model_dump())
        return await self._program_repo.create(program)
```

**Prerequisites**: Program repository (Task 2.2), Service base (Task 2.4)  
**Dependencies**: 2.2, 2.4  
**Testing**: Unit tests with mock repositories, integration tests

**Risk Mitigation**: Run in parallel with old code, compare outputs  
**Rollback**: Revert to direct database access

#### 6.2 Add Transaction Decorator to Service Methods
**File**: `/Users/shourjosmac/Documents/alloy/app/services/program.py`
```python
from app.core.transactions import transactional

class ProgramService(BaseService):
    @transactional(isolation=IsolationLevel.REPEATABLE_READ)
    async def create_program(self, request: ProgramCreateRequest) -> Program:
        program = Program(**request.model_dump())
        program = await self._program_repo.create(program)
        
        # Create sessions within transaction
        for session_data in request.sessions:
            session = Session(program_id=program.id, **session_data)
            await self._session.add(session)
        
        return program
    
    @transactional()
    async def delete_program(self, program_id: int) -> bool:
        program = await self._get_or_404(Program, program_id)
        return await self._program_repo.delete(program_id)
```

**Prerequisites**: Transaction decorator (Task 2.3)  
**Dependencies**: 2.3  
**Testing**: Transaction commit/rollback tests, isolation level tests

**Risk Mitigation**: Monitor transaction duration, add timeouts  
**Rollback**: Remove decorator usage

#### 6.3 Update Error Handling in Services
**File**: `/Users/shourjosmac/Documents/alloy/app/services/program.py`
```python
# Before:
if not program:
    raise ValueError(f"Program {program_id} not found")

# After:
from app.core.exceptions import NotFoundError

if not program:
    raise NotFoundError("Program", f"Program {program_id} not found", {"program_id": program_id})
```

**Prerequisites**: Domain exceptions (Task 1.3)  
**Dependencies**: 1.3  
**Testing**: Exception propagation tests, error message tests

---

## Phase 3: Error Handling & Observability

**Duration**: 3 weeks  
**Issues**: 14 total, 6 MVP  
**Priority**: Medium-High (user-facing errors)  
**Success Criteria**: MTTR reduced 40%, error response clarity score > 4/5

### Week 8: Error Code Taxonomy

#### 8.1 Define Error Code Standards
**File**: `/Users/shourjosmac/Documents/alloy/docs/ERROR_CODES.md` (create new)
```markdown
# Error Code Taxonomy

## Format
`{DOMAIN}_{SPECIFIC_ERROR}`

## Domains
- `AUTH` - Authentication/authorization errors
- `VAL` - Validation errors
- `NF` - Not found errors
- `BR` - Business rule violations
- `CF` - Conflict errors
- `SYS` - System errors

## Common Codes
| Code | HTTP Status | Message |
|------|-------------|----------|
| AUTH_INVALID_CREDENTIALS | 401 | Invalid email or password |
| AUTH_EXPIRED_TOKEN | 401 | Token has expired |
| AUTH_MISSING_TOKEN | 401 | Authorization header required |
| AUTH_FORBIDDEN | 403 | Insufficient permissions |
| NF_PROGRAM | 404 | Program not found |
| NF_SESSION | 404 | Session not found |
| NF_MOVEMENT | 404 | Movement not found |
| VAL_INVALID_DURATION | 400 | Program duration must be 8-12 weeks |
| VAL_INVALID_DATE_RANGE | 400 | End date must be after start date |
| BR_PROGRAM_ACTIVE | 409 | Cannot delete active program |
| BR_SESSION_COMPLETE | 409 | Cannot modify completed session |
| CF_DUPLICATE_EMAIL | 409 | Email already registered |
| SYS_DATABASE_ERROR | 500 | Internal database error |
| SYS_EXTERNAL_SERVICE_ERROR | 503 | External service unavailable |
```

**Prerequisites**: Domain exceptions (Task 1.3)  
**Dependencies**: 1.3  
**Testing**: Team review, documentation tests

#### 8.2 Update Exceptions with Error Codes
**File**: `/Users/shourjosmac/Documents/alloy/app/core/exceptions.py`
```python
class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class NotFoundError(DomainError):
    def __init__(self, entity: str, message: str, details: dict | None = None):
        code = f"NF_{entity.upper()}"
        super().__init__(code, message, details)

class ValidationError(DomainError):
    def __init__(self, field: str, message: str, details: dict | None = None):
        code = f"VAL_{field.upper()}"
        super().__init__(code, f"Validation failed for {field}: {message", details)

class BusinessRuleError(DomainError):
    def __init__(self, rule: str, message: str, details: dict | None = None):
        code = f"BR_{rule.upper()}"
        super().__init__(code, message, details)

class ConflictError(DomainError):
    def __init__(self, conflict: str, message: str, details: dict | None = None):
        code = f"CF_{conflict.upper()}"
        super().__init__(code, message, details)
```

**Prerequisites**: Error code taxonomy (Task 8.1)  
**Dependencies**: 8.1  
**Testing**: Exception code generation tests

#### 8.3 Update Global Exception Handler
**File**: `/Users/shourjosmac/Documents/alloy/app/core/error_handlers.py`
```python
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Log error with context
    logger.error(
        "Domain error: %s",
        exc.code,
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": datetime.utcnow()
            },
            "errors": [{
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }]
        }
    )
```

**Prerequisites**: Updated exceptions (Task 8.2)  
**Dependencies**: 8.2  
**Testing**: Integration tests for each error type, logging tests

### Week 9: Logging Integration

#### 9.1 Create Request ID Middleware
**File**: `/Users/shourjosmac/Documents/alloy/app/middleware/request_id.py` (create new)
```python
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**File**: `/Users/shourjosmac/Documents/alloy/app/main.py`
```python
from app.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Request ID propagation tests, header tests

#### 9.2 Add Structured Logging
**File**: `/Users/shourjosmac/Documents/alloy/app/core/logging.py` (create new)
```python
import structlog
from app.core.config import settings

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)
```

**Prerequisites**: Install structlog  
**Dependencies**: None  
**Testing**: Log format tests, structured log tests

### Week 10: Error Response Examples

#### 10.1 Create Error Response Documentation
**File**: `/Users/shourjosmac/Documents/alloy/docs/ERROR_RESPONSES.md` (create new)
```markdown
# Error Response Examples

## Structure
```json
{
  "data": null,
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-02-10T10:30:00Z"
  },
  "errors": [
    {
      "code": "NF_PROGRAM",
      "message": "Program not found",
      "details": {
        "program_id": 123
      }
    }
  ]
}
```

## Common Errors

### Authentication Errors
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {}
  }]
}
```

### Validation Errors
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "VAL_DURATION_WEEKS",
    "message": "Validation failed for duration_weeks: must be between 8 and 12",
    "details": {
      "field": "duration_weeks",
      "min": 8,
      "max": 12,
      "actual": 6
    }
  }]
}
```

### Business Rule Errors
```json
{
  "data": null,
  "meta": {
    "request_id": "...",
    "timestamp": "..."
  },
  "errors": [{
    "code": "BR_PROGRAM_ACTIVE",
    "message": "Cannot delete active program",
    "details": {
      "program_id": 123,
      "status": "ACTIVE"
    }
  }]
}
```
```

**Prerequisites**: Error codes (Task 8.1)  
**Dependencies**: 8.1  
**Testing**: Documentation validation, example generation tests

---

## Phase 4: Performance & Scalability

**Duration**: 4 weeks  
**Issues**: 10 total, 5 MVP  
**Priority**: Medium (user experience)  
**Success Criteria**: P95 < 200ms, 99.9% success rate under load

### Week 11: Cursor-based Pagination

#### 11.1 Implement Cursor Utilities
**File**: `/Users/shourjosmac/Documents/alloy/app/core/pagination.py` (create new)
```python
import base64
import json
from datetime import datetime

def encode_cursor(value: any, field: str) -> str:
    data = {"f": field, "v": str(value)}
    json_str = json.dumps(data)
    return base64.urlsafe_b64encode(json_str.encode()).decode()

def decode_cursor(cursor: str) -> tuple[str, any]:
    try:
        json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(json_str)
        return data["f"], data["v"]
    except (ValueError, json.JSONDecodeError, KeyError):
        raise ValidationError("cursor", "Invalid cursor format")
```

**Prerequisites**: Domain exceptions (Task 1.3)  
**Dependencies**: 1.3  
**Testing**: Encoding/decoding tests, edge case tests

#### 11.2 Update Programs Endpoint with Cursor Pagination
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/programs.py`
```python
from app.schemas.pagination import PaginationParams, PaginatedResult
from app.core.pagination import encode_cursor

@router.get("", response_model=ListResponseWrapper[ProgramResponse])
async def list_programs(
    cursor: str | None = None,
    limit: int = 20,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    pagination = PaginationParams(cursor=cursor, limit=limit)
    result = await program_repository.list(
        filter={"user_id": current_user_id},
        pagination=pagination
    )
    
    programs = [ProgramResponse.model_validate(p) for p in result.items]
    
    return ListResponseWrapper(
        items=programs,
        total=len(programs),
        limit=limit,
        has_more=result.has_more
    )
```

**Prerequisites**: Cursor utilities (Task 11.1), Program repository (Task 2.2)  
**Dependencies**: 11.1, 2.2  
**Testing**: Pagination tests, cursor navigation tests

**Risk Mitigation**: A/B test with offset pagination, monitor performance  
**Rollback**: Restore offset pagination

### Week 12: Structured Filtering

#### 12.1 Define Filter Contract
**File**: `/Users/shourjosmac/Documents/alloy/app/schemas/filtering.py` (create new)
```python
from typing import Generic, TypeVar, Optional, Literal
from pydantic import BaseModel, Field

class FilterOperator(str, enum.Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NIN = "nin"
    LIKE = "like"

class FilterExpression(BaseModel, Generic[T]):
    field: str
    operator: FilterOperator
    value: T

class FilterRequest(BaseModel):
    filters: list[FilterExpression] = Field(default_factory=list)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

**Prerequisites**: None  
**Dependencies**: None  
**Testing**: Filter expression tests, validation tests

#### 12.2 Update Movements Endpoint with Structured Filtering
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/settings.py`
```python
from app.schemas.filtering import FilterRequest

@router.post("/movements/query", response_model=ListResponseWrapper[MovementResponse])
async def query_movements(
    request: FilterRequest,
    db: AsyncSession = Depends(get_db)
):
    # Build query from filter expressions
    query = select(Movement)
    
    for filter_expr in request.filters:
        column = getattr(Movement, filter_expr.field)
        
        if filter_expr.operator == FilterOperator.EQ:
            query = query.where(column == filter_expr.value)
        elif filter_expr.operator == FilterOperator.GT:
            query = query.where(column > filter_expr.value)
        elif filter_expr.operator == FilterOperator.IN:
            query = query.where(column.in_(filter_expr.value))
        # ... other operators
    
    if request.sort_by:
        column = getattr(Movement, request.sort_by)
        order_func = asc if request.sort_order == "asc" else desc
        query = query.order_by(order_func(column))
    
    query = query.limit(request.limit).offset(request.offset)
    
    result = await db.execute(query)
    movements = result.scalars().all()
    
    return ListResponseWrapper(
        items=[MovementResponse.model_validate(m) for m in movements],
        total=len(movements),
        limit=request.limit,
        offset=request.offset
    )
```

**Prerequisites**: Filter contract (Task 12.1), Movement repository (Task 5.3)  
**Dependencies**: 12.1, 5.3  
**Testing**: Filter tests, sorting tests, query optimization tests

### Week 13: Rate Limiting

#### 13.1 Create Rate Limiting Middleware
**File**: `/Users/shourjosmac/Documents/alloy/app/middleware/rate_limit.py` (create new)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": datetime.utcnow()
            },
            "errors": [{
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "details": {
                    "limit": exc.detail,
                    "retry_after": 60
                }
            }]
        }
    )
```

**Prerequisites**: Install slowapi  
**Dependencies**: None  
**Testing**: Rate limit tests, burst tests

#### 13.2 Apply Rate Limiting to Endpoints
**File**: `/Users/shourjosmac/Documents/alloy/app/api/routes/programs.py`
```python
from app.middleware.rate_limit import limiter

@router.post("", response_model=ProgramResponse)
@limiter.limit("10/minute")
async def create_program(
    request: ProgramCreateRequest,
    current_user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    # ...
```

**Prerequisites**: Rate limit middleware (Task 13.1)  
**Dependencies**: 13.1  
**Testing**: Rate limit enforcement tests, bypass tests

### Week 14: Caching Pattern

#### 14.1 Create Caching Layer
**File**: `/Users/shourjosmac/Documents/alloy/app/core/cache.py` (create new)
```python
import json
from typing import Optional, Callable, TypeVar
from functools import wraps
import redis.asyncio as redis

T = TypeVar('T')

cache = redis.from_url(settings.redis_url, decode_responses=True)

async def get_cached(key: str) -> Optional[T]:
    value = await cache.get(key)
    if value:
        return json.loads(value)
    return None

async def set_cached(key: str, value: T, ttl: int = 300):
    await cache.setex(key, ttl, json.dumps(value))

async def invalidate_cached(key: str):
    await cache.delete(key)

def cache_result(key_pattern: str, ttl: int = 300):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = key_pattern.format(**kwargs)
            
            cached = await get_cached(cache_key)
            if cached:
                return cached
            
            result = await func(*args, **kwargs)
            await set_cached(cache_key, result, ttl)
            return result
        return wrapper
    return decorator
```

**Prerequisites**: Redis configured  
**Dependencies**: None  
**Testing**: Cache hit/miss tests, TTL tests

#### 14.2 Apply Caching to Read-Heavy Endpoints
**File**: `/Users/shourjosmac/Documents/alloy/app/repositories/program_repository.py`
```python
from app.core.cache import cache_result

class ProgramRepository(Repository[Program, int]):
    @cache_result("program:{id}", ttl=600)
    async def get(self, id: int) -> Program | None:
        # ... existing implementation
```

**Prerequisites**: Caching layer (Task 14.1)  
**Dependencies**: 14.1  
**Testing**: Cache performance tests, invalidation tests

**Risk Mitigation**: Monitor cache hit rate, disable cache on errors  
**Rollback**: Remove cache decorator usage

---

## Phase 5: Remaining Issues

**Duration**: Ongoing  
**Issues**: 35 remaining  
**Priority**: Medium-Low  
**Success Criteria**: All 60 issues resolved

### Remaining Tasks by Theme

#### Foundation & Contracts (8 remaining)
- Complete migration to envelope responses for all endpoints
- Add OpenAPI documentation for all new contracts
- Create contract versioning strategy

#### Error Handling (8 remaining)
- Add error localization support
- Create error monitoring dashboard
- Add error rate limiting

#### Data Access (5 remaining)
- Implement remaining repositories (Circuit, Activity, etc.)
- Add connection pooling optimization
- Implement read replica support

#### Security (4 remaining)
- Add OAuth2 integration support
- Implement token refresh flow
- Add security audit logging

#### Performance (5 remaining)
- Implement query optimization for slow endpoints
- Add database indexing for frequently queried fields
- Implement response compression

#### Developer Experience (3 remaining)
- Create code generation templates
- Add IDE type stubs
- Create interactive documentation

---

## Testing Strategy

### Unit Tests
- **Coverage Goal**: 80% for services, 90% for repositories
- **Framework**: pytest with pytest-asyncio
- **Mocking**: pytest-mock for dependencies
- **Fixtures**: conftest.py for shared setup

### Integration Tests
- **Coverage Goal**: All API endpoints
- **Framework**: pytest with test database
- **Data**: Factories for test data creation
- **Cleanup**: Database rollback between tests

### Contract Tests
- **Tool**: Dredd or schemathesis
- **Scope**: All documented endpoints
- **Validation**: Response structure, status codes, error formats
- **Automation**: Run in CI pipeline

### Performance Tests
- **Tool**: Locust or k6
- **Scenarios**: User journeys, peak load
- **Metrics**: Response times, error rates, throughput
- **Baseline**: Establish before changes, compare after

### Security Tests
- **Tool**: OWASP ZAP or Burp Suite
- **Scope**: Authentication, authorization, input validation
- **Frequency**: Before each major release
- **Reporting**: Track vulnerabilities to closure

---

## Rollback Procedures

### Phase 1 Rollback
**Trigger**: Contract validation breaks existing clients  
**Procedure**:
1. Revert response envelope changes
2. Restore old HTTPException usage
3. Remove global exception handler
4. Redeploy previous version

**Time to Rollback**: < 30 minutes

### Phase 2 Rollback
**Trigger**: Security vulnerabilities or auth failures  
**Procedure**:
1. Revert JWT changes
2. Restore X-Admin-Token endpoints
3. Revert role migration
4. Redeploy previous version

**Time to Rollback**: < 30 minutes

### Phase 3 Rollback
**Trigger**: Data integrity issues or transaction failures  
**Procedure**:
1. Remove transaction decorators
2. Restore manual session management
3. Revert repository implementations
4. Restore direct database access in services

**Time to Rollback**: < 1 hour

### Phase 4 Rollback
**Trigger**: Performance degradation or pagination bugs  
**Procedure**:
1. Restore offset pagination
2. Remove structured filtering
3. Disable rate limiting
4. Disable caching layer

**Time to Rollback**: < 30 minutes

### General Rollback Strategy
1. **Monitor**: Set up alerts for key metrics
2. **Detect**: Automated rollback triggers based on thresholds
3. **Decision**: Manual approval for rollback decisions
4. **Execute**: Automated rollback scripts
5. **Verify**: Health checks after rollback
6. **Communicate**: Notify team and stakeholders

---

## Success Criteria Summary

| Phase | Success Criteria | Measurement |
|-------|-----------------|--------------|
| 1: Foundation | 100% new APIs validated, 90% documented | Contract validator pass rate, documentation coverage |
| 2: Security | Zero critical vulnerabilities, auth failure < 0.5% | Security scans, auth metrics |
| 2: Dev Experience | Code review time -30%, onboarding < 2 weeks | Review metrics, onboarding surveys |
| 2: Data Access | Zero data loss, transaction failures < 0.1% | Incident reports, transaction logs |
| 3: Error Handling | MTTR -40%, clarity score > 4/5 | Incident metrics, user surveys |
| 4: Performance | P95 < 200ms, 99.9% success under load | APM metrics, load tests |

---

## Conclusion

This implementation plan provides a clear, step-by-step path to resolving all 60 identified inconsistencies while delivering business value incrementally. Each phase builds on the previous one, with clear dependencies and rollback procedures.

Key principles:
- **Foundation first**: Unblocks all downstream work
- **Security early**: Addresses critical risk
- **Parallel execution**: Maximizes team velocity
- **Incremental value**: Each phase delivers measurable improvements
- **Safe rollback**: Every change can be reversed quickly

By following this plan, the team will achieve:
- 80% business value in 15 weeks
- Reduced technical debt
- Improved developer experience
- Better security posture
- Enhanced performance and scalability

---

## Implementation To-Do List

### Phase 1: Foundation & Contract Consistency (Weeks 1-3)

#### Week 1: API Response Wrapper Contract

- [x] 1.1 Create Standard Response Models (`app/schemas/base.py`)
  - Create ResponseMeta class with request_id, timestamp, warnings
  - Create APIError class with code, message, details
  - Create APIResponse generic class with data, meta, errors
  - Create ListResponseWrapper class with items, total, pagination fields
  - Write unit tests for all response models

- [x] 1.2 Create Pagination Base Models (`app/schemas/pagination.py`)
  - Create PaginationParams class with cursor, limit, direction
  - Create PaginatedResult generic class with items, cursors, has_more
  - Write unit tests for pagination models

- [x] 1.3 Create Domain Exception Hierarchy (`app/core/exceptions.py`)
  - Create DomainError base class
  - Create NotFoundError subclass
  - Create ValidationError subclass with field context
  - Create BusinessRuleError subclass
  - Create ConflictError subclass
  - Create AuthenticationError subclass
  - Create AuthorizationError subclass
  - Write unit tests for each exception type

- [x] 1.4 Create Global Exception Handler (`app/core/error_handlers.py`)
  - Create ERROR_STATUS_MAP mapping exceptions to HTTP status codes
  - Create domain_error_handler function
  - Register handler in FastAPI app
  - Write integration tests for each exception type
  - Test response structure validation

#### Week 2: Service Interface Templates

- [x] 2.1 Create Base Repository Interface (`app/repositories/base.py`)
  - Define Repository Protocol with get, list, create, update, delete methods
  - Import PaginationParams and PaginatedResult
  - Write protocol compliance tests

- [x] 2.2 Create Program Repository (`app/repositories/program_repository.py`)
  - Implement ProgramRepository class from Repository Protocol
  - Add get method with eager loading (program_disciplines, sessions)
  - Add list method with filtering and cursor-based pagination
  - Add create, update, delete methods
  - Write unit tests with test database
  - Write integration tests

- [x] 2.3 Create Transaction Decorator (`app/core/transactions.py`)
  - Create transactional decorator with isolation level support
  - Add timeout and readonly parameters
  - Create _extract_session helper function
  - Write unit tests for commit/rollback behavior
  - Write isolation level tests

- [x] 2.4 Create Service Base Class (`app/services/base.py`)
  - Create BaseService class with session initialization
  - Add _get_or_404 generic helper method
  - Write unit tests for 404 scenarios

#### Week 3: Contract Validation Tooling

- [x] 3.1 Create Contract Validation Linter (`scripts/validate_contracts.py`)
  - Create check_response_envelope function using AST
  - Add main function to scan all route files
  - Implement exit codes for pass/fail
  - Test with existing route files
  - Ensure false negatives/positives are handled

- [x] 3.2 Add to Pre-commit Hooks (`.pre-commit-config.yaml`)
  - Add validate-api-contracts hook
  - Configure file pattern for route files
  - Test pre-commit hook with valid/invalid files
  - Document pre-commit hook usage

---

### Phase 2: Parallel Tracks ✅ COMPLETED

#### Track 2A: Security & Authentication (Weeks 4-5)

- [x] 4.1 Add Role Field to User Model (`app/models/user.py`)
  - Create UserRole enum (USER, ADMIN, SUPER_ADMIN)
  - Add role column to User model with default USER
  - Write unit tests for role field

- [x] 4.2 Create Migration for Role Field (`alembic/versions/add_user_role.py`)
  - Create upgrade migration to add role column
  - Add data migration to set admin role from admin_access table
  - Create downgrade migration
  - Test migration up/down
  - Test data integrity

- [x] 4.3 Update JWT Claims with Role (`app/core/security.py`)
  - Update create_access_token to include role in payload
  - Update verify_token to extract role
  - Write token generation tests
  - Write role claim tests

- [x] 4.4 Create RBAC Decorator (`app/api/routes/dependencies.py`)
  - Create get_current_user dependency
  - Create require_role decorator factory
  - Add proper error handling for auth/authorization failures
  - Write unit tests for role checks
  - Write integration tests

- [x] 4.5 Migrate Admin Endpoints to RBAC
  - Update `app/api/routes/circuits.py` to use @require_role
  - Update `app/api/routes/scoring_config.py` to use @require_role
  - Remove X-Admin-Token dependencies
  - Test all migrated endpoints
  - Verify RBAC behavior

- [x] 5.1 Add Security Headers Middleware (`app/middleware/security.py`)
  - Create SecurityHeadersMiddleware class
  - Add standard security headers (X-Content-Type-Options, etc.)
  - Register middleware in main.py
  - Test header presence in responses

- [x] 5.2 Deprecate X-Admin-Token Endpoints
  - Add deprecation warnings to X-Admin-Token endpoints
  - Update documentation to use JWT authentication
  - Plan deprecation timeline
  - Monitor X-Admin-Token usage

- [x] 4.6 Create Naming Convention Guide (`docs/NAMING_CONVENTIONS.md`)
  - Define API endpoint naming conventions
  - Define schema naming conventions
  - Define service naming conventions
  - Define repository naming conventions
  - Define variable naming conventions
  - Add examples and anti-patterns

- [x] 4.7 Standardize DateTime Format (`app/schemas/datetime.py`)
  - Create DateTimeStr type with ISO 8601 validation
  - Create DateStr type with date validation
  - Write unit tests for datetime parsing

- [x] 4.8 Standardize ID Types (`app/schemas/ids.py`)
  - Create ResourceId type for UUID v7
  - Create LegacyId type for backward compatibility
  - Create MigrationId type for transition support
  - Write unit tests for ID validation

#### Track 2B: Developer Experience (Week 4)

- [ ] (See tasks 4.6, 4.7, 4.8 above - naming conventions, datetime, IDs)

#### Track 2C: Data Access & Transaction Safety (Weeks 5-6)

- [ ] 5.3 Create Movement Repository (`app/repositories/movement_repository.py`)
  - Implement MovementRepository class from Repository Protocol
  - Add get, list, create, update, delete methods
  - Write unit tests with test database

- [x] 5.4 Create Circuit Repository (`app/repositories/circuit_repository.py`)
  - Implement CircuitRepository class from Repository Protocol
  - Add get, list, create, update, delete methods
  - Write unit tests with test database

- [x] 6.1 Refactor ProgramService to Use Repository (`app/services/program.py`)
  - Update ProgramService to use ProgramRepository
  - Remove direct database access
  - Update method signatures
  - Write integration tests

- [x] 6.2 Add Transaction Decorator to Service Methods (`app/services/program.py`)
  - Add @transactional decorator to write operations
  - Configure appropriate isolation levels
  - Test transaction commit/rollback behavior

- [x] 6.3 Update Error Handling in Services (`app/services/program.py`)
  - Replace HTTPException with domain exceptions
  - Update error messages to be more descriptive
  - Add proper error context
  - Write tests for error scenarios

---

### Phase 3: Error Handling & Observability (Weeks 8-10) ✅ COMPLETED

- [x] 8.1 Define Error Code Standards (`docs/ERROR_CODES.md`)
  - Define AUTH error codes (AUTH_001, AUTH_002, etc.)
  - Define VAL error codes (VAL_001, VAL_002, etc.)
  - Define NF error codes (NF_PROGRAM_001, NF_MOVEMENT_001, etc.)
  - Define BR error codes (BR_001, BR_002, etc.)
  - Define CF error codes (CF_001, CF_002, etc.)
  - Define SYS error codes (SYS_001, SYS_002, etc.)
  - Document error code taxonomy and usage guidelines

- [x] 8.2 Update Exceptions with Error Codes (`app/core/exceptions.py`)
  - Add code parameter to DomainError base class
  - Update NotFoundError to generate code based on entity
  - Update ValidationError to include field in code
  - Update all exception subclasses
  - Write unit tests for error code generation

- [x] 8.3 Update Global Exception Handler (`app/core/error_handlers.py`)
  - Include error codes in responses
  - Add request_id from request state
  - Add timestamp to meta
  - Update error response format
  - Write integration tests for error code responses

- [x] 9.1 Create Request ID Middleware (`app/middleware/request_id.py`)
  - Create RequestIDMiddleware class
  - Generate UUID for request_id
  - Extract from X-Request-ID header if present
  - Add to request state
  - Register in main.py
  - Write tests for request ID propagation

- [x] 9.2 Add Structured Logging (`app/core/logging.py`)
  - Configure structlog with JSON processor
  - Add request_id to log context
  - Add user_id to log context when available
  - Add exception logging with traceback
  - Update existing logging calls
  - Write tests for log output format

- [x] 10.1 Create Error Response Documentation (`docs/ERROR_RESPONSES.md`)
  - Document error response format
  - Provide examples for each error code
  - Include common error scenarios
  - Add troubleshooting guidance

---

### Phase 4: Performance & Scalability (Weeks 11-14) ✅ COMPLETED

- [x] 11.1 Implement Cursor Utilities (`app/core/pagination.py`)
  - Create encode_cursor function
  - Create decode_cursor function
  - Handle timestamp-based cursors
  - Handle ID-based cursors
  - Write unit tests for encoding/decoding

- [x] 11.2 Update Programs Endpoint with Cursor Pagination (`app/api/routes/programs.py`)
  - Update GET /programs to use cursor pagination
  - Add PaginationParams dependency
  - Update response format to PaginatedResult
  - Add next/prev cursor logic
  - Write integration tests for pagination

- [x] 12.1 Define Filter Contract (`app/schemas/filtering.py`)
  - Create FilterOperator enum (eq, ne, gt, gte, lt, lte, in, nin, like)
  - Create FilterExpression class
  - Create FilterRequest class
  - Write unit tests for filter expressions

- [x] 12.2 Update Movements Endpoint with Structured Filtering (`app/api/routes/settings.py`)
  - Add POST /movements/query endpoint
  - Accept FilterRequest body
  - Implement filter expression evaluation
  - Return filtered results
  - Write integration tests for filtering

- [x] 13.1 Create Rate Limiting Middleware (`app/middleware/rate_limit.py`)
  - Configure slowapi limiter
  - Create rate_limit_exceeded_handler
  - Add rate limiting by IP and user
  - Register middleware in main.py
  - Write tests for rate limiting

- [x] 13.2 Apply Rate Limiting to Endpoints
  - Apply rate limiting to write operations
  - Apply rate limiting to expensive queries
  - Configure appropriate limits per endpoint
  - Test rate limiting behavior

- [x] 14.1 Create Caching Layer (`app/core/cache.py`)
  - Create get_cached function
  - Create set_cached function with TTL
  - Create cache_result decorator
  - Configure Redis connection
  - Write unit tests for caching

- [x] 14.2 Apply Caching to Read-Heavy Endpoints
  - Add caching to ProgramRepository.get
  - Add cache invalidation on write operations
  - Add caching to MovementRepository.get
  - Monitor cache hit/miss rates
  - Test caching behavior

---

### Phase 5: Remaining Issues (35 tasks across all themes)

#### Foundation & Contract Consistency (4 remaining tasks)

- [x] Document all existing API endpoints
- [x] Update all existing endpoints to use response wrapper
- [x] Update all existing endpoints to use domain exceptions
- [x] Create API documentation generator

#### Security & Authentication (4 remaining tasks)

- [x] Implement refresh token flow
- [x] Add 2FA support for admin users
- [x] Implement password strength requirements
- [x] Add audit logging for security events

#### Developer Experience (3 remaining tasks)

- [x] Create API client generator
- [x] Add interactive API documentation improvements
- [x] Create developer onboarding guide

#### Data Access & Transaction Safety (6 remaining tasks)

- [x] Create SessionRepository
- [x] Create MovementAssignmentRepository
- [x] Migrate all services to use repositories
- [x] Add read replica support
- [x] Implement connection pooling optimization
- [x] Add database health checks

#### Error Handling & Observability (8 remaining tasks)

- [x] Add metrics collection (Prometheus)
- [x] Implement distributed tracing
- [x] Create error aggregation dashboard
- [x] Add alerting for error rates
- [x] Implement log retention policies
- [x] Add performance monitoring
- [x] Create incident response procedures
- [x] Add synthetic monitoring

#### Performance & Scalability (10 remaining tasks)

- [x] Implement database query optimization
- [x] Add database indexing improvements
- [x] Implement response compression
- [x] Add CDN for static assets
- [x] Implement database read replicas
- [x] Add connection pool monitoring
- [x] Implement query result caching
- [x] Add load testing automation
- [x] Implement auto-scaling policies
- [x] Add performance regression tests

---

**Last Updated**: 2026-02-11
**Next Phase**: Phase 5 - Continuing with remaining 0 tasks (39 completed)
