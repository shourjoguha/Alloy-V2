# Architectural Choices

This document records key architectural decisions made during the API contract and service architecture refactoring initiative. Each decision follows the Architecture Decision Record (ADR) format.

---

## Table of Contents

1. [API Response Pattern](#api-response-pattern)
2. [Authentication & Authorization](#authentication--authorization)
3. [Pagination Strategy](#pagination-strategy)
4. [Error Handling Strategy](#error-handling-strategy)
5. [Data Access Pattern](#data-access-pattern)
6. [Transaction Management](#transaction-management)
7. [Exception Hierarchy](#exception-hierarchy)
8. [Dependency Injection](#dependency-injection)
9. [Naming Conventions](#naming-conventions)
10. [DateTime Handling](#datetime-handling)
11. [ID Types](#id-types)

---

## API Response Pattern

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: API contracts show inconsistent response structures - some endpoints return wrapped responses, others return raw data.

### Decision

Use **enveloped responses** with standard structure for all API endpoints.

### Structure

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601",
    "warnings": []
  },
  "errors": []
}
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Direct responses** | Simpler, less overhead | Inconsistent error handling, no metadata support | Rejected |
| **Headers-only metadata** | Cleaner payload | HTTP header size limits, client complexity | Rejected |
| **GraphQL-style** | Flexible querying | Complex to implement, overkill for REST | Rejected |

### Consequences

**Positive**:
- Consistent structure enables generic client-side error handling
- Pagination metadata travels naturally with data
- Extensible for future requirements (warnings, rate limit info)
- Facilitates API gateway transformations

**Negative**:
- Slightly larger response payload (~5-10%)
- Requires client-side envelope unwrapping
- May feel over-engineered for simple CRUD operations

### Migration Path

1. Create `APIResponse[T]` base model
2. Implement adapter function `envelope(data, meta)`
3. Migrate endpoints gradually starting with critical ones
4. Maintain old response formats for one major version

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#phase-1-foundation--contract-consistency)
- ADR: Response Envelope Pattern

---

## Authentication & Authorization

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Current implementation uses two authentication mechanisms - JWT Bearer tokens for most endpoints and `X-Admin-Token` header for admin endpoints.

### Decision

Unify to **JWT with Role-Based Access Control (RBAC)**. Deprecate `X-Admin-Token` header.

### Design

```python
class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

# JWT payload
{
  "sub": "user_id",
  "role": "admin",
  "exp": timestamp
}
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Dual auth (JWT + X-Admin-Token)** | Existing admin flow works | Complexity, dual code paths, security surface | Rejected |
| **Session-based authentication** | Simple revocation | Stateful, doesn't scale horizontally | Rejected |
| **API keys** | Simple for service accounts | No user context, revocation challenges | Rejected |

### Consequences

**Positive**:
- Single authentication flow reduces cognitive load
- Standard library support (FastAPI Security, OAuth2)
- Stateless tokens scale horizontally
- Role-based authorization enables fine-grained access
- Easy to integrate with external identity providers (Auth0, Firebase, Cognito)

**Negative**:
- Token revocation requires infrastructure (blacklist or short-lived tokens)
- JWT payload size grows with additional claims
- Requires careful secret management and rotation

### Migration Path

1. Add `role` field to User model
2. Update JWT claims to include role
3. Create `require_role(*roles)` decorator
4. Update admin endpoints to use RBAC
5. Deprecate `X-Admin-Token` (return 410 Gone in v3.0.0)

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#track-2a-security--authentication-weeks-4-5)
- ADR: Unified Authentication with RBAC

---

## Pagination Strategy

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Current implementation uses offset-based pagination inconsistently. Some endpoints support pagination, others don't.

### Decision

Use **cursor-based pagination** with `cursor`, `limit`, and optional `direction` parameters.

### Design

```python
class PaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = 20  # max 100
    direction: "next" | "prev" = "next"

# Cursor encoding
def encode_cursor(value: any, field: str) -> str:
    data = {"f": field, "v": str(value)}
    return base64url_encode(json.dumps(data))

def decode_cursor(cursor: str) -> tuple[str, any]:
    data = json.loads(base64url_decode(cursor))
    return data["f"], data["v"]
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Offset-based** | Simple, supports arbitrary page jumps | Performance degrades at high offsets, inconsistent during concurrent writes | Rejected |
| **Keyset pagination** | Similar to cursor | Limited to specific field types, less flexible | Rejected |
| **No pagination** | Simplest | Doesn't scale, performance issues | Rejected |

### Consequences

**Positive**:
- O(1) performance regardless of offset position
- Stable results even during concurrent modifications
- Natural support for infinite scroll
- No duplicate or skipped items during pagination
- Efficient for real-time data feeds

**Negative**:
- Cannot jump to arbitrary pages
- Requires indexed cursor field (typically `created_at` or `id`)
- Slightly more complex client-side implementation
- Sorting limited to cursor-compatible fields

### Migration Path

1. Implement cursor encoding/decoding utilities
2. Update repository `list()` methods to support cursor
3. Update API endpoints to use cursor-based pagination
4. A/B test with offset pagination during transition
5. Deprecate offset parameters after validation

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#phase-4-performance--scalability)
- ADR: Cursor-Based Pagination

---

## Error Handling Strategy

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Error responses are inconsistent across endpoints. Some raise `HTTPException` directly, others use various formats.

### Decision

Use **structured error response envelope** with `code`, `message`, `details`, and `request_id`.

### Design

```json
{
  "data": null,
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  },
  "errors": [{
    "code": "NF_PROGRAM",
    "message": "Program not found",
    "details": {
      "program_id": 123
    }
  }]
}
```

### Error Code Taxonomy

Format: `{DOMAIN}_{SPECIFIC_ERROR}`

Domains:
- `AUTH` - Authentication/authorization errors
- `VAL` - Validation errors
- `NF` - Not found errors
- `BR` - Business rule violations
- `CF` - Conflict errors
- `SYS` - System errors

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **HTTPException everywhere** | Simple, FastAPI default | Tight coupling to HTTP layer, untestable services | Rejected |
| **Generic exceptions** | Fewer classes | Lack of specificity, poor error handling | Rejected |

### Consequences

**Positive**:
- Machine-readable error codes enable client-side handling
- Debugging context via `details` and `request_id`
- Supports internationalization of error messages
- Type-safe error handling in services
- Consistent structure across all endpoints

**Negative**:
- Additional exception classes to maintain
- Requires discipline to use appropriate exception types
- May create excessive granularity if not careful

### Migration Path

1. Create domain exception hierarchy
2. Define error code taxonomy
3. Implement global exception handler
4. Update services to raise domain exceptions
5. Deprecate direct `HTTPException` usage

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#phase-3-error-handling--observability)
- [docs/ERROR_CODES.md](ERROR_CODES.md)
- ADR: Structured Error Responses

---

## Data Access Pattern

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Services directly use SQLAlchemy ORM, mixing query styles and tightly coupling business logic to persistence.

### Decision

Implement **Repository Pattern with Unit of Work**.

### Design

```python
class Repository[T, ID](Protocol):
    async def get(self, id: ID) -> T | None: ...
    async def list(self, filter: dict, pagination: PaginationParams) -> PaginatedResult[T]: ...
    async def create(self, entity: T) -> T: ...
    async def update(self, id: ID, updates: dict) -> T | None: ...
    async def delete(self, id: ID) -> bool: ...

class ProgramRepository(Repository[Program, int]):
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get(self, id: int) -> Program | None:
        result = await self._session.execute(
            select(Program)
            .options(selectinload(Program.program_disciplines))
            .where(Program.id == id)
        )
        return result.scalar_one_or_none()
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Active Record (Direct ORM)** | Simple, less code | Tight coupling, difficult to test | Rejected |
| **Data Mapper (Full abstraction)** | Complete separation | Complexity, maintenance burden | Rejected |

### Consequences

**Positive**:
- Clear separation between business logic and data access
- Easy to mock for unit testing
- Centralizes query logic and optimizations
- Enables multiple data source implementations (cache, read replicas)
- Supports domain-driven design boundaries

**Negative**:
- Additional abstraction layer increases code volume
- May feel over-engineered for simple CRUD operations
- Leaky abstraction when complex queries needed

### Migration Path

1. Create base repository interface
2. Implement `ProgramRepository` as example
3. Update `ProgramService` to use repository
4. Implement remaining repositories incrementally
5. Remove direct ORM access from services

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#phase-2-track-2c-data-access--transaction-safety-weeks-5-6)
- ADR: Repository Pattern

---

## Transaction Management

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Transactions are managed manually with inconsistent patterns. Some services use `flush()`, others use `commit()`, with only one rollback found.

### Decision

Use **explicit transaction decorator** `@transactional` with context manager support.

### Design

```python
def transactional(
    *,
    isolation: IsolationLevel = IsolationLevel.READ_COMMITTED,
    timeout: float | None = None,
    readonly: bool = False,
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session = _extract_session(args, kwargs)
            
            async with session.begin(
                isolation_level=isolation,
                timeout=timeout,
                readonly=readonly
            ):
                return await func(*args, **kwargs)
        return wrapper
    return decorator

class ProgramService(BaseService):
    @transactional(isolation=IsolationLevel.REPEATABLE_READ)
    async def create_program(self, request: ProgramCreateRequest) -> Program:
        # Multiple operations here are transactional
        program = Program(**request.model_dump())
        self._session.add(program)
        await self._session.flush()
        
        # Create sessions within transaction
        for session_data in request.sessions:
            session = Session(program_id=program.id, **session_data)
            self._session.add(session)
        
        return program
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Manual session management** | Full control | Inconsistent, potential leaks, error-prone | Rejected |
| **Context manager only** | Clear boundaries | Verbose for every method | Rejected |

### Consequences

**Positive**:
- Clear transaction boundaries in code
- Automatic rollback on exception
- Reduces boilerplate session management
- Enables transaction-level configuration (isolation, timeout)
- Consistent behavior across all services

**Negative**:
- Decorator magic may obscure control flow
- Requires careful exception handling design
- May conflict with existing explicit session management

### Migration Path

1. Create transactional decorator
2. Update critical service methods with decorator
3. Remove manual `commit()`/`rollback()` calls
4. Test transaction behavior thoroughly
5. Deploy with monitoring

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#week-6-service-refactoring)
- ADR: Transaction Decorator Pattern

---

## Exception Hierarchy

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Services use mixed exception types - `ValueError`, `HTTPException`, and some custom exceptions.

### Decision

Create **domain exception hierarchy** → service exception translation.

### Design

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
        super().__init__(code, f"Validation failed for {field}: {message}", details)

class BusinessRuleError(DomainError):
    def __init__(self, rule: str, message: str, details: dict | None = None):
        code = f"BR_{rule.upper()}"
        super().__init__(code, message, details)

class ConflictError(DomainError):
    def __init__(self, conflict: str, message: str, details: dict | None = None):
        code = f"CF_{conflict.upper()}"
        super().__init__(code, message, details)
```

### Exception to HTTP Status Mapping

```python
ERROR_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
}
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **HTTPException everywhere** | Simple, FastAPI default | Tight coupling to HTTP, untestable services | Rejected |
| **Generic exceptions** | Fewer classes | Lack of specificity, poor error handling | Rejected |

### Consequences

**Positive**:
- Clear separation between business logic and infrastructure concerns
- Enables client-specific error messages without exposing internals
- Facilitates centralized error logging and monitoring
- Supports internationalization of error messages
- Type-safe error handling in services

**Negative**:
- Additional exception classes to maintain
- Requires discipline to use appropriate exception types
- May create excessive granularity if not careful

### Migration Path

1. Create domain exception hierarchy
2. Update services to raise domain exceptions
3. Implement global exception handler for translation
4. Remove direct `HTTPException` usage from services
5. Test error responses for all exception types

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#week-2-service-interface-templates)
- [docs/ERROR_CODES.md](ERROR_CODES.md)
- ADR: Domain Exception Hierarchy

---

## Dependency Injection

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Services use mixed instantiation patterns - module-level singletons, factory functions, and instance creation.

### Decision

Use **dependency injection with factory pattern**. Leverage FastAPI's `Depends()`.

### Design

```python
# Factory function
def get_program_repository(session: AsyncSession = Depends(get_db_session)) -> ProgramRepository:
    return ProgramRepository(session)

def get_program_service(repository: ProgramRepository = Depends(get_program_repository)) -> ProgramService:
    return ProgramService(repository)

# Usage in routes
@router.get("/programs/{program_id}")
async def get_program(
    program_id: int,
    service: ProgramService = Depends(get_program_service)
):
    program = await service.get_program(program_id)
    return envelope(program)
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Singleton services** | Simple, always available | Difficult to test, no DI, inflexible config | Rejected |
| **Instance in __init__** | Explicit dependencies | Manual construction, no lifecycle management | Rejected |

### Consequences

**Positive**:
- Enables testing with mock dependencies
- Configuration flexibility
- Lifecycle management
- Clear dependency graph
- Framework integration (FastAPI Depends)

**Negative**:
- More boilerplate code
- Requires understanding of DI concepts
- Slightly more complex for simple use cases

### Migration Path

1. Create factory functions for repositories and services
2. Update route signatures to use `Depends()`
3. Remove module-level singleton instances
4. Remove factory functions that wrap singletons
5. Update tests to use dependency injection

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#week-2-service-interface-templates)
- ADR: Dependency Injection Pattern

---

## Naming Conventions

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Inconsistent naming across API endpoints, schemas, services, and variables.

### Decision

Document and enforce **standard naming conventions** following Python/FastAPI best practices.

### Conventions

#### API Endpoints
- Use `snake_case` for paths: `/programs/{program_id}`, not `/Programs/{programId}`
- Use resource hierarchy: `/programs/{program_id}/sessions`, not `/programSessions`
- Use HTTP methods for intent: GET, POST, PUT, PATCH, DELETE
- Avoid action verbs in paths

#### Schemas
- Request schemas end with `Request`: `ProgramCreateRequest`, `ProgramUpdateRequest`
- Response schemas end with `Response`: `ProgramResponse`, `SessionResponse`
- Use `PascalCase` for model names: `WorkoutLog`, `MovementPattern`
- Use `snake_case` for field names: `created_at`, `max_session_duration`

#### Services
- Use `PascalCase` with `Service` suffix: `ProgramService`, `MovementService`
- Method names: `get_{resource}`, `create_{resource}`, `update_{resource}`, `delete_{resource}`
- Async methods: always use `async def`

#### Repositories
- Use `PascalCase` with `Repository` suffix: `ProgramRepository`, `MovementRepository`
- Follow same method naming as services

#### Variables
- Use `snake_case` for all Python variables: `user_id`, `program_data`
- Constants: `UPPER_SNAKE_CASE`: `DEFAULT_PAGE_SIZE`, `MAX_RETRY_ATTEMPTS`
- Private methods: prefix with underscore: `_get_or_404`, `_validate_request`

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **No conventions** | Freedom | Inconsistent, hard to understand | Rejected |
| **CamelCase** | JavaScript standard | Non-idiomatic for Python | Rejected |

### Consequences

**Positive**:
- Consistent codebase
- Easier to understand and navigate
- Reduced cognitive load for developers
- Better IDE autocomplete
- Clear intent from naming

**Negative**:
- Requires discipline to follow conventions
- May conflict with external library conventions

### Migration Path

1. Document naming conventions in `docs/NAMING_CONVENTIONS.md`
2. Add pre-commit hooks for naming validation
3. Refactor existing code to follow conventions
4. Update code review checklist
5. Onboarding training for new developers

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#week-4-tasks)
- [docs/NAMING_CONVENTIONS.md](NAMING_CONVENTIONS.md)
- ADR: Naming Conventions

---

## DateTime Handling

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: Mixed use of `date`, `datetime`, and custom `DateType`/`TimeType`. No explicit timezone handling.

### Decision

Use **ISO 8601 with timezone** (always return UTC, accept timezone-aware input).

### Design

```python
from datetime import datetime, date
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

# Store all datetimes in UTC
created_at: DateTimeStr  # Always UTC
updated_at: DateTimeStr  # Always UTC

# Include timezone in responses
{
  "created_at": "2024-02-10T10:30:00Z",
  "updated_at": "2024-02-10T14:45:00Z"
}
```

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Unix timestamps** | Simple, unambiguous | Not human-readable, requires conversion | Rejected |
| **Custom format** | Flexible | Non-standard, confusing | Rejected |

### Consequences

**Positive**:
- Eliminates ambiguity in datetime handling
- Standard format (ISO 8601)
- Explicit timezone handling
- Client-side compatibility
- Database storage in UTC (best practice)

**Negative**:
- Requires validation and parsing logic
- Client must handle timezone conversion

### Migration Path

1. Create `DateTimeStr` and `DateStr` types
2. Update all datetime fields in schemas
3. Ensure database stores UTC
4. Document datetime format expectations
5. Add validation for timezone-aware input

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#47-standardize-datetime-format)
- ADR: ISO 8601 DateTime Handling

---

## ID Types

**Status**: Accepted  
**Date**: 2024-02-10  
**Context**: JWT stores `user_id` as string, database uses integer. Mixing of integer IDs and potential UUIDs.

### Decision

Use **UUID v7 strings for all new resources**. Maintain integer IDs for legacy during migration.

### Design

```python
from uuid import UUID, uuid7
from typing import Annotated, Union

# Use UUID v7 for all new resources
ResourceId = UUID

# Legacy integer IDs (migrate to UUID)
LegacyId = int

# Accept both during migration period
MigrationId = Union[ResourceId, LegacyId]

class Program(Base):
    __tablename__ = "programs"
    
    # New programs use UUID
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=False), default_factory=uuid7, primary_key=True)
    # ...

class User(Base):
    __tablename__ = "users"
    
    # Legacy - will migrate
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ...
```

### Why UUID v7?

UUID v7 combines the benefits of:
- **Time-ordered**: Embeds timestamp for natural sorting
- **Globally unique**: No coordination needed across services
- **URL-safe**: Base64 encoding compact representation
- **Standard**: RFC 4122 compliant

### Alternatives Considered

| Alternative | Pros | Cons | Decision |
|-------------|-------|-------|-----------|
| **Integer IDs** | Simple, compact | Not globally unique, sequential | Rejected |
| **UUID v4** | Standard, unique | Not time-ordered, random | Rejected |
| **ULID** | Time-ordered, compact | Less standard than UUID | Rejected |
| **Snowflake IDs** | Time-ordered, compact | Coordination required, Twitter-specific | Rejected |

### Consequences

**Positive**:
- Time-ordered, globally unique identifiers
- No coordination needed for ID generation
- Supports microservice extraction
- URL-safe with base64 encoding
- Future-proof for distributed systems

**Negative**:
- Larger than integer IDs (36 chars vs 10 digits)
- Requires migration for existing integer IDs
- Less human-readable

### Migration Path

1. Add `ResourceId` type alias for UUID
2. Update new models to use UUID v7
3. Maintain integer IDs for existing models
4. Create migration script for legacy data
5. Update API to accept both types during transition
6. Deprecate integer IDs after migration

### References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md#48-standardize-id-types)
- ADR: UUID v7 Identifiers

---

## Summary of Architectural Principles

This document captures decisions guided by the following principles:

1. **Consistency Over Cleverness** - Standardize on one approach per concern
2. **Explicit Over Implicit** - Make dependencies and data flow visible
3. **Layering Principles** - Clear boundaries between presentation, application, domain, and infrastructure
4. **Single Responsibility** - Each class/function has one reason to change
5. **Fail Fast and Explicitly** - Validate at boundaries, return early on errors
6. **Testability First** - Design for dependency injection
7. **Evolutionary Design** - Make decisions reversible and document trade-offs

## References

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) - Detailed implementation roadmap
- [docs/NAMING_CONVENTIONS.md](NAMING_CONVENTIONS.md) - Naming guidelines
- [docs/ERROR_CODES.md](ERROR_CODES.md) - Error code taxonomy
- [docs/ERROR_RESPONSES.md](ERROR_RESPONSES.md) - Error response examples

## Change Log

| Date | ADR | Status | Notes |
|-------|------|--------|-------|
| 2024-02-10 | API Response Pattern | Accepted | Enveloped responses for all endpoints |
| 2024-02-10 | Authentication & Authorization | Accepted | Unified JWT with RBAC |
| 2024-02-10 | Pagination Strategy | Accepted | Cursor-based pagination |
| 2024-02-10 | Error Handling Strategy | Accepted | Structured error response envelope |
| 2024-02-10 | Data Access Pattern | Accepted | Repository Pattern with Unit of Work |
| 2024-02-10 | Transaction Management | Accepted | Explicit transaction decorator |
| 2024-02-10 | Exception Hierarchy | Accepted | Domain exception hierarchy |
| 2024-02-10 | Dependency Injection | Accepted | Factory pattern with FastAPI Depends |
| 2024-02-10 | Naming Conventions | Accepted | Standard naming conventions |
| 2024-02-10 | DateTime Handling | Accepted | ISO 8601 with timezone |
| 2024-02-10 | ID Types | Accepted | UUID v7 for new resources |
