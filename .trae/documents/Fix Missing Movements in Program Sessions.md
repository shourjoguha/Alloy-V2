# Fix Missing Movements in Program Sessions

## Summary
Program 265 has 84 sessions, but only 13 have exercises. Root cause: Background task only generates for ACTIVE microcycle and stopped partway through. All other microcycles have `generation_status="pending"` with 0 exercises.

## Implementation Plan

### 1. Add generation_status Updates (CRITICAL)
**File**: `app/services/session_generator.py`
- Update `populate_session_by_id()` to set `session.generation_status = "complete"` after successful save
- Set `generation_status = "failed"` when exceptions occur
- This provides visibility into which sessions succeeded/failed

### 2. Change Empty Dict Return to Exception
**File**: `app/services/session_generator.py` (line 154-156)
- Change `return {}` to `raise ValueError(...)` when session/program/microcycle not found
- Prevents silent failures where caller doesn't check for empty return

### 3. Add generation_status Enum
**File**: `app/models/enums.py`
- Add `GenerationStatus` enum: `PENDING`, `IN_PROGRESS`, `COMPLETE`, `FAILED`
- Update Session model to use this enum

### 4. Fix generation_status in Session Model
**File**: `app/models/program.py` (Session class)
- Add `generation_status` column to Session model
- Default to `GenerationStatus.PENDING`

### 5. Add Comprehensive Error Logging
**File**: `app/services/session_generator.py`
- Log ERROR level (not WARNING) when draft generation fails
- Log full exception traceback
- Log which specific movement lookups failed

### 6. Lower Missing Movements Threshold
**File**: `app/services/session_generator.py` (line 489-496)
- Change threshold from 25% to 10% for critical failure
- Prevents accepting too many incomplete sessions

### 7. Create Regenerate Endpoint for Failed Sessions
**File**: `app/api/routes/programs.py`
- Add POST `/programs/{program_id}/regenerate-sessions` endpoint
- Allows regenerating sessions that failed or have `generation_status != "complete"`

### 8. Fix Active Microcycle Only Generation (OPTIONAL)
**File**: `app/services/program.py`
- Consider creating `generate_all_program_sessions()` to generate for ALL microcycles
- Or add logic to auto-advance to next microcycle when current completes

### 9. Add Database Migration
**File**: Create new migration file
- Add `generation_status` column to sessions table
- Set default to `PENDING`

### 10. Fix Existing Program 265
**Action**: Manual script or admin endpoint
- Regenerate all pending sessions for program 265
- Update `generation_status` to `COMPLETE` for session 16827 (the only one with exercises)

## Testing
1. Test program creation - verify all sessions get `generation_status = COMPLETE`
2. Test regeneration endpoint - verify failed sessions are regenerated
3. Test frontend - verify sessions display with populated exercises
4. Verify logs show clear error messages when generation fails