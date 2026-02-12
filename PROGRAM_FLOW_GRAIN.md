# Program Creation Flow - Complete Workflow Documentation

## Overview

This document traces the complete program creation workflow from frontend UI through backend services, intelligence engine (decision tree), and back to database storage and UI display. All forks and branches are identified with hierarchical reference IDs.

---

## FORK [1.0] FRONTEND: User Clicks "Create Program"

**Entry Points:**
1. [Dashboard](frontend/src/components/layout/dashboard.tsx) - Lines 191-197, 202-207
2. [ProgramsTab](frontend/src/components/settings/ProgramsTab.tsx) - Lines 75-85
3. [program.new.tsx](frontend/src/routes/program.new.tsx) - Selection page

### FORK [1.1] Button Component Handler

**Location:** [WizardContainer.tsx:85-94](frontend/src/components/wizard/WizardContainer.tsx#L85-L94)

**Implementation:** Uses `onClick` handler (not form submission)

```typescript
<Button
  variant="cta"
  onClick={onSubmit}
  disabled={!canProceed || isSubmitting}
  isLoading={isSubmitting}
  className="flex-1"
>
  <Check className="h-4 w-4 mr-2" />
  Create Program
</Button>
```

**Branch A (Current):** onClick handler - Calls parent's onSubmit prop
**Branch B (Not Used):** type="submit" - Would trigger form submission

**Next → [1.2]**

---

## FORK [1.2] FRONTEND: Wizard State Validation

**Location:** [program.wizard.tsx:115-218](frontend/src/routes/program.wizard.tsx#L115-L218)

**Purpose:** Validates all wizard inputs before API call

### FORK [1.2.1] Goals Validation

**Branch A:** Goals sum to exactly $10
- Valid: Continue to next validation
- Invalid: Show error message

**Branch B:** 1-3 goals selected
- Valid: Continue
- Invalid: Show error message

**Next → [1.2.2]**

### FORK [1.2.2] Duration Validation

**Branch A:** Duration 8-12 weeks
- Valid: Continue
- Invalid: Show error message

**Branch B:** Duration is even number
- Valid: Continue
- Invalid: Show error message

**Next → [1.2.3]**

### FORK [1.2.3] Frequency Validation

**Branch A:** 2-7 days per week
- Valid: Continue
- Invalid: Show error message

**Next → [2.0]**

---

## FORK [2.0] FRONTEND → BACKEND: POST /programs

**Location:** [program.wizard.tsx:160](frontend/src/routes/program.wizard.tsx#L160) → [programs.ts:27-30](frontend/src/api/programs.ts#L27-L30) → [programs.py:82](app/api/routes/programs.py#L82)

**Purpose:** Send program creation request to backend

### FORK [2.1] Network Request Success/Failure

**Branch A:** Success (200 OK)
- Action: Navigate to `/program/$programId`
- Action: Invalidate React Query cache for programs list

**Branch B:** Network Error
- Action: Show error message to user
- Action: Stay on wizard page

**Branch C:** Server Error (500+)
- Action: Show error message to user
- Action: Stay on wizard page

**Branch D:** Timeout (60s)
- **CURRENT ISSUE:** Request hangs for 60 seconds
- Expected: Timeout error message
- Actual: No response, request appears to not reach server

**Next → [3.0]**

---

## FORK [3.0] BACKEND: POST /programs Endpoint

**Location:** [programs.py:82-264](app/api/routes/programs.py#L82-L264)

**Purpose:** Create program with microcycles and sessions, return skeleton, start background generation

### FORK [3.1] User Authentication

**Location:** Line 87 - `user_id = Depends(get_current_user_id)`

**Branch A:** User authenticated
- Action: Continue to program creation
- Result: user_id extracted from JWT token

**Branch B:** User not authenticated
- Action: Return 401 Unauthorized
- Action: Stop processing

**Next → [3.2]**

### FORK [3.2] User Lookup

**Location:** Lines 110-118

**Branch A:** User found
- Action: Extract user.experience_level, user.persona_tone, user.persona_aggression
- Action: Continue to program creation

**Branch B:** User not found
- Action: Raise NotFoundError
- Action: Return 404 response

**Next → [3.3]**

### FORK [3.3] ProgramService.create_program Call

**Location:** Line 124 - `program = await service.create_program(user_id, program_data)`

**Critical Issue:** This call is wrapped in `@transactional()` decorator and can take 60+ seconds

**Branch A:** Success
- Action: Program entity created with microcycles and sessions
- Action: Proceed to skeleton response construction
- **CURRENT PROBLEM:** This takes 60+ seconds due to large transaction

**Branch B:** ValidationError
- Action: Catch and return 400 error
- Action: Stop processing

**Branch C:** BusinessRuleError
- Action: Catch and return 400 error
- Action: Stop processing

**Next → [3.4]**

### FORK [3.4] Program Disciplines Creation

**Location:** Lines 203-228

**Branch A:** Disciplines from request
- Action: Create ProgramDiscipline entities for each
- Action: Add to transaction

**Branch B:** Disciplines from user profile
- Action: Load from UserProfile.discipline_preferences
- Action: Create ProgramDiscipline entities

**Branch C:** Fallback based on experience level
- Action: Use default discipline weights
- Action: Create ProgramDiscipline entities

**Next → [3.5]**

### FORK [3.5] Microcycle and Sessions Creation Loop

**Location:** Lines 230-283

**Purpose:** Create 4-12 microcycles (each 7-14 days) with sessions

**Critical Issue:** Creates 28-84 sessions in a single transaction

**Loop for each microcycle:**

### FORK [3.5.1] Microcycle Creation

**Branch A:** First microcycle (mc_idx = 0)
- Action: Set status = ACTIVE
- Action: Keep reference for session generation

**Branch B:** Subsequent microcycles (mc_idx > 0)
- Action: Set status = PLANNED
- Action: Don't generate sessions yet

**Next → [3.5.2]**

### FORK [3.5.2] Split Configuration

**Location:** Lines 246-267

**Branch A:** Goal-based cycle distribution
- Action: Apply goal weights to session types
- Action: Adjust cardio/mobility/conditioning days
- Action: Set finisher/accessory preferences

**Branch B:** Freeform split (no goals)
- Action: Use default template
- Action: Distribute training days evenly

**Next → [3.5.3]**

### FORK [3.5.3] Session Creation per Day

**Location:** Lines 872-893 in `_create_microcycle`

**Branch A:** Training day (lifting)
- Action: Create Session with type based on split (upper/lower/push/pull/full_body)
- Action: Add intent_tags (squat, hinge, lunge, horizontal_push, etc.)

**Branch B:** Cardio day
- Action: Create Session with type = CARDIO
- Action: Add focus tags (endurance/fat_loss)

**Branch C:** Mobility day
- Action: Create Session with type = MOBILITY
- Action: Add recovery activities

**Branch D:** Rest day
- Action: Create Session with type = RECOVERY
- Action: No exercises generated initially

**Next → [3.6]**

### FORK [3.6] Movement Rules and Activities

**Location:** Lines 143-168

**Branch A:** Movement rules provided
- Action: Create UserMovementRule entities
- Action: Store in database

**Branch B:** Enjoyable activities provided
- Action: Create UserEnjoyableActivity entities
- Action: Store in database

**Branch C:** Neither provided
- Action: Skip this step
- Action: Continue to response

**Next → [3.7]**

### FORK [3.7] Skeleton Response Construction

**Location:** Lines 178-258

**Purpose:** Load microcycles and sessions for immediate response

**Branch A:** Active microcycle found
- Action: Load microcycle.sessions with exercises
- Action: Build MicrocycleWithSessionsResponse

**Branch B:** No active microcycle
- Action: Set active_microcycle = None
- Action: Return skeleton with planned microcycles only

**Next → [3.8]**

### FORK [3.8] Background Task Scheduling

**Location:** Lines 234-236

**Branch A:** Background task scheduled
- Action: `background_tasks.add_task(_background_generate_sessions, program.id)`
- Action: Task runs AFTER response is returned

**Branch B:** Background task fails to schedule
- Action: Log error
- Action: Continue with skeleton response

**Next → [4.0]**

---

## FORK [4.0] BACKGROUND: _background_generate_sessions

**Location:** [programs.py:48-68](app/api/routes/programs.py#L48-L68)

**Purpose:** Wrapper for background generation with comprehensive logging

### FORK [4.1] Task Lifecycle

**Branch A:** Task started successfully
- Action: Log "[BACKGROUND_TASK] STARTED"
- Action: Call generate_active_microcycle_sessions

**Branch B:** Exception raised
- Action: Log "[BACKGROUND_TASK] FAILED" with full traceback
- Action: Re-raise exception

**Next → [5.0]**

---

## FORK [5.0] PROGRAM SERVICE: generate_active_microcycle_sessions

**Location:** [program.py:317-355](app/services/program.py#L317-L355)

**Purpose:** Generate exercise content for all non-rest sessions in active microcycle

### FORK [5.1] Active Microcycle Lookup

**Branch A:** Active microcycle found
- Action: Set generation_status = IN_PROGRESS
- Action: Proceed to session generation

**Branch B:** Active microcycle not found
- Action: Return error {"status": "failed", "error": "Active microcycle not found"}
- Action: Stop generation

**Next → [5.2]**

### FORK [5.2] Session Generation Loop

**Purpose:** Iterate through all sessions in microcycle and generate content

**For each session:**

### FORK [5.2.1] Session Type Handling

**Location:** Lines 428-447

**Branch A:** RECOVERY session
- Action: Skip content generation
- Action: Mark generation_status = COMPLETED
- Action: Continue to next session

**Branch B:** CARDIO/MOBILITY session
- Action: Skip content generation (use predefined content)
- Action: Mark generation_status = COMPLETED
- Action: Continue to next session

**Branch C:** CUSTOM + conditioning session
- Action: Use LLM call (120s timeout)
- Action: Generate via generate_session_exercises_offline
- Action: **TIMEOUT RISK:** Can exceed 120s

**Branch D:** Regular lifting session
- Action: Use GreedyOptimizer (60s timeout)
- Action: Generate via generate_session_exercises_offline
- Action: **TIMEOUT RISK:** Can exceed 60s

**Next → [5.2.2]**

### FORK [5.2.2] Pattern Interference Rules

**Location:** Lines 632-712

**Purpose:** Apply inter-session interference rules for main lift patterns

**Branch A:** Pattern conflict detected
- Action: Find alternative pattern
- Action: Replace conflicting pattern in intent_tags
- Action: Log replacement

**Branch B:** No conflict
- Action: Keep original pattern
- Action: Continue to generation

**Next → [5.2.3]**

### FORK [5.2.3] Session Content Generation

**Location:** Lines 485-494 - Call to `populate_session_by_id`

**Branch A:** Generation successful
- Action: Mark generation_status = COMPLETED
- Action: Track used movements and patterns
- Action: Update previous_day_volume
- Action: Continue to next session

**Branch B:** TimeoutError (60s or 120s)
- Action: Set coach_notes with timeout message
- Action: Mark generation_status = FAILED
- Action: Continue to next session (resilient)

**Branch C:** Other Exception
- Action: Log error with full traceback
- Action: Mark generation_status = FAILED
- Action: Continue to next session (resilient)

**Next → [5.3]**

### FORK [5.3] Microcycle Completion

**Location:** Lines 616-624

**Branch A:** All sessions completed successfully
- Action: Set microcycle generation_status = COMPLETED
- Action: Return success progress

**Branch B:** Some sessions failed
- Action: Set microcycle generation_status = FAILED
- Action: Return progress with failure counts

**Next → [6.0]**

---

## FORK [6.0] SESSION GENERATOR: populate_session_by_id

**Location:** [session_generator.py:146-350](app/services/session_generator.py#L146-L350)

**Purpose:** Generate and save exercise content to a session using IDs

### FORK [6.1] Context Data Collection

**Location:** Lines 176-247

**Purpose:** Fetch all necessary data (short DB transaction)

**Branch A:** All entities found
- Action: Build context_data dictionary
- Action: Include program goals, session info, movements, rules, user profile
- Action: Proceed to content generation

**Branch B:** Missing entities
- Action: Raise ValueError
- Action: Stop generation

**Next → [6.2]**

### FORK [6.2] Content Generation (Long Running, NO DB Connection)

**Location:** Lines 249-304

**Purpose:** Generate exercises without holding DB lock

### FORK [6.2.1] Session Type Determination

**Branch A:** RECOVERY
- Action: Return predefined recovery content

**Branch B:** CARDIO/MOBILITY
- Action: Return predefined cardio/mobility content

**Branch C:** CUSTOM + conditioning
- Action: Use LLM for conditioning session
- Action: 120s timeout

**Branch D:** Regular session
- Action: Use GreedyOptimizer via generate_session_exercises_offline
- Action: 60s timeout

**Next → [6.2.2]**

### FORK [6.2.2] Fatigue Calculation

**Location:** Lines 253-255

**Branch A:** Previous day volume exists
- Action: Calculate fatigued muscles (volume > 2)
- Action: Pass to generation

**Branch B:** No previous day
- Action: Set fatigued_muscles = []
- Action: Pass to generation

**Next → [6.3]**

### FORK [6.3] Timeout Handling

**Location:** Lines 257-291

**Branch A:** Generation completes within timeout
- Action: Proceed to save results
- Action: Return content

**Branch B:** TimeoutError raised
- Action: Log timeout error
- Action: Mark session as FAILED with timeout message
- Action: Return empty dict (skip to next session)

**Next → [6.4]**

### FORK [6.4] Duplicate Removal

**Location:** Lines 294-303

**Branch A:** Previous day has accessories
- Action: Remove duplicate movements from current session
- Action: Apply only to accessory exercises

**Branch B:** No previous accessories
- Action: Skip duplicate removal
- Action: Continue

**Next → [6.5]**

### FORK [6.5] Save Results to Database

**Location:** Lines 306-347

**Purpose:** Save generated exercises and update session

**Branch A:** Save successful
- Action: Create SessionExercise entities
- Action: Set estimated_duration_minutes
- Action: Set coach_notes with reasoning
- Action: Set generation_status = COMPLETED
- Action: Commit transaction

**Branch B:** Save failed
- Action: Log error
- Action: Keep session as PENDING or FAILED

**Next → [7.0]**

---

## FORK [7.0] GREEDY OPTIMIZER: Movement Selection

**Location:** [greedy_optimizer.py:125-150](app/services/greedy_optimizer.py#L125-L150)

**Purpose:** Solve for optimal movements using greedy selection with progressive relaxation

### FORK [7.1] Progressive Relaxation (6 Steps)

**Location:** Lines 98-104 (RelaxationConfig)

**Purpose:** Relax constraints progressively if no solution found

**Branch 0 (Step 0): Strict Mode**
- Action: All constraints enforced
- Action: pattern_compatibility_expansion = False
- Action: include_synergist_muscles = False
- Action: discipline_weight_multiplier = 1.0
- Action: allow_isolation_movements = False
- Action: allow_generic_movements = False
- Action: emergency_mode = False

**Branch 1 (Step 1):** Expand Pattern Compatibility
- Action: pattern_compatibility_expansion = True
- Action: Allow similar patterns to be considered compatible

**Branch 2 (Step 2):** Include Synergist Muscles
- Action: include_synergist_muscles = True
- Action: Expand volume calculations to include synergists

**Branch 3 (Step 3):** Reduce Discipline Weight
- Action: discipline_weight_multiplier = 0.7
- Action: Lower importance of discipline preference

**Branch 4 (Step 4):** Accept Isolation Movements
- Action: allow_isolation_movements = True
- Action: Allow single-joint exercises

**Branch 5 (Step 5):** Accept Generic Movements
- Action: allow_generic_movements = True
- Action: Allow low-tier compound exercises

**Branch 6 (Step 6):** Emergency Mode
- Action: emergency_mode = True
- Action: Minimal constraints only

**Next → [8.0]**

---

## FORK [8.0] INTELLIGENCE ENGINE: GlobalMovementScorer

**Location:** [movement_scorer.py:1-150](app/ml/scoring/movement_scorer.py#L1-L150)

**Purpose:** Decision tree scorer for movement selection with 7 priority levels

### FORK [8.1] Scoring Dimensions (7 Priority Levels)

**Location:** Lines 82-103 (ScoringDimension)

**Purpose:** Multi-dimensional evaluation of movements

**Priority Level 1:** Pattern Alignment
- **Weight:** 0.25
- **Purpose:** Match movement to session intent_tags
- **Rules:** Exact match = 1.0, compatible pattern = 0.8, incompatible = 0.0

**Priority Level 2:** Muscle Coverage
- **Weight:** 0.20
- **Purpose:** Cover primary and secondary muscles
- **Rules:** New muscle = 1.0, already covered = 0.3

**Priority Level 3:** Discipline Preference
- **Weight:** 0.15
- **Purpose:** Match user's preferred discipline (bodybuilding/powerlifting/etc.)
- **Rules:** Exact match = 1.0, related = 0.6, unrelated = 0.0

**Priority Level 4:** Compound Bonus
- **Weight:** 0.15
- **Purpose:** Reward compound movements over isolation
- **Rules:** Compound = 1.0, isolation = 0.0

**Priority Level 5:** Specialization
- **Weight:** 0.10
- **Purpose:** Reward movements matching user's specialization
- **Rules:** Specialized movement = 1.0, general = 0.5

**Priority Level 6:** Goal Alignment
- **Weight:** 0.10
- **Purpose:** Match movement to program goals
- **Rules:** Strength goal + strength pattern = 1.0, etc.

**Priority Level 7:** Time Utilization
- **Weight:** 0.05
- **Purpose:** Fit within max_session_duration
- **Rules:** Within ±5% tolerance = 1.0, slightly over = 0.5, significantly over = 0.0

**Next → [9.0]**

---

## FORK [9.0] DATABASE: SessionExercise Creation

**Location:** [session_generator.py:336-347](app/services/session_generator.py#L336-L347)

**Purpose:** Save generated exercises to database

### FORK [9.1] Exercise Role Assignment

**Branch A:** WARMUP
- Action: Create SessionExercise with exercise_role = WARMUP
- Action: Sets, reps, rpe based on warmup heuristics

**Branch B:** MAIN
- Action: Create SessionExercise with exercise_role = MAIN
- Action: Use movement from optimization result
- Action: Sets based on progression style and deload

**Branch C:** ACCESSORY
- Action: Create SessionExercise with exercise_role = ACCESSORY
- Action: Use movement from optimization result

**Branch D:** FINISHER
- Action: Create SessionExercise with exercise_role = FINISHER
- Action: Use movement from optimization result

**Branch E:** COOLDOWN
- Action: Create SessionExercise with exercise_role = COOLDOWN
- Action: Use recovery movements

**Next → [10.0]**

---

## FORK [10.0] FRONTEND: Program Display and Polling

**Location:** After navigation to `/program/$programId`

**Purpose:** Display program skeleton and poll for generation status

### FORK [10.1] Polling Loop

**Branch A:** Generation in progress (IN_PROGRESS)
- Action: Show loading spinner
- Action: Poll GET /programs/{programId}/generation-status every 2-3 seconds
- Action: Update progress indicators

**Branch B:** Generation completed (COMPLETED)
- Action: Show full program with exercises
- Action: Display coach notes
- Action: Allow starting sessions

**Branch C:** Generation failed (FAILED)
- Action: Show error message
- Action: Display coach notes with failure reason
- Action: Offer regeneration button

**Next → [END]**

---

## Complete Parameter Flow Summary

### Parameters from Frontend to Intelligence Engine

| Parameter | Origin Stage | Transform Location | Route to Intelligence Engine | Final Storage |
|-----------|----------------|---------------------|----------------------------|----------------|
| **goals** (1-3, $10 budget) | [GoalsStep.tsx](frontend/src/components/wizard/GoalsStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:96-109](app/services/program.py#L96-L109) → [greedy_optimizer.py:125-150](app/services/greedy_optimizer.py#L125-L150) | Program.goal_1, goal_2, goal_3, goal_weight_1, goal_weight_2, goal_weight_3 |
| **duration_weeks** (8-12) | [CoachStep.tsx](frontend/src/components/wizard/CoachStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:88-94](app/services/program.py#L88-L94) | Program.duration_weeks |
| **days_per_week** (2-7) | [SplitStep.tsx](frontend/src/components/wizard/SplitStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:179](app/services/program.py#L179) | Program.days_per_week |
| **split_template** | [SplitStep.tsx](frontend/src/components/wizard/SplitStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:136-145](app/services/program.py#L136-L145) | Program.split_template |
| **max_session_duration** (30-120 mins) | [SplitStep.tsx](frontend/src/components/wizard/SplitStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:180](app/services/program.py#L180) → TimeEstimationService | Program.max_session_duration |
| **persona_tone** | [CoachStep.tsx](frontend/src/components/wizard/CoachStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:168-170](app/services/program.py#L168-L170) | Program.persona_tone |
| **persona_aggression** (1-5) | [CoachStep.tsx](frontend/src/components/wizard/CoachStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:169](app/services/program.py#L169) | Program.persona_aggression |
| **movement_rules** (hard yes/no/preferred) | [ActivitiesAndMovementsStep.tsx](frontend/src/components/wizard/ActivitiesAndMovementsStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:143-152](app/services/program.py#L143-L152) | UserMovementRule table |
| **enjoyable_activities** | [ActivitiesAndMovementsStep.tsx](frontend/src/components/wizard/ActivitiesAndMovementsStep.tsx) | [program.wizard.tsx:145-155](frontend/src/routes/program.wizard.tsx#L145-L155) → [programs.py:82](app/api/routes/programs.py#L82) | [program.py:154-168](app/services/program.py#L154-L168) | UserEnjoyableActivity table |

### Intelligence Engine (GlobalMovementScorer) Parameters

| Parameter | Source | Purpose in Scoring |
|-----------|--------|-------------------|
| **goal_weights** | Program.goal_weight_1, goal_weight_2, goal_weight_3 | [scoring_metrics.py:630-648](app/ml/scoring/scoring_metrics.py#L630-L648) - goal_alignment dimension |
| **session_type** | Session.session_type | Determines pattern requirements and movement count |
| **intent_tags** | Session.intent_tags | Pattern alignment scoring via [movement_scorer.py](app/ml/scoring/movement_scorer.py) |
| **movements_by_pattern** | DB query | [session_generator.py:85](app/services/session_generator.py#L85) - Pattern alignment |
| **movement_rules** | UserMovementRule table | [session_generator.py:199](app/services/session_generator.py#L199) - User constraints |
| **discipline_preferences** | UserProfile.discipline_preferences | [session_generator.py:244](app/services/session_generator.py#L244) - Discipline dimension |
| **used_movements** | Microcycle tracking | Variety enforcement across sessions |
| **previous_day_volume** | Previous session tracking | Fatigue/interference logic |
| **max_session_duration** | Program.max_session_duration | Time constraint validation (±5% tolerance) |

---

## Dependencies Summary

### Frontend Dependencies
1. **Zustand Store** ([program-wizard-store.ts](frontend/src/stores/program-wizard-store.ts)) - State management
2. **React Query** ([programs.ts:93-104](frontend/src/api/programs.ts#L93-L104)) - API mutation hooks
3. **Button Component** ([WizardContainer.tsx:85-94](frontend/src/components/wizard/WizardContainer.tsx#L85-L94)) - Click handler

### Backend Dependencies
1. **FastAPI BackgroundTasks** - Async task execution ([programs.py:234-236](app/api/routes/programs.py#L234-L236))
2. **SQLAlchemy AsyncSession** - Database operations
3. **ProgramService** ([program.py](app/services/program.py)) - Business logic
4. **SessionGeneratorService** ([session_generator.py](app/services/session_generator.py)) - Session content generation
5. **GreedyOptimizationService** ([greedy_optimizer.py](app/services/greedy_optimizer.py)) - Movement selection
6. **GlobalMovementScorer** ([movement_scorer.py](app/ml/scoring/movement_scorer.py)) - Decision tree scoring
7. **TimeEstimationService** - Duration calculations

### Critical Dependencies (Blocking Issues)

**FastAPI BackgroundTasks:**
- BackgroundTasks run on same event loop as main request
- If any blocking code (synchronous DB calls, CPU-intensive ops, `time.sleep()`) is in background task path, it blocks the ENTIRE event loop
- This prevents other requests from being processed

**Program Service Transaction:**
- The `@transactional()` decorator on [program.py:65-288](app/services/program.py#L65-L288) keeps a database transaction open for the ENTIRE program creation
- This includes creating dozens/hundreds of database entities (program, disciplines, microcycles, sessions)
- Can easily exceed 60 seconds for large programs

**Database Query Performance:**
- The `_infer_avoid_cardio_days()` query in [program.py:290-315](app/services/program.py#L290-L315) uses four ILIKE operations with wildcards
- Cannot use database indexes efficiently
- Requires full table scans
- Could be slow on large Movement table

---

## Known Issues and Symptoms

### Issue 1: POST /programs Request Hanging (60 Seconds)

**Symptom:** Request to create program hangs for 60 seconds without returning

**Root Cause:** Long database transaction in `ProgramService.create_program()` wrapped with `@transactional()` decorator

**Contributing Factors:**
1. Creating 4-12 microcycles
2. Each microcycle has 7-14 days = 28-168 sessions
3. All created in a single transaction
4. Multiple flushes and commits accumulate
5. ILIKE queries for avoid_cardio_days check

**Impact:** Frontend receives no response, background task never starts, sessions never generated

### Issue 2: Sessions Not Generating

**Symptom:** Programs created but sessions have no exercises

**Root Cause:** If POST /programs times out or fails, background task never starts

**Impact:** User sees skeleton program with empty sessions
**Recovery:** User must manually regenerate sessions via admin endpoints

### Issue 3: Polling Shows Wrong Status

**Symptom:** Frontend polls for program 272's status (from previous session)

**Root Cause:** POST /programs request never reached server for new program creation

**Impact:** User sees old program status, not new program

---

## Fix Priorities

### Priority 1: Fix 60-second Hang (Critical)

**Approach A: Break Transaction (Recommended)**
- Commit program entity first
- Return skeleton response immediately
- Handle microcycles and sessions in separate async operations

**Approach B: Optimize Database Queries**
- Add indexes for ILIKE operations
- Reduce query complexity
- Batch insert operations

**Approach C: Reduce Transaction Scope**
- Move transaction boundary to be smaller
- Commit after each major operation
- Use async operations for long-running tasks

### Priority 2: Add Diagnostic Logging

**Add Entry/Exit Logs:**
- POST /programs endpoint: Log start/end with timing
- Background task: Log when scheduled and when completes
- Session generation: Log each session with timing

### Priority 3: Improve Error Recovery

**Add Fallback Mechanisms:**
- Retry failed sessions automatically
- Provide clear error messages to user
- Allow manual regeneration of individual sessions

---

## Success Criteria

- POST /programs returns within 2-3 seconds (not 60s)
- Background task executes asynchronously
- Frontend can poll generation status successfully
- All sessions have exercises generated
- No database lock issues
- Frontend shows correct program after creation
