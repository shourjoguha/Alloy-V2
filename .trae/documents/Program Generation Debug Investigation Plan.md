# Complete Debug Investigation and Fix Implementation Plan

## Root Cause Identified

**Critical Issue**: The `create_program` endpoint is hanging for 60 seconds due to **long database transaction** wrapping entire program creation (program + disciplines + microcycles + sessions).

**Key Finding**: [program.py:65-288](file:///Users/shourjosmac/Documents/alloy/app/services/program.py#L65-L288) uses `@transactional()` decorator that keeps a single database transaction open for creating dozens/hundreds of entities.

## Investigation Summary

### Phase 1: Frontend → Backend Communication ✅
- Frontend wizard correctly uses onClick handler
- Button component uses `type="button"` (correct for onClick pattern)
- API call should trigger via [program.wizard.tsx:160](file:///Users/shourjosmac/Documents/alloy/frontend/src/routes/program.wizard.tsx#L160)

### Phase 2: Backend Analysis ✅
- **All database operations are async** - no synchronous calls found
- **No `time.sleep()` calls** - proper async patterns used
- **Root cause**: Single transaction creating 4-12 microcycles × 7 days = 28-84 sessions

### Phase 3: Blocking Code Check ✅
- No blocking operations in background task path
- Background task properly scheduled AFTER program creation

### Phase 4: Background Task Execution ✅
- Proper async/await patterns throughout
- Timeout handling implemented (60-120s per session)
- Multi-layer error handling with fallbacks
- Continues generation even if individual sessions fail

### Phase 5: Documentation (IN PROGRESS)
- Will create PROGRAM_FLOW_GRAIN.md with all forks and branches
- Will document complete parameter flow from frontend to intelligence engine

## Fix Implementation Plan

### 1. Create PROGRAM_FLOW_GRAIN.md Document
Document complete workflow with all forks:
- Frontend wizard flow (4 steps)
- API call path
- Backend program creation flow
- Background session generation flow
- Intelligence engine decision tree (7 priority levels)
- All branching points with hierarchical IDs

### 2. Fix the 60-second Hang

**Option A: Break Transaction (Recommended)**
- Commit program entity first
- Then handle microcycles/sessions in separate transactions
- Allows immediate return after program is created

**Option B: Async Skeleton Creation**
- Create microcycles and sessions asynchronously after program is committed
- Return skeleton response immediately
- Continue generation in background

**Option C: Optimize Database Queries**
- Add indexes for ILIKE operations
- Batch insert operations
- Reduce query complexity

### 3. Add Diagnostic Logging
- Add entry/exit logs to POST /programs endpoint
- Add timing logs for major operations
- Log background task scheduling

### 4. Test End-to-End Flow
- Verify POST /programs returns immediately
- Verify background task executes properly
- Verify polling endpoint shows correct status
- Verify sessions are generated successfully

## Files to Modify

1. **[PROGRAM_FLOW_GRAIN.md](file:///Users/shourjosmac/Documents/alloy/PROGRAM_FLOW_GRAIN.md)** - Create new documentation
2. **[app/services/program.py](file:///Users/shourjosmac/Documents/alloy/app/services/program.py)** - Refactor create_program transaction handling
3. **[app/api/routes/programs.py](file:///Users/shourjosmac/Documents/alloy/app/api/routes/programs.py)** - Add diagnostic logging
4. **[app/core/transactions.py](file:///Users/shourjosmac/Documents/alloy/app/core/transactions.py)** - Consider transaction scope optimization

## Dependencies to Verify

1. **Frontend**: Zustand store, React Query, Button component
2. **Backend**: FastAPI, SQLAlchemy AsyncSession, BackgroundTasks
3. **Services**: ProgramService, SessionGeneratorService, GreedyOptimizationService
4. **ML**: GlobalMovementScorer (decision tree with 7 dimensions)
5. **Database**: PostgreSQL with proper indexes

## Success Criteria

- POST /programs returns within 2-3 seconds (not 60s)
- Background task generates sessions asynchronously
- Frontend can poll generation status successfully
- All sessions have exercises generated
- No database lock issues