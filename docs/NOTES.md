# ShowMeGains Development Notes

## Architecture & Design Decisions

### 1. Heuristics Read-Only in MVP
**Decision**: Heuristic configs are read-only endpoints (`GET /settings/heuristics` only)

**Rationale**:
- Heuristics drive core algorithm logic (10 pre-seeded config sets)
- Used for goal-dose mapping, CNS thresholds, interference rules, deload triggers
- Write access would allow users to break system invariants
- Versioned model (`name`, `version`, `active`) supports future admin panel

**Future**: POST/PUT/DELETE endpoints after adding admin auth layer

---

### 2. Type Shadowing Pattern
**Problem**: Python reserved words conflict with schema field names (e.g., `date` type imported vs `date` field)

**Solution**: Field name aliases in schemas
- `date` → `log_date`, `plan_date`, `session_date`
- `date` → `session_date` in SessionResponse
- `date` → `micro_start_date` in MicrocycleResponse

**Pattern established**: When field name matches imported type, suffix with semantic context

---

### 3. SSE Streaming vs WebSocket
**Decision**: Use Server-Sent Events (SSE) instead of WebSocket for adaptation chat

**Rationale**:
- Simpler to implement with FastAPI
- No bidirectional complexity needed for chat flow
- REST + SSE cleaner than stateful WebSocket
- Stored conversation threads provide audit trail

**Endpoints**:
- `POST /days/{date}/adapt` - Non-streaming (full response)
- `POST /days/{date}/adapt/stream` - SSE streaming

---

### 4. User Authorization Pattern
**Current (MVP)**: Hardcoded `default_user_id = 1`

**Pattern**: Every endpoint validates with dependency injection:
```python
def get_current_user_id() -> int:
    return settings.default_user_id

# Then use: @router.post("...") async def endpoint(..., user_id: int = Depends(get_current_user_id))
```

**Future**: Replace with JWT token validation using same dependency

---

### 5. Database Session Management
**Pattern**: Async SQLAlchemy with aiosqlite (SQLite)

**Key decisions**:
- FastAPI `get_db` dependency injects per-request sessions
- `async with` not used; SQLAlchemy handles context
- No session pooling needed for MVP SQLite backend
- Greenlet dependency required for async sync ops

---

### 6. Movement Rules Flexibility
**Supported rule types**:
- `exclude` - Don't include this movement in programs
- `substitute` - Replace with this alternative movement
- `prefer` - Prioritize this movement (future)

**Pattern**: Rules include semantic context (reason field) for audit trail

---

## Movement Variety & Pattern Interference System

### Core Enhancement Features
1. **Intra-Session Deduplication**: Prevents same exercise appearing multiple times within a session
2. **Inter-Session Variety Enforcement**: Improves movement variety across the week using movement group tracking
3. **Intelligent Replacement System**: Preserves session philosophy by replacing removed exercises with muscle-group appropriate alternatives
4. **Pattern Interference Rules**: Enforces movement pattern diversity for main lifts across the microcycle

### Pattern Interference Rules
- **No same main pattern on consecutive training days** (Day 5 squat → Day 6 hinge)
- **No same main pattern within 2 days** (Day 3 squat → Day 5 hinge, not squat)
- **Maximum 2 uses per pattern per week** (squat max 2x in 7 days)
- **Pattern priority hierarchy**: squat → hinge → lunge for lower body

### Pattern Alternatives Configuration
```python
pattern_alternatives = {
    "squat": ["hinge", "lunge"],           # Knee-dominant → hip-dominant
    "hinge": ["squat", "lunge"],           # Hip-dominant → knee-dominant  
    "lunge": ["squat", "hinge"],           # Unilateral → bilateral
    "horizontal_push": ["vertical_push"],   # Horizontal → vertical plane
    "vertical_pull": ["horizontal_pull"],   # Vertical → horizontal plane
}
```

### Implementation Files
- **`app/services/program.py`**: Added pattern interference detection and resolution
- **`app/llm/prompts.py`**: Enhanced prompts with pattern focus context and critical pattern rules

---

## Frontend Implementation Strategy

### Design System
- **Color System**: Vibrant teal primary (#06B6D4), deep slate backgrounds (#1E293B), amber warnings (#F59E0B)
- **Typography**: Inter font family with clear hierarchy (H1: 32px, H2: 24px, H3: 18px, Body: 16px)
- **Button System**: Unified 40px height, 8px border-radius, 200ms transitions with hover effects
- **Accessibility**: WCAG AA compliant contrast ratios, focus indicators, semantic HTML

### Tech Stack
- **Framework**: React 19 + TypeScript + Vite
- **Routing**: TanStack Router (type-safe, modern)
- **State**: TanStack Query (server state) + Zustand (UI state)
- **Forms**: React Hook Form + Zod validation
- **Styling**: Tailwind CSS with custom design tokens
- **Testing**: Vitest + React Testing Library + MSW

### Implementation Phases
1. **Foundation** (Week 1): Project setup, component library, layout, API client
2. **Core Features** (Week 2): Onboarding, daily plan, session adaptation with SSE streaming, workout logging
3. **Polish** (Week 3): Settings, program history, error handling, performance optimization
4. **Mobile** (Week 4): Responsive design, mobile refinements, documentation

---

## Program Creation Flow Implementation

### Current State Analysis
- Backend creates Program → Microcycles → Sessions (empty shells)
- LLM infrastructure exists but not integrated into program creation
- Frontend wizard collects preferences but no program display page exists
- Dashboard shows hardcoded data instead of real API data

### Implementation Strategy
1. **Session Generation Service**: Create `app/services/session_generator.py` to populate sessions with exercises using Ollama
2. **Integration**: Modify `program_service.create_program()` to call session generator after creating session shells
3. **Program Detail Route**: Create `/program/$id` route to display program with sessions
4. **Dashboard Connection**: Replace hardcoded data with real API data
5. **Navigation Flow**: Redirect post-creation to program page instead of dashboard

### Session Generation Approach
- **Synchronous generation** for MVP (30-60s program creation but complete program)
- Uses `SESSION_PLAN_SCHEMA` for structured JSON output
- System prompt includes goals, session type, movement library context, progression style
- Generates warmup, main, accessory, finisher (optional), cooldown blocks

---

## API Endpoint Pattern

All endpoints follow this structure:
```python
@router.post("/{resource_id}/action", response_model=ResponseSchema)
async def action(
    resource_id: int,
    request: RequestSchema,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    # Verify resource ownership
    # Query related data
    # Business logic
    # Commit and return response
```

---

## LLM Integration

### Provider Interface
Located in `app/llm/base.py`:
- Abstract `LLMProvider` class
- `Message`, `LLMResponse`, `StreamChunk` data classes
- `PromptBuilder` for constructing system prompts

### Ollama Provider
Located in `app/llm/ollama_provider.py`:
- Implements `/api/chat` endpoint calls
- Enforces JSON schema on structured responses
- Supports streaming via `chat_stream()` generator
- Health check via `/api/tags`

### Schema Enforcement
Uses Ollama's `format.schema` parameter:
```python
{
    "type": "object",
    "properties": {
        "adapted_plan": {...},
        "reasoning": {"type": "string"},
        ...
    }
}
```

---

## e1RM Calculation
**Supported formulas** (configurable per user):
- `epley`: weight × (1 + reps/30)
- `brzycki`: weight × 36 / (37 - reps)
- `lombardi`: weight × reps^0.10
- `oconner`: weight × (1 + reps/40)

**Located in**: `app/services/metrics.py`

---

## Testing Strategy (TBD)

**Unit tests**:
- Metrics calculations (e1RM, PSI)
- Schema validation
- Enum mapping

**Integration tests**:
- Full endpoint flows with mock LLM
- Database session lifecycle
- Authorization checks

**Mock LLM provider**: Create for testing without Ollama

---

## Known Limitations

1. **No authentication** - MVP uses hardcoded user_id
2. **No update endpoints** - Movement rules/activities are create-only
3. **Single user** - No multi-tenant support
4. **SQLite backend** - No production scaling
5. **Heuristics immutable** - No user tuning
6. **No pagination defaults** - Clients must specify limits

---

## Common Patterns

### Error Handling
```python
if not resource or resource.user_id != user_id:
    raise HTTPException(status_code=404, detail="Not found")
```

### Enum Handling
```python
from app.models.enums import Goal
program.goal_1 = Goal.STRENGTH
# Value stored as string in DB, loaded as enum
```

### JSON Storage
```python
# Session sections stored as JSON
session.main_json = [{"movement": "squat", ...}]
```

---

## File Structure Reference

```
app/
├── api/routes/
│   ├── days.py          # Daily planning + adaptation
│   ├── logs.py          # Workout logging
│   ├── programs.py      # Program CRUD
│   └── settings.py      # User settings + config
├── config/
│   └── settings.py      # App configuration (Pydantic BaseSettings)
├── db/
│   ├── database.py      # SQLAlchemy setup
│   └── seed.py          # Database initialization
├── llm/
│   ├── base.py          # Provider interface
│   └── ollama_provider.py # Ollama implementation
├── models/
│   ├── enums.py         # All enum definitions
│   ├── movement.py      # Movement repository
│   ├── user.py          # User + settings models
│   ├── program.py       # Program + session models
│   ├── logging.py       # Workout log + recovery models
│   └── config.py        # Heuristics + conversation models
├── schemas/             # Pydantic request/response models
├── services/            # Business logic (metrics, time estimation)
└── main.py              # FastAPI app entry point
```

---

## Next Implementation Phase

1. **ProgramService** - Program generation logic
   - Distribute goals across microcycles
   - Generate session structures per split template
   - Apply progression style rules

2. **AdaptationService** - Session adaptation logic
   - Parse constraints
   - Apply interference rules
   - Generate alternative suggestions

3. **DeloadService** - Deload scheduling
   - Track microcycle history
   - Monitor PSI trends
   - Trigger time-based or performance-based deloads

4. **Testing** - Unit + integration test suite
   - Mock LLM provider
   - Database fixtures
   - End-to-end flows

---

## Environment Setup (Local Development)

```bash
# Create and activate venv
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Ollama (separate terminal)
ollama serve

# Run app
uvicorn app.main:app --reload

# Seed database (runs automatically on startup)
# Or manually: python -m app.db.seed
```

**Required Ollama model**:
```bash
ollama pull llama3.1:8b
```

---

## Session Tracking

See `SESSION_LOG.md` for detailed progress notes with timestamp headers for each development session (defined as ≤45 min interruption).

