# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Quick Start

### Backend (FastAPI)
```bash
# Navigate to project directory
cd Gainsly

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn app.main:app --reload

# Run tests
pytest

# Run tests with coverage
pytest --cov=app

# Lint and format
ruff check .
ruff format .
black .
```

### Frontend (React + Vite)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint
npm run lint
```

### LLM Prerequisites
The application requires Ollama to be running with the llama3.1:8b model:
```bash
# Start Ollama service (if not already running)
ollama serve

# Pull the required model
ollama pull llama3.1:8b
```

## High-Level Architecture

### Core Components

#### Backend Architecture
- **FastAPI**: Asynchronous Python framework serving the API
- **SQLAlchemy ORM**: Database models with async support
- **SQLite**: Default database (designed for Postgres migration)
- **Ollama**: Local LLM provider for program generation

#### Database Model Hierarchy
```
User -> Programs -> Microcycles -> Sessions -> SessionExercises
      -> UserSettings
      -> WorkoutLogs -> TopSetLogs
      -> SorenessLogs
      -> RecoverySignals
```

#### Key Services
- **Metrics Service** (`app/services/metrics.py`): e1RM calculations and Pattern Strength Index (PSI)
- **Time Estimation Service** (`app/services/time_estimation.py`): Session duration predictions
- **Program Service** (`app/services/program.py`): Program generation with pattern interference rules
- **Session Generator** (`app/services/session_generator.py`): LLM-powered session creation
- **LLM Integration** (`app/llm/`): Abstraction layer for LLM providers (currently Ollama)

#### LLM Integration
The application uses a provider-agnostic LLM interface in `app/llm/base.py` with the Ollama implementation in `app/llm/ollama_provider.py`. This enables future expansion to cloud providers (OpenAI, Anthropic).

#### Program Generation
The ten-dollar goal system enables users to select 3 goals with weights summing to 10:
- `strength`, `hypertrophy`, `endurance`, `fat_loss`, `mobility`, `explosiveness`, `speed`

#### Session Structure
Sessions have flexible, optional sections stored as JSON:
- warmup_json, main_json, accessory_json, finisher_json, cooldown_json
- This allows for varied session types (cardio, strength, mobility)

#### Progress Tracking
- **e1RM Calculations**: Multiple formulas available (Epley, Brzycki, Lombardi, O'Conner)
- **Pattern Strength Index (PSI)**: Tracks strength across movement patterns
- **Top Set Logging**: Key performance indicators for progression

#### Movement Variety System
- **Pattern Interference Rules**: Prevents same movement patterns on consecutive days
- **Intra-Session Deduplication**: No exercise appears twice in same session
- **Inter-Session Variety**: Tracks movement usage across the week
- **Intelligent Replacement**: Preserves session philosophy when removing duplicates

### Testing Strategy
- Tests use in-memory SQLite with async sessions (defined in `conftest.py`)
- Fixtures provide test data for users, movements, programs, and logs
- Service tests focus on business logic isolation
- Performance testing with Locust framework

### Frontend Architecture
- **React 19** with TypeScript
- **TanStack Router** for routing
- **React Query** for server state management
- **Tailwind CSS** for styling with dark neon theme
- **Zustand** for client-side state management
- **React Hook Form** for form handling

### Data Flow
1. User creates a program with goals and split template
2. Microcycles are generated (7-10 day blocks)
3. Sessions are planned within microcycles with LLM-generated exercises
4. Daily adaptation adjusts sessions based on constraints and recovery
5. Workout logs drive progression and PSI calculations

## Development Notes

### Database Configuration
- Default uses SQLite at `./workout_coach.db`
- Database initialization happens automatically via the app lifespan in `main.py`
- For testing, an in-memory SQLite database is used with automatic schema creation

### LLM Health Check
The application includes health check endpoints:
- `/health`: Basic application status
- `/health/llm`: LLM provider connectivity status

### Session Adaptation
The system supports real-time session adaptation using SSE (Server-Sent Events) when users provide constraints like:
- Time limitations
- Equipment availability
- Recovery status

### Pattern Interference System
The movement variety system prevents:
- Same exercise appearing multiple times in one session
- Same movement patterns on consecutive training days
- Excessive muscle group fatigue through intelligent tracking
- Poor recovery management through pattern rotation

### Key Directories
- `app/models/`: Database models and enums
- `app/api/routes/`: API endpoint definitions
- `app/services/`: Business logic and calculations
- `app/llm/`: LLM provider abstractions and prompts
- `seed_data/`: Default data for movement library and configurations
- `tests/`: Test suite with fixtures
- `frontend/src/`: React application with component library

