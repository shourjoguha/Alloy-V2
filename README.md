# Alloy - AI Workout Coach

An AI-enabled workout coach that creates adaptive 8-12 week strength/fitness programs and adapts daily sessions based on your preferences, constraints, and recovery signals.

## Features

- **Program Generation**: Create personalized 8-12 week programs based on 3 weighted goals
- **Multiple Split Templates**: Upper/Lower, PPL, Full Body, or custom Hybrid splits
- **Daily Adaptation**: Real-time session adjustments based on constraints and recovery
- **Diversity-Based Scoring**: Multi-dimensional movement scoring (7 scoring dimensions) with progressive constraint relaxation
- **Progress Tracking**: e1RM calculation with multiple formulas (Epley, Brzycki, Lombardi, O'Conner)
- **Pattern Strength Index (PSI)**: Track strength across movement patterns
- **Intelligent Deloading**: Time-based and performance-triggered deload scheduling
- **Interference Management**: Account for recreational activities affecting training
- **Coach Personas**: Customizable tone and programming aggressiveness
- **Movement Variety System**: Prevents exercise duplication and enforces pattern diversity
- **Session Quality KPIs**: Block-specific validation, pattern rotation, muscle coverage tracking
- **Real-time Streaming**: SSE-powered session adaptation with live LLM feedback
- **Advanced Preferences**: Discipline priorities, cardio finishers, and scheduling options
- **Circuit Support**: CrossFit-style circuits with AMRAP, EMOM, and other formats
- **Goals System**: Long-term macro cycles with versioned goals and check-ins
- **External Integrations**: Data lake architecture for Strava, Garmin, Apple Health, WHOOP, Oura
- **Custom Workout Logging**: Log ad-hoc activities and custom workouts with detailed metrics
- **Historic Tracking**: View and manage past programs and sessions
- **Feature Flags**: Gradual rollout system with configurable feature toggles
- **Admin API**: Configuration management and metrics tracking endpoints
- **Two-Factor Authentication**: Enhanced security with TOTP-based 2FA
- **Audit Logging**: Comprehensive audit trail for security and compliance
- **Vector Similarity Search**: pgvector-powered semantic search for movement recommendations
- **Greedy Optimization**: Deterministic O(n log n) algorithm for exercise selection
- **Favorites System**: Save favorite movements and programs for quick access


## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (via SQLAlchemy async engine) with pgvector support
- **LLM**: Ollama (local) with provider-agnostic interface (llama3.2:3b)
- **HTTP Client**: httpx (async)
- **Frontend**: React 19 + TypeScript + Vite + TanStack Router + Tailwind CSS
- **Optimization**: Custom Greedy Optimizer (deterministic O(n log n) algorithm)
- **ML Scoring**: Decision tree scorer with 7 scoring dimensions and progressive relaxation
- **Configuration**: YAML-based scoring config with hot-reload support
- **Feature Flags**: In-memory flag system with gradual rollout strategy
- **Authentication**: JWT with refresh tokens and 2FA support
- **State Management**: Zustand (client) + TanStack Query (server)
- **PWA**: Progressive Web App capabilities with service worker

## Quick Start

### Prerequisites

1. Python 3.11+
2. Ollama installed and running (`ollama serve`)
3. llama3.2:3b model pulled (`ollama pull llama3.2:3b`)
4. PostgreSQL with pgvector extension (Docker recommended)

### Installation

```bash
# Navigate to project directory
cd alloy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run the application (use the dev script for convenience)
./start-dev.sh
```

Or manually start services:

```bash
# Start PostgreSQL with pgvector (Docker)
docker run --name alloy-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=alloy \
  -p 5432:5432 \
  -v alloy-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg16

# Start Ollama (if not running)
ollama serve

# Pull the model (if not already done)
ollama pull llama3.2:3b

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check LLM connection
curl http://localhost:8000/health/llm
```

## Project Structure

```
alloy/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoint routers
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── programs.py    # Program lifecycle
│   │       ├── days.py       # Daily planning & SSE
│   │       ├── logs.py       # Workout logging
│   │       ├── settings.py   # User settings
│   │       ├── circuits.py   # Circuit templates
│   │       ├── activities.py # Activity management
│   │       ├── favorites.py  # Favorites
│   │       ├── admin.py      # Admin operations
│   │       ├── audit.py      # Audit logs
│   │       ├── performance.py # Performance metrics
│   │       ├── errors.py     # Error dashboard
│   │       ├── scoring_config.py # Scoring configuration
│   │       ├── scoring_metrics.py # Scoring metrics
│   │       ├── two_factor.py # 2FA
│   │       ├── health.py     # Health checks
│   │       └── dependencies.py # Dependency injection
│   ├── config/
│   │   ├── settings.py      # Application configuration
│   │   ├── features.py      # Feature flags and rollout management
│   │   ├── activity_distribution.py # Activity distribution logic
│   │   ├── optimization_config.yaml # Unified optimization config
│   │   ├── movement_scoring.yaml # YAML-based scoring configuration
│   │   └── optimization_config_loader.py # Config loader with hot-reload
│   ├── core/
│   │   ├── error_handlers.py # Domain error handling
│   │   ├── exceptions.py     # Custom exceptions
│   │   ├── transactions.py   # Transaction management
│   │   ├── cache.py          # Caching layer
│   │   ├── audit.py          # Audit system
│   │   └── performance.py    # Performance monitoring
│   ├── db/
│   │   ├── database.py      # Database connection
│   │   └── seed.py          # Data seeding
│   ├── llm/
│   │   ├── base.py          # LLM provider interface
│   │   ├── ollama_provider.py  # Ollama implementation
│   │   └── prompts.py       # System prompts for session generation
│   ├── middleware/          # FastAPI middleware
│   │   ├── audit_logging.py # Audit logging
│   │   ├── security.py      # Security headers
│   │   ├── rate_limit.py    # Rate limiting
│   │   ├── request_id.py    # Request ID tracking
│   │   └── tracing.py       # Distributed tracing
│   ├── ml/scoring/          # Diversity-based scoring system
│   │   ├── movement_scorer.py # Decision tree scorer (7 dimensions)
│   │   ├── scoring_metrics.py # Session metrics tracker
│   │   ├── session_quality_kpi.py # Block-specific validation
│   │   ├── variety_kpi.py   # Movement variety KPIs
│   │   ├── muscle_coverage_kpi.py # Muscle coverage tracking
│   │   ├── constants.py     # Centralized constants
│   │   └── config_loader.py # YAML config loader
│   ├── models/
│   │   ├── enums.py         # Enum definitions (42 enum types)
│   │   ├── user.py          # User, UserProfile, UserSettings, etc.
│   │   ├── program.py       # Program, Microcycle, Session, etc.
│   │   ├── movement.py      # Movement, MovementRelationship, etc.
│   │   ├── circuit.py       # CircuitTemplate
│   │   ├── logging.py       # WorkoutLog, SorenessLog, etc.
│   │   ├── audit_log.py     # AuditLog
│   │   ├── favorite.py      # Favorite
│   │   ├── refresh_token.py # RefreshToken
│   │   └── two_factor_auth.py # TwoFactorAuth
│   ├── repositories/        # Data access layer
│   │   ├── base.py          # Repository protocol
│   │   ├── program_repository.py
│   │   ├── session_repository.py
│   │   ├── movement_repository.py
│   │   ├── circuit_repository.py
│   │   └── audit_log_repository.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── program.py
│   │   ├── daily.py
│   │   ├── circuit.py
│   │   ├── settings.py
│   │   ├── logging.py
│   │   ├── pagination.py
│   │   ├── filtering.py
│   │   └── base.py
│   ├── security/
│   │   └── jwt_utils.py     # JWT utilities
│   ├── services/            # Business logic
│   │   ├── program.py       # ProgramService
│   │   ├── session_generator.py # SessionGeneratorService
│   │   ├── adaptation.py    # AdaptationService
│   │   ├── deload.py       # DeloadService
│   │   ├── greedy_optimizer.py # GreedyOptimizationService
│   │   ├── metrics.py       # e1RM and PSI calculations
│   │   ├── time_estimation.py # Session duration estimation
│   │   ├── interference.py # Goal validation and conflict detection
│   │   ├── movement.py      # MovementQueryService, MovementSubstitutionService
│   │   ├── rpe_suggestion_service.py
│   │   ├── two_factor_service.py
│   │   └── audit_service.py
│   └── main.py              # FastAPI app entry point
├── frontend/
│   ├── src/
│   │   ├── api/             # API client layer
│   │   │   ├── client.ts    # HTTP client with auth
│   │   │   ├── programs.ts
│   │   │   ├── circuits.ts
│   │   │   ├── settings.ts
│   │   │   ├── logs.ts
│   │   │   ├── stats.ts
│   │   │   ├── favorites.ts
│   │   │   └── movement-preferences.ts
│   │   ├── components/      # React components
│   │   │   ├── auth/       # Authentication components
│   │   │   ├── layout/     # Layout components
│   │   │   ├── onboarding/ # Onboarding flow
│   │   │   ├── program/    # Program components
│   │   │   ├── circuit/    # Circuit display
│   │   │   ├── settings/   # Settings pages
│   │   │   ├── shared/     # Shared components
│   │   │   ├── ui/         # UI primitives
│   │   │   ├── visual/     # Visualizations
│   │   │   └── wizard/     # Program wizard
│   │   ├── routes/         # TanStack Router routes
│   │   │   ├── __root.tsx  # Root layout
│   │   │   ├── dashboard.tsx
│   │   │   ├── programs.tsx
│   │   │   ├── program.wizard.tsx
│   │   │   ├── log.workout.tsx
│   │   │   ├── settings.tsx
│   │   │   └── ...
│   │   ├── stores/         # Zustand stores
│   │   │   ├── auth-store.ts
│   │   │   └── program-wizard-store.ts
│   │   ├── hooks/          # Custom React hooks
│   │   ├── types/          # TypeScript definitions
│   │   ├── config/         # Frontend config
│   │   ├── styles/         # CSS/Tailwind
│   │   └── main.tsx        # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── alembic/
│   └── versions/          # Database migration files
├── scripts/               # Data ingestion and utility scripts
├── tests/                 # Test suites
│   ├── conftest.py        # Test fixtures
│   ├── test_*.py          # Unit and integration tests
│   └── performance/       # Performance tests
├── docs/                  # Documentation
│   ├── DEVELOPER_ONBOARDING.md
│   ├── ARCHITECTURAL_CHOICES.md
│   ├── WARP.md
│   ├── ERROR_CODES.md
│   ├── PERFORMANCE_TESTING.md
│   └── NOTES.md
├── deployment/            # Deployment configs
├── seed_data/             # Seed data files
├── requirements.txt
├── alembic.ini
├── start-dev.sh
└── README.md
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login with JWT token
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout (revoke refresh token)
- `POST /auth/2fa/enable` - Enable 2FA
- `POST /auth/2fa/disable` - Disable 2FA
- `POST /auth/2fa/verify` - Verify 2FA setup
- `POST /auth/2fa/challenge` - Complete 2FA challenge

### Program Lifecycle
- `POST /programs` - Create new program with LLM-generated sessions
- `GET /programs` - List user programs
- `GET /programs/{id}` - Get program details with sessions
- `GET /programs/{id}/generation-status` - Check program generation status
- `PUT /programs/{id}` - Update program
- `DELETE /programs/{id}` - Delete program
- `POST /programs/{id}/regenerate-sessions` - Regenerate sessions

### Daily Planning
- `GET /days/{date}/plan` - Get daily session plan
- `POST /days/{date}/adapt` - Adapt session with constraints
- `POST /days/{date}/adapt/stream` - Real-time adaptation with SSE streaming

### Logging
- `POST /logs/workouts` - Log workout completion with feedback
- `GET /logs/workouts` - List workout logs
- `POST /logs/custom` - Log custom workout or activity
- `POST /logs/soreness` - Log muscle soreness
- `GET /logs/soreness` - Get soreness logs
- `POST /logs/recovery` - Log recovery signals
- `GET /logs/recovery` - Get recovery signals

### Settings & Configuration
- `GET /settings` - Get user settings
- `PUT /settings` - Update settings
- `GET /settings/profile` - Get user profile with advanced preferences
- `PUT /settings/profile` - Update user profile
- `GET /configs` - List heuristic configurations
- `PUT /configs/{name}/active` - Activate config version

### Movements
- `GET /movements` - List movements with filtering
- `GET /movements/{id}` - Get movement details
- `GET /movements/search` - Vector similarity search
- `POST /movements/preferences` - Set movement preferences

### Circuits
- `GET /circuits` - List circuit templates
- `GET /circuits/{id}` - Get circuit details
- `POST /circuits` - Create circuit template
- `PUT /circuits/{id}` - Update circuit template
- `DELETE /circuits/{id}` - Delete circuit template

### Activities
- `GET /activities` - List activity instances
- `POST /activities` - Log activity
- `GET /activities/definitions` - List activity definitions

### Favorites
- `GET /favorites` - Get user favorites
- `POST /favorites/movements/{movement_id}` - Add movement to favorites
- `DELETE /favorites/movements/{movement_id}` - Remove movement from favorites
- `POST /favorites/programs/{program_id}` - Add program to favorites
- `DELETE /favorites/programs/{program_id}` - Remove program from favorites

### Admin
- `GET /admin/errors` - Get error dashboard
- `GET /admin/errors/summary` - Get error summary
- `GET /admin/audit-logs` - Get audit logs
- `GET /admin/metrics` - Get performance metrics
- `POST /admin/seed` - Seed database

### Diversity Scoring (Admin)
- `GET /scoring/config` - View current scoring configuration
- `POST /scoring/config/reload` - Hot-reload scoring configuration
- `POST /scoring/config/validate` - Validate YAML schema
- `GET /scoring/config/metadata` - Get configuration metadata
- `GET /scoring/config/global` - Get global configuration

### Scoring Metrics (Admin)
- `GET /scoring/metrics/{user_id}` - Get scoring metrics for specific user
- `GET /scoring/metrics/summary` - Aggregate metrics across all users
- `GET /scoring/metrics/success-rate` - Calculate session success rate
- `GET /scoring/metrics/dimension-effectiveness` - Analyze dimension effectiveness

### Health Checks
- `GET /health` - API health check
- `GET /health/llm` - LLM connection check
- `GET /health/database` - Database connection check

## Configuration
Environment variables (or `.env` file):

```env
# LLM Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=1100.0

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/alloy

# App
DEBUG=true
SECRET_KEY=your-secret-key

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Feature Flags (Optional)
APP_FEATURE_USE_DIVERSITY_OPTIMIZER=true
APP_FEATURE_ENABLE_METRICS_LOGGING=true
APP_FEATURE_USE_DIVERSITY_SCORING=true
APP_FEATURE_ENABLE_AUDIT_LOGGING=true
```

## Goals (Ten-Dollar Method)

Select 3 goals and assign weights that sum to 10:
- `strength` - Max force production
- `hypertrophy` - Muscle growth
- `endurance` - Work capacity
- `fat_loss` - Body composition
- `mobility` - Range of motion
- `explosiveness` - Power output
- `speed` - Movement velocity

## Split Templates

- **Upper/Lower**: 4 days/week, alternating upper and lower body
- **PPL**: 6 days/week, Push/Pull/Legs rotation
- **Full Body**: 3 days/week, whole body each session
- **Hybrid**: Custom day-by-day or block composition

## Progression Styles

1. **Single Progression**: Increase weight when hitting rep target
2. **Double Progression**: Increase reps, then weight
3. **Paused Variations**: Add pauses for difficulty
4. **Build to Drop**: Build reps, drop and add weight
5. **Wave Loading**: Undulating intensity across sets

## Movement Variety System
### Pattern Interference Rules
- No same main pattern on consecutive training days
- Maximum 2 uses per pattern per week
- Intelligent pattern substitution (squat → hinge → lunge rotation)
- Prevents back-to-back loading of same movement patterns

### Variety Enforcement
- Intra-session deduplication prevents exercise repetition
- Inter-session variety tracking across the week
- Muscle group fatigue tracking to prevent overload
- Movement history context passed to LLM

## Diversity-Based Scoring System

### 7 Scoring Dimensions
1. **Pattern Alignment** (Priority 1): Match required movement pattern for block
2. **Muscle Coverage** (Priority 2): Target specified muscle groups
3. **Discipline Preference** (Priority 3): Match user discipline priorities (1-5 scale → 0-1 normalized)
4. **Compound Bonus** (Priority 4): Reward compound movements
5. **Specialization** (Priority 5): Target specialization goals
6. **Goal Alignment** (Priority 6): Align with training goals (strength, hypertrophy, etc.)
7. **Time Utilization** (Priority 7): Optimize for target duration

### Progressive Constraint Relaxation
6-step relaxation strategy when constraints cannot be satisfied:
1. **Expand pattern compatibility** - Allow more pattern variations
2. **Include synergist muscles** - Accept movements targeting secondary muscles
3. **Reduce discipline weight** - Lower discipline importance (0.7× multiplier)
4. **Accept isolation movements** - Allow non-compound exercises
5. **Accept generic movements** - Permit lower-tier exercises
6. **Emergency selection** - Minimal constraints for worst-case scenarios

### Goal Modifiers
- **Explosiveness goal**: Olympic movements ×1.5 boost
- **Speed goal**: Plyometric movements ×1.5 boost
- **Calisthenics goal**: Calisthenics movements ×1.5 boost
- **Goal conflicts**: Conflicting goals (e.g., Strength + Endurance) apply weight reduction

### Session Quality KPIs
**Block-Specific Validation**:
- Warmup: 2-5 movements
- Cooldown: 2-5 movements
- Main: 2-5 (strength/hypertrophy), 6-10 (endurance)
- Accessory: 2-4 movements
- Finisher: 1 unit (circuits counted as whole)

**Success Rate Criteria** (all must be met):
1. Structural completeness: warmup + main + (accessory/finisher) + cooldown
2. Movement count: ≥8 (regular/cardio/conditioning), ≤15 (finisher = 1 unit)
3. Time utilization: ±5% of target duration
4. Pattern diversity: Session-type dependent
5. Muscle coverage: No major muscle group missed in microcycle
6. Hard constraint compliance: Equipment, variety, time, user rules

**Variety Tracking**:
- Pattern rotation: No pattern repeats within 2 sessions of SAME TYPE
- Movement diversity: % unique movements in microcycle (threshold: 70%)
- Muscle coverage: 7 major muscle groups tracked (quadriceps, hamstrings, glutes, chest, lats, upper_back, shoulders)

## Session Structure

Sessions have flexible, optional sections stored as JSON:
- **warmup_json** - Always included
- **main_json** - Main lifts or cardio block
- **accessory_json** - Optional accessory work
- **finisher_json** - Optional finisher (conditioning, cardio, or metabolic)
- **cooldown_json** - Always included

Session types determine middle piece structure:
- **Strength/Hypertrophy**: Main lifts + (Accessory XOR Finisher)
- **Cardio-only**: Dedicated cardio block only
- **Conditioning-only**: Circuit-based conditioning (≥5 movements, ≥30 minutes)
- **Mobility**: Extended warmup/cooldown with mobility work

## Frontend Design System

### Color Palette
- **Primary**: Vibrant teal (#06B6D4) for CTAs and progress
- **Secondary**: Deep slate (#1E293B) for backgrounds
- **Accent**: Amber (#F59E0B) for warnings and deload indicators
- **Success**: Emerald (#10B981) for completed sessions and PRs

### Component Library
- Unified button system with hover effects and accessibility
- Card components with type-specific styling
- Form components with real-time validation
- Modal system with smooth animations
- Loading states and skeleton components

### State Management
- **Zustand**: Client-side state (auth, wizard, UI preferences)
- **TanStack Query**: Server state management (programs, settings, logs)
- **TanStack Router**: File-based routing with type safety

## Database Schema

The database uses PostgreSQL with SQLAlchemy ORM and pgvector for vector similarity search. The schema consists of **45 tables** organized into the following categories:

### User Management (8 tables)
- **users** - User profiles, settings, and personas with role-based access (USER, ADMIN, SUPER_ADMIN)
- **user_settings** - User preferences (e1RM formula, units)
- **user_profiles** - Extended user profile with discipline preferences, equipment, and scheduling
- **user_movement_rules** - Movement preferences (HARD_NO, HARD_YES, PREFERRED)
- **user_enjoyable_activities** - Recreational activities for recommendations
- **user_biometrics_history** - Biometric tracking (weight, body fat, HRV, sleep)
- **user_skills** - Discipline skill levels and experience
- **user_injuries** - User injury tracking with severity

### Program Planning (11 tables)
- **programs** - 8-12 week programs with goals, splits, and progression
- **program_disciplines** - Junction table for program-discipline relationships
- **microcycles** - 7-14 day blocks within programs with generation status tracking
- **sessions** - Daily workout plans with JSON content sections and time constraints
- **session_exercises** - Individual exercises within sessions with sets, reps, RPE
- **pattern_recovery_states** - Recovery tracking for movement patterns
- **macro_cycles** - Long-term (12-month) planning periods
- **goals** - Versioned goals with check-ins (PERFORMANCE, BODY_COMPOSITION, SKILL, etc.)
- **goal_checkins** - Goal progress tracking
- **disciplines** - Discipline definitions (POWERLIFTING, OLYMPIC, BODYBUILDING, etc.)
- **activity_definitions** - Activity type definitions with default metrics

### Movement Library (11 tables)
- **movements** - Exercise library with vector embeddings for semantic search
- **movement_relationships** - Progression, regression, and variation relationships
- **muscles** - Muscle definitions with stimulus/fatigue coefficients
- **movement_muscle_map** - Movement-to-muscle mappings with roles (PRIMARY, SECONDARY, STABILIZER)
- **equipment** - Equipment definitions
- **movement_equipment** - Movement-equipment junction table
- **tags** - Tag definitions
- **movement_tags** - Movement-tag junction table
- **movement_disciplines** - Movement-discipline junction table
- **movement_coaching_cues** - Coaching cues for movements

### Circuit Templates (1 table)
- **circuit_templates** - CrossFit-style circuits (AMRAP, EMOM, LADDER, TABATA, etc.)

### Logging & Tracking (6 tables)
- **workout_logs** - Completed workouts with performance data and feedback
- **top_set_logs** - Top set tracking with e1RM calculations
- **pattern_exposures** - Pattern-based exposure tracking for PSI
- **soreness_logs** - Muscle soreness tracking
- **recovery_signals** - Recovery data from various sources (MANUAL, GARMIN, APPLE, WHOOP, OURA)
- **muscle_recovery_states** - Muscle-specific recovery levels

### Authentication & Security (3 tables)
- **two_factor_auths** - TOTP-based 2FA secrets and backup codes
- **refresh_tokens** - JWT refresh tokens with device tracking
- **audit_logs** - Comprehensive audit trail for security events

### Configuration & Conversations (3 tables)
- **heuristic_configs** - Configuration versions with active status
- **conversation_threads** - AI conversation context management
- **conversation_turns** - Individual conversation turns

### External Integrations (4 tables)
- **external_provider_accounts** - OAuth credentials for external providers (STRAVA, GARMIN, APPLE_HEALTH, WHOOP, OURA)
- **external_ingestion_runs** - Ingestion run tracking
- **external_activity_records** - Imported activity data
- **external_metric_streams** - Raw metric stream data

### Activity Tracking (2 tables)
- **activity_instances** - Activity execution records (PLANNED, MANUAL, PROVIDER)
- **activity_instance_links** - Links between activities, external records, and workout logs
- **user_fatigue_state** - Muscle-specific fatigue tracking

### Favorites (1 table)
- **favorites** - User favorites for movements and programs

### Key Features
- **Vector Embeddings**: pgvector support for semantic search on movements (768-dimensional vectors)
- **JSONB Columns**: Flexible storage for preferences, metrics, and nested data
- **Read Replica Support**: Primary database with optional read replicas for scalability
- **Async SQLAlchemy**: Full async support for database operations
- **Comprehensive Indexing**: Strategic indexes on frequently queried columns
- **Enum Types**: PostgreSQL enums for type safety on categorical data (42 enum types)

For complete schema documentation, see [DATABASE_OVERVIEW.md](DATABASE_OVERVIEW.md).

## e1RM Calculation

**Supported formulas** (configurable per user):
- `epley`: weight × (1 + reps/30)
- `brzycki`: weight × 36 / (37 - reps)
- `lombardi`: weight × reps^0.10
- `oconner`: weight × (1 + reps/40)

## Testing
```bash
# Run backend tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test suites
pytest tests/test_diversity_scoring.py
pytest tests/test_optimization_v2_integration.py
pytest tests/test_muscle_coverage_kpi.py
pytest tests/test_features.py

# Run frontend tests
cd frontend && npm test

# Performance testing with Locust
pip install locust
locust -f tests/performance_test_locust.py
```

### Test Coverage
- **Unit Tests**: 57 tests for diversity scoring system
- **Integration Tests**: 24 tests for v2 optimization
- **KPI Tests**: 21 tests for muscle coverage
- **Feature Flags Tests**: 33 tests for feature flag system
- **Total**: 135+ tests covering core functionality

See [docs/PERFORMANCE_TESTING.md](docs/PERFORMANCE_TESTING.md) for detailed performance testing guidance.

## Development Notes
For detailed architecture decisions, development patterns, and implementation notes, see:
- [docs/NOTES.md](docs/NOTES.md) - Architecture decisions and design patterns
- [docs/DEVELOPER_ONBOARDING.md](docs/DEVELOPER_ONBOARDING.md) - New developer guide
- [docs/ARCHITECTURAL_CHOICES.md](docs/ARCHITECTURAL_CHOICES.md) - Major architectural decisions
- [docs/WARP.md](docs/WARP.md) - WARP (warp.dev) development guide
- [docs/ERROR_CODES.md](docs/ERROR_CODES.md) - Error code taxonomy
- [Agents.md](Agents.md) - Agent capabilities and collaboration patterns
- [DATABASE_OVERVIEW.md](DATABASE_OVERVIEW.md) - Complete database schema documentation

## Roadmap & Future Enhancements

### Recently Completed (2026-02)
- ✅ **Diversity-Based Scoring System**: Multi-dimensional movement scoring with 7 scoring dimensions
- ✅ **Progressive Constraint Relaxation**: 6-step relaxation strategy for optimization
- ✅ **Session Quality KPIs**: Block-specific validation, pattern rotation, muscle coverage tracking
- ✅ **Feature Flags System**: Gradual rollout with configurable feature toggles
- ✅ **Admin API Endpoints**: Configuration management and metrics tracking
- ✅ **Comprehensive Testing**: 135+ unit and integration tests
- ✅ **Greedy Optimizer**: Deterministic O(n log n) algorithm replacing OR-Tools
- ✅ **Vector Similarity Search**: pgvector-powered semantic search for movements
- ✅ **Audit Logging**: Comprehensive audit trail with middleware
- ✅ **Two-Factor Authentication**: TOTP-based 2FA support
- ✅ **Favorites System**: Save favorite movements and programs
- ✅ **Code Refactoring**: Eliminated 200+ lines of duplicate code, centralized constants

### Current Development
- Ensemble coach architecture with multiple LLM providers
- Circuit metrics normalization for optimizer integration
- Goal-based weekly time distribution
- External activity ingestion (Strava, Garmin, Apple Health)
- Biometrics tracking and user profiles

### Planned Features
- [ ] Mobile native app (React Native)
- [ ] Cloud LLM providers (OpenAI, Anthropic)
- [ ] Advanced analytics and progress visualization
- [ ] Social features (share programs, compete with friends)
- [ ] Workout video analysis with computer vision
- [ ] Real-time coaching feedback during workouts
- [ ] AI-powered exercise form detection
- [ ] Nutrition tracking and meal planning
- [ ] Wearable device integrations (WHOOP, Oura, Garmin)

## License

MIT
