# Naming Conventions

## API Endpoint Naming

### Resource-Based URLs
- Use plural nouns for collections: `/api/programs`, `/api/movements`, `/api/circuits`
- Use singular nouns for single resource: `/api/programs/{program_id}`, `/api/movements/{movement_id}`
- Use kebab-case for multi-word resources: `/api/circuit-templates`

### HTTP Methods
- `GET` - Retrieve resources
- `POST` - Create new resources
- `PUT` - Replace entire resource
- `PATCH` - Partial update of resource
- `DELETE` - Remove resource

### Query Parameters
- Use snake_case: `?user_id=123&is_active=true`
- Pagination: `?cursor=xxx&limit=20&direction=next`
- Filtering: Use field names directly: `?status=active&created_after=2024-01-01`
- Sorting: `?sort=created_at&order=desc`

## Schema Naming

### Request/Response Models
- Use PascalCase for class names: `ProgramCreate`, `ProgramResponse`, `PaginationParams`
- Use snake_case for field names: `user_id`, `program_name`, `created_at`
- Suffix request models with `Create`, `Update`, or action: `ProgramCreate`, `ProgramUpdate`
- Suffix response models with `Response` or omit for simple returns: `ProgramResponse`, `ProgramList`

### Pydantic Models
- Base classes in `schemas/base.py`: `ResponseMeta`, `APIError`, `APIResponse`
- Domain models: Use domain entity name: `Program`, `Movement`, `Circuit`
- Generic types: Use `T` for generic type variables

## Service Naming

### Class Names
- Use PascalCase with entity name + `Service`: `ProgramService`, `MovementService`, `CircuitService`
- Base class: `BaseService`

### Method Names
- CRUD operations: `get`, `list`, `create`, `update`, `delete`
- Business logic actions: Use descriptive verbs: `generate_program`, `validate_rules`, `optimize_session`
- Private helpers: Prefix with underscore: `_get_or_404`, `_calculate_score`

## Repository Naming

### Class Names
- Use PascalCase with entity name + `Repository`: `ProgramRepository`, `MovementRepository`
- Base protocol: `Repository` (generic protocol)

### Method Names
- Standard CRUD: `get`, `list`, `create`, `update`, `delete`
- Query methods: Use descriptive names: `find_by_user`, `search_by_name`, `count_active`

## Variable Naming

### Python Variables
- Use snake_case: `user_id`, `program_name`, `is_active`
- Boolean variables: Prefix with `is_`, `has_`, `can_`: `is_active`, `has_permission`, `can_edit`
- Constants: UPPER_SNAKE_CASE: `MAX_SESSION_DURATION`, `DEFAULT_PAGE_SIZE`

### Database Columns
- Use snake_case: `user_id`, `program_name`, `created_at`
- Foreign keys: `{entity}_id`: `user_id`, `program_id`, `movement_id`
- Timestamps: `{action}_at`: `created_at`, `updated_at`, `deleted_at`

## Enum Naming

### Class Names
- Use PascalCase: `UserRole`, `Goal`, `SplitTemplate`
- SQL enums: Use `SQLEnum` for database compatibility

### Values
- Use UPPER_SNAKE_CASE: `USER`, `ADMIN`, `SUPER_ADMIN`
- Or use descriptive names: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`

## Anti-Patterns

### Avoid
- ❌ CamelCase in Python: `programName`, `userId`
- ❌ Hungarian notation: `strUserName`, `iCount`
- ❌ Abbreviations unless common: `prog`, `usr`, `mov`
- ❌ Inconsistent naming: Mix `user_id` and `userId` in same module

### Prefer
- ✅ Descriptive names: `max_session_duration` instead of `msd`
- ✅ Full words: `program` instead of `prog`, `movement` instead of `mov`
- ✅ Consistent casing: Always `user_id`, never `userId`
