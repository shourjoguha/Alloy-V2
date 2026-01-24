# Component Interaction Map

## Overview
This document maps the dependencies and event flows between frontend components, state stores, API services, and backend endpoints. It provides a comprehensive view of how data flows through the Gainsly application from user interactions to database persistence.

## Table of Contents
1. [Dependency Matrix](#dependency-matrix)
2. [Event Flows](#event-flows)
3. [SSE Streaming Flow](#sse-streaming-flow)
4. [State Synchronization](#state-synchronization)
5. [Cross-References](#cross-references)

---

## Dependency Matrix

### Frontend Component Dependencies

| Component | State Stores | API Hooks | UI Components | Backend Endpoints |
|-----------|--------------|-----------|---------------|-------------------|
| **Dashboard** | `useUIStore` (activeProgramId) | `usePrograms`, `useProgram`, `useDashboardStats` | `SessionCard`, `Button`, `Card` | GET /api/programs, GET /api/programs/{id}, GET /api/stats/dashboard |
| **ProgramWizard** | `useProgramWizardStore`, `useUIStore` (wizardStep) | `useCreateProgram` | All wizard step components, `WizardContainer` | POST /api/programs |
| **GoalsStep** | `useProgramWizardStore` (goals) | - | `Button`, `Card` | - |
| **SplitStep** | `useProgramWizardStore` (daysPerWeek, maxDuration, splitPreference) | - | `Button`, `Card` | - |
| **DisciplinesStep** | `useProgramWizardStore` (disciplines) | - | `Button`, `Card` | - |
| **ProgressionStep** | `useProgramWizardStore` (progressionStyle) | - | `Button`, `Card` | - |
| **MovementsStep** | `useProgramWizardStore` (movementRules) | - | `Button`, `Card` | - |
| **ActivitiesStep** | `useProgramWizardStore` (enjoyableActivities) | - | `Button`, `Card` | - |
| **CoachStep** | `useProgramWizardStore` (communicationStyle, pushIntensity) | - | `Button`, `Card` | - |
| **ProgramDetail** | `useUIStore` (activeProgramId) | `useProgram`, `useDeleteProgram` | `SessionCard`, `Button`, `Card` | GET /api/programs/{id}, DELETE /api/programs/{id} |
| **LogWorkout** | `useUIStore` (activeWorkoutSessionId) | `useLogWorkout`, `useLogTopSet` | `Button`, `Card`, `Spinner` | POST /api/logs/custom, POST /api/logs/top-set |
| **LogSoreness** | - | `useLogSoreness`, `useRecoveryState` | `SorenessTracker`, `HumanBodyMap`, `Button` | POST /api/logs/soreness, GET /api/logs/recovery-state |
| **Settings** | `useUIStore` (toasts) | `useUserProfile`, `useUpdateProfile` | `ProfileTab`, `ProgramsTab`, `FavoritesTab`, `Tabs` | GET /api/settings/profile, PUT /api/settings/profile |
| **ProfileTab** | - | `useUserProfile`, `useUpdateProfile`, `useMovementRules`, `useEnjoyableActivities` | `Button`, `Card` | GET/PUT /api/settings/profile, GET/POST/DELETE /api/settings/movement-rules, GET/POST /api/settings/enjoyable-activities |
| **BottomNav** | - | - | - | - |
| **AppShell** | `useUIStore` (isMenuOpen, theme) | - | `Header`, `BottomNav`, `BurgerMenu`, `ToastContainer` | - |

### State Store Dependencies

| State Store | Dependencies | Consumers |
|-------------|--------------|------------|
| **useUIStore** | Zustand, zustand/middleware (persist) | `AppShell`, `BottomNav`, `BurgerMenu`, `Dashboard`, `ProgramWizard`, `Settings` |
| **useProgramWizardStore** | Zustand, zustand/middleware (persist) | All wizard step components, `WizardContainer`, `program.wizard.tsx` |

### API Hook Dependencies

| API Hook | API Client | Backend Service | State Store Updates |
|----------|------------|-----------------|---------------------|
| **usePrograms** | `programsApi.list` | ProgramService | Query invalidation on mutations |
| **useProgram** | `programsApi.getById` | ProgramService | - |
| **useCreateProgram** | `programsApi.create` | ProgramService | Invalidates `['programs']` query |
| **useDeleteProgram** | `programsApi.delete` | ProgramService | Invalidates `['programs']` query |
| **useLogWorkout** | `logsApi.createCustom` | LogService | Invalidates `['logs']`, `['stats']` queries |
| **useLogTopSet** | `logsApi.logTopSet` | LogService | Invalidates `['logs']`, `['stats']` queries |
| **useLogSoreness** | `logsApi.logSoreness` | LogService | Invalidates `['recovery-state']` query |
| **useRecoveryState** | `logsApi.getRecoveryState` | LogService | - |
| **useUserProfile** | `settingsApi.getProfile` | SettingsService | - |
| **useUpdateProfile** | `settingsApi.updateProfile` | SettingsService | Invalidates `['profile']` query |
| **useDashboardStats** | `statsApi.getDashboard` | StatsService | - |

---

## Event Flows

### Program Creation Flow

```mermaid
sequenceDiagram
    participant User
    participant ProgramWizard
    participant WizardStore
    participant WizardSteps
    participant API
    participant Backend
    participant QueryClient
    
    User->>ProgramWizard: Start new program
    ProgramWizard->>WizardStore: reset()
    
    User->>WizardSteps: Goals (strength, hypertrophy, endurance)
    WizardSteps->>WizardStore: setGoals([strength: 0.8, hypertrophy: 0.6])
    
    User->>WizardSteps: Split (5 days, 60 min, Full Body)
    WizardSteps->>WizardStore: setDaysPerWeek(5), setMaxDuration(60), setSplitPreference('full_body')
    
    User->>WizardSteps: Disciplines (bodybuilding: 0.7, powerlifting: 0.3)
    WizardSteps->>WizardStore: setDisciplines([{bodybuilding: 0.7}, {powerlifting: 0.3}])
    
    User->>WizardSteps: Progression (linear)
    WizardSteps->>WizardStore: setProgressionStyle('linear')
    
    User->>WizardSteps: Movements (restrict injured shoulder)
    WizardSteps->>WizardStore: addMovementRule({movement_id: 123, restriction: 'avoid'})
    
    User->>WizardSteps: Activities (enjoy: running, hiking)
    WizardSteps->>WizardStore: setEnjoyableActivities([{type: 'running'}, {type: 'hiking'}])
    
    User->>WizardSteps: Coach persona (encouraging, push: 3)
    WizardSteps->>WizardStore: setCommunicationStyle('encouraging'), setPushIntensity(3)
    
    User->>ProgramWizard: Create program
    ProgramWizard->>WizardStore: getState()
    WizardStore-->>ProgramWizard: Return program data
    
    ProgramWizard->>API: POST /api/programs
    API->>Backend: Create program with microcycle
    Backend-->>API: ProgramResponse
    API-->>ProgramWizard: Return program
    
    ProgramWizard->>QueryClient: invalidateQueries(['programs'])
    QueryClient-->>WizardSteps: Refetch program list
    
    ProgramWizard->>User: Navigate to program detail
```

**Key Events:**
- `setGoals()`: Updates wizard store state
- `setDaysPerWeek()`: Updates wizard store state
- `setSplitPreference()`: Updates wizard store state
- `addMovementRule()`: Adds movement restriction to wizard store
- `createProgram.mutateAsync()`: Triggers API call
- `queryClient.invalidateQueries(['programs'])`: Refreshes program list

---

### Workout Logging Flow

```mermaid
sequenceDiagram
    participant User
    participant LogWorkout
    participant UIStore
    participant API
    participant Backend
    participant QueryClient
    
    User->>LogWorkout: Log custom workout
    LogWorkout->>User: Input exercises, sets, reps, weight
    
    User->>LogWorkout: Submit workout
    LogWorkout->>UIStore: setActiveWorkoutSessionId(sessionId)
    
    LogWorkout->>API: POST /api/logs/custom
    Note over API: Body: {exercises: [{id, sets, reps, weight, rpe}]}
    
    API->>Backend: Log workout and calculate e1RM
    Backend->>Backend: calculate_e1rm(weight, reps)
    Backend->>Backend: Update workout_logs table
    Backend->>Backend: Update user_stats table
    Backend-->>API: WorkoutLogResponse
    
    API-->>LogWorkout: Return logged workout
    
    LogWorkout->>QueryClient: invalidateQueries(['logs'])
    LogWorkout->>QueryClient: invalidateQueries(['stats'])
    QueryClient-->>LogWorkout: Refresh logs and stats
    
    LogWorkout->>User: Display success toast
    LogWorkout->>UIStore: addToast({type: 'success', message: 'Workout logged!'})
```

**Key Events:**
- `setActiveWorkoutSessionId()`: Sets active workout context
- `logWorkout.mutateAsync()`: Triggers API call
- `calculate_e1rm()`: Backend algorithm for estimated 1RM
- `invalidateQueries(['logs'])`: Refreshes workout history
- `invalidateQueries(['stats'])`: Refreshes dashboard statistics
- `addToast()`: Displays success notification

---

### Soreness Logging & Recovery State Flow

```mermaid
sequenceDiagram
    participant User
    participant LogSoreness
    participant SorenessTracker
    participant API
    participant Backend
    participant QueryClient
    
    User->>LogSoreness: Log soreness
    SorenessTracker->>User: Display body map
    
    User->>SorenessTracker: Select muscle groups (shoulders: 4/10, quads: 2/10)
    SorenessTracker->>SorenessTracker: Highlight selected muscles
    
    User->>LogSoreness: Submit soreness
    LogSoreness->>API: POST /api/logs/soreness
    Note over API: Body: [{muscle_id: 1, soreness: 4}, {muscle_id: 2, soreness: 2}]
    
    API->>Backend: Log soreness entries
    Backend->>Backend: Update soreness_logs table
    Backend-->>API: SorenessLogResponse
    
    API-->>LogSoreness: Return logged soreness
    
    LogSoreness->>QueryClient: invalidateQueries(['recovery-state'])
    QueryClient->>API: GET /api/logs/recovery-state
    API->>Backend: Calculate recovery state with decay
    Backend->>Backend: apply_decay(last_soreness, days_since)
    Backend-->>API: RecoveryStateResponse
    
    API-->>QueryClient: Return recovery percentages
    QueryClient-->>LogSoreness: Update recovery display
    
    LogSoreness->>User: Show recovery state (shoulders: 60%, quads: 85%)
```

**Key Events:**
- `POST /api/logs/soreness`: Logs soreness entries
- `calculate_recovery_with_decay()`: Backend decay algorithm
- `invalidateQueries(['recovery-state'])`: Triggers recovery recalculation
- `GET /api/logs/recovery-state`: Fetches updated recovery state

---

### Dashboard Load Flow

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant QueryClient
    participant ProgramsAPI
    participant StatsAPI
    participant Backend
    
    User->>Dashboard: Navigate to dashboard
    Dashboard->>UIStore: getActiveProgramId()
    UIStore-->>Dashboard: Return activeProgramId
    
    Dashboard->>QueryClient: usePrograms(activeOnly: true)
    QueryClient->>ProgramsAPI: GET /api/programs?active_only=true
    ProgramsAPI->>Backend: Fetch active programs
    Backend-->>ProgramsAPI: Return programs
    ProgramsAPI-->>QueryClient: Cache programs
    QueryClient-->>Dashboard: Return active program
    
    Dashboard->>QueryClient: useProgram(activeProgramId)
    QueryClient->>ProgramsAPI: GET /api/programs/{id}
    ProgramsAPI->>Backend: Fetch program details with sessions
    Backend-->>ProgramsAPI: Return program details
    ProgramsAPI-->>QueryClient: Cache program details
    QueryClient-->>Dashboard: Return program sessions
    
    Dashboard->>QueryClient: useDashboardStats()
    QueryClient->>StatsAPI: GET /api/stats/dashboard
    StatsAPI->>Backend: Calculate dashboard statistics
    Backend->>Backend: Aggregate workout logs, e1RM PRs, volume
    Backend-->>StatsAPI: Return stats
    StatsAPI-->>QueryClient: Cache stats
    QueryClient-->>Dashboard: Return stats
    
    Dashboard->>User: Display dashboard with program, sessions, and stats
```

**Key Events:**
- `usePrograms(activeOnly: true)`: Fetches active program
- `useProgram(activeProgramId)`: Fetches program details with sessions
- `useDashboardStats()`: Fetches dashboard statistics
- Query caching prevents redundant API calls
- Parallel fetching with TanStack Query

---

## SSE Streaming Flow

### Workout Adaptation Streaming

```mermaid
sequenceDiagram
    participant User
    participant AdaptationModal
    participant Client
    participant Backend
    participant LLM
    participant ORTools
    participant DB
    
    User->>AdaptationModal: Request workout adaptation
    AdaptationModal->>User: Input constraints (soreness, time, equipment)
    
    User->>AdaptationModal: Submit adaptation request
    AdaptationModal->>Client: streamSSE('/days/{date}/adapt/stream', constraints)
    
    Client->>Backend: POST /api/days/{date}/adapt/stream
    Note over Client: Headers: Content-Type: application/json<br/>Authorization: Bearer <token>
    
    Backend->>DB: Fetch recent logs & signals
    DB-->>Backend: Return data
    
    Backend->>Backend: Calculate recovery state
    Backend->>Backend: Build constraint set
    
    loop Adaptation Process
        Backend->>LLM: Generate adapted plan
        LLM-->>Backend: Return proposed exercises (chunk 1)
        Backend-->>Client: SSE: data: {"type": "exercises", "content": "..."}
        Client-->>AdaptationModal: Yield chunk 1
        AdaptationModal->>User: Display partial exercises
        
        Backend->>LLM: Continue generation
        LLM-->>Backend: Return rationale (chunk 2)
        Backend-->>Client: SSE: data: {"type": "rationale", "content": "..."}
        Client-->>AdaptationModal: Yield chunk 2
        AdaptationModal->>User: Display rationale
        
        Backend->>ORTools: Validate against constraints
        ORTools-->>Backend: Return optimized plan
        Backend-->>Client: SSE: data: {"type": "optimized", "content": "..."}
        Client-->>AdaptationModal: Yield chunk 3
        AdaptationModal->>User: Display optimized plan
    end
    
    Backend-->>Client: SSE: data: [DONE]
    Client-->>AdaptationModal: Stream complete
    AdaptationModal->>User: Display "Accept" button
    
    User->>AdaptationModal: Accept adapted plan
    AdaptationModal->>Backend: POST /api/days/{date}/accept-plan
    Backend->>DB: Update session & mark accepted
    Backend-->>AdaptationModal: Success response
    
    AdaptationModal->>User: Show success toast
    AdaptationModal->>UIStore: addToast({type: 'success', message: 'Workout adapted!'})
```

**SSE Event Types:**
- `exercises`: Proposed exercises from LLM
- `rationale`: Reasoning behind adaptations
- `optimized`: OR-Tools optimized plan
- `[DONE]`: Stream termination signal

**Key Events:**
- `streamSSE()`: Async generator yielding SSE chunks
- `POST /api/days/{date}/adapt/stream`: Backend SSE endpoint
- `LLM generation`: Chunked response streaming
- `OR-Tools validation`: Constraint optimization
- `accept-plan`: Commits adapted plan to database

---

## State Synchronization

### Client State (Zustand) Flow

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> MenuOpen: toggleMenu()
    MenuOpen --> Idle: toggleMenu()
    
    Idle --> ProgramActive: setActiveProgramId(id)
    ProgramActive --> Idle: setActiveProgramId(null)
    
    ProgramActive --> WorkoutActive: setActiveWorkoutSessionId(id)
    WorkoutActive --> ProgramActive: setActiveWorkoutSessionId(null)
    
    Idle --> WizardStep1: resetWizardStep()
    WizardStep1 --> WizardStep2: nextWizardStep()
    WizardStep2 --> WizardStep3: nextWizardStep()
    WizardStep3 --> WizardStep4: nextWizardStep()
    WizardStep4 --> WizardStep5: nextWizardStep()
    WizardStep5 --> WizardStep6: nextWizardStep()
    WizardStep6 --> WizardStep7: nextWizardStep()
    WizardStep7 --> Idle: resetWizardStep()
    
    Idle --> ToastVisible: addToast()
    ToastVisible --> Idle: removeToast() or timeout
```

### Server State (TanStack Query) Flow

```mermaid
stateDiagram-v2
    [*] --> Fresh: Initial fetch
    Fresh --> Stale: After staleTime (1 min)
    Stale --> Fetching: Refetch triggered
    Fetching --> Fresh: Successful fetch
    Fetching --> Error: Fetch failed
    Error --> Fetching: Retry (max 1)
    Error --> Stale: Max retries exceeded
    
    Stale --> GC: After gcTime (5 min)
    GC --> [*]
    
    Fresh --> Fetching: Manual refetch
    Fresh --> Fetching: Window focus (disabled)
    Fresh --> Fetching: Query invalidation
```

### State Update Cascade

```mermaid
graph LR
    A[User Action] --> B[State Store Update]
    B --> C[API Mutation]
    C --> D[Backend Update]
    D --> E[Query Invalidation]
    E --> F[Query Refetch]
    F --> G[Component Re-render]
    
    style A fill:#e1f5fe
    style B fill:#fff9c4
    style C fill:#c8e6c9
    style D fill:#c8e6c9
    style E fill:#ffccbc
    style F fill:#e1bee7
    style G fill:#b2dfdb
```

**Example Cascade:**
1. User creates program via wizard
2. `WizardStore` updated with program data
3. `createProgram.mutateAsync()` triggers API call
4. Backend creates program in database
5. `queryClient.invalidateQueries(['programs'])` triggered
6. TanStack Query refetches program list
7. Dashboard re-renders with new program

---

## Cross-References

### System Architecture
- See [01_System_Architecture.md](./01_System_Architecture.md) for system-level design
- See [02_Backend_API_and_Logic.md](./02_Backend_API_and_Logic.md) for API endpoints
- See [03_Frontend_Architecture.md](./03_Frontend_Architecture.md) for component details

### Database Schema
- See [DATABASE_OVERVIEW.md](../DATABASE_OVERVIEW.md) for data models
- State stores mirror database models for consistency

### Implementation Plans
- See `docs/plans/adaptive-workout-loop.md` for adaptation flow details
- See `docs/plans/llm-integration.md` for LLM streaming implementation
- See `docs/plans/optimization-engine.md` for OR-Tools integration

---

## Glossary

- **Dependency Matrix**: Table showing component dependencies and data flow
- **Event Flow**: Sequence of events triggered by user actions
- **SSE**: Server-Sent Events for real-time streaming
- **Query Invalidation**: TanStack Query mechanism to refresh stale data
- **State Cascade**: Chain reaction of state updates across the app
- **Wizard Store**: Zustand store for multi-step program creation
- **UI Store**: Zustand store for global UI state
- **Mutation**: TanStack Query operation that modifies server state

---

## Tags

#component-interaction #dependency-matrix #event-flows #sse #state-synchronization #frontend #backend #zustand #tanstack-query #api-integration #data-flow #architecture
