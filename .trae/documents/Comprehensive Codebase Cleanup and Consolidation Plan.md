# Comprehensive Codebase Cleanup and Consolidation Plan

## Executive Summary

This plan addresses 4 major problem areas identified after 2026-02-10 cleanup:
1. Frontend loading issues (Spinner duplication, inconsistent imports)
2. Missing program UI components
3. OR-Tools vs decision tree optimization hybrid duplication
4. Enum duplications (MovementRuleType, SkillLevel, PrimaryMuscle)

---

## Important Clarification: Optimization Architecture

**Current State (Hybrid):**
- `app/services/optimization_v2.py` - Wrapper using OR-Tools CP-SAT solver
- `app/ml/scoring/movement_scorer.py` - Decision tree scorer (GlobalMovementScorer) ← **KEEPS THIS**

**After Changes:**
- **DELETE:** `optimization_v2.py` (OR-Tools wrapper)
- **KEEP:** `movement_scorer.py` (decision tree logic with 7 scoring dimensions)
- **CREATE:** `greedy_optimizer.py` (uses GlobalMovementScorer without OR-Tools)

The ML-based decision tree logic (`GlobalMovementScorer`) is NOT in optimization_v2.py - it's in `app/ml/scoring/movement_scorer.py`. The optimization_v2.py file just wraps OR-Tools and uses GlobalMovementScorer as its objective function.

---

## Problem 1: Frontend Loading Issues

### Root Causes
- **Duplicate Spinner**: Two implementations (common/Spinner.tsx vs ui/spinner.tsx) with 7 components using common, 1 using UI
- **Inconsistent imports**: Mixed barrel file vs direct imports across components
- **Empty file**: MuscleList.tsx exists but is empty (0 lines)
- **Missing type re-exports**: Anatomy types not re-exported from main types/index.ts

### Implementation Plan

**Phase 1.1: Standardize Spinner Component** (30 min)
1. Choose UI spinner (Lucide-based) as standard
2. Update 7 components using common/Spinner to use @/components/ui/spinner
3. Delete common/Spinner.tsx
4. Update components/common/index.ts barrel export

**Phase 1.2: Standardize Component Imports** (20 min)
1. Audit all Button, Card, Tabs imports for consistency
2. Update any direct imports to use barrel files (@/components/ui/*)
3. Document import pattern in CONTRIBUTING.md

**Phase 1.3: Fix Empty MuscleList** (15 min)
1. Delete empty MuscleList.tsx file
2. Verify no imports exist (already confirmed)

**Phase 1.4: Re-export Anatomy Types** (10 min)
1. Add to types/index.ts: `export type { MuscleGroup, BodyZone } from './anatomy'`
2. Add: `export { ZONE_MAPPING, BODY_ZONE_LABELS, MUSCLE_DISPLAY_NAMES } from './anatomy'`

### Second-Order Effects
- None identified - these are purely structural fixes

---

## Problem 2: Missing Program UI Components

### Root Causes
- No dedicated program folder with consistent components
- Basic program.$programId.tsx route exists but displays minimal data
- Backend API is complete but frontend doesn't use all available fields

### Implementation Plan

**Phase 2.1: Create Component Structure** (2 hours)
Create new components in `frontend/src/components/program/`:
1. **ProgramHeader.tsx** - Program name (editable), goals, stats, split template
2. **MicrocycleList.tsx** - Week-by-week timeline with status badges
3. **MicrocycleCard.tsx** - Individual week display with 7-14 day grid
4. **SessionThumbnail.tsx** - Compact session preview (type, duration, key exercises)
5. **ProgramStats.tsx** - Weeks completed, days trained, adherence rate

**Phase 2.2: Rewrite program.$programId.tsx** (3 hours)
1. Implement tab navigation (Overview | Schedule | History)
2. Integrate new components into page structure
3. Add breadcrumbs: Dashboard → Programs → Program Name → Week X → Day Y
4. Add loading skeletons and empty states

**Phase 2.3: Enhance ProgramsTab** (1 hour)
1. Replace placeholder day cells with real SessionThumbnail components
2. Add progress indicators (weeks completed / total)
3. Improve quick action menu (edit, duplicate, archive)

**Phase 2.4: API Integration** (1 hour)
1. Ensure all new components use existing API hooks (useProgram, usePrograms)
2. Verify data flow from backend Pydantic schemas to TypeScript types
3. Add error handling and retry logic

### Second-Order Effects
- Dashboard component may need updates to display program summary
- TanStack Query cache invalidation strategies needed
- Mobile responsive design considerations for new components

### Third-Order Effects
- May reveal missing backend API fields (add endpoints if needed)
- Performance optimization for large program lists (pagination)
- Accessibility improvements for new UI patterns

---

## Problem 3: OR-Tools vs Decision Tree Optimization Duplication

### Root Causes
- Hybrid architecture: OR-Tools CP solver + GlobalMovementScorer (decision tree)
- 3 configuration sources with overlapping settings
- OR-Tools adds complexity without clear benefit over greedy selection

### Current Architecture
```
SessionGeneratorService
  └─> DiversityOptimizationService.solve_session_with_diversity_scoring()
       ├─> OR-Tools CpModel (constraint satisfaction) ← DELETE THIS
       └─> GlobalMovementScorer (objective function) ← KEEP THIS
```

### Configuration Duplications
| Setting | Location 1 | Location 2 | Location 3 |
|---------|-------------|-------------|-------------|
| Volume targets | activity_distribution_config | OptimizationConstants | YAML scoring config |
| Muscle coverage limits | YAML max_repeats | OptimizationConstants | SessionQualityKPI |
| Time calculations | OptimizationConstants | YAML rest_seconds | activity_distribution_config |
| Pattern compatibility | YAML matrix | optimization_v2.py logic | GlobalMovementScorer checks |

### Implementation Plan

**Phase 3.1: Create Unified Configuration** (2 hours)
1. Create `app/config/optimization_config.yaml` with:
   - All scoring dimensions (from movement_scoring.yaml)
   - All constraints (volume, fatigue, duration, equipment)
   - All relaxation strategy settings
   - All goal profiles and discipline modifiers
2. Create `OptimizationConfigLoader` class (similar to ScoringConfigLoader)
3. Update all imports to use unified config

**Phase 3.2: Implement Greedy Selection Algorithm** (4 hours)
Create `app/services/greedy_optimizer.py`:
```python
class GreedyOptimizer:
    async def select_movements_with_scoring(
        self,
        available_movements: list[SolverMovement],
        targets: dict[str, int],  # muscle -> sets
        constraints: dict
    ) -> OptimizationResultV2:
        """
        Greedy selection based on GlobalMovementScorer scores.
        1. Score all movements using GlobalMovementScorer (from app/ml/scoring/)
        2. Sort by total_score (descending)
        3. Greedily select until volume targets met
        4. Apply progressive relaxation (6 steps) if needed
        """
```

**Phase 3.3: Migrate Session Generator** (2 hours)
1. Update `session_generator.py` to use greedy optimizer
2. Add feature flag: `use_or_tools_optimizer` (default: False)
3. Keep optimization_v2.py for A/B comparison during testing

**Phase 3.4: Comprehensive Testing** (3 hours)
1. Port 24 integration tests to greedy optimizer
2. Add A/B comparison tests (OR-Tools vs greedy)
3. Measure session quality metrics (KPIs, success rate)
4. Performance benchmark (solve time, memory usage)

**Phase 3.5: Remove OR-Tools** (1 hour)
1. After validation passes, remove `ortools` from requirements.txt
2. **DELETE** `app/services/optimization_v2.py` (OR-Tools wrapper only)
3. **DELETE** `app/services/optimization.py` (old version)
4. **KEEP** `app/ml/scoring/movement_scorer.py` (decision tree logic)
5. Remove feature flag
6. Update documentation

### Second-Order Effects
- All 57 unit tests for diversity scoring must be updated
- SessionQualityKPI validation may need threshold adjustments
- Progressive relaxation logic may need tuning for greedy algorithm

### Third-Order Effects
- Performance regression if greedy selection is slower
- May need to implement caching for movement scores
- Documentation updates for new architecture

---

## Problem 4: Enum Duplications and Type Safety Issues

### Root Causes

**MovementRuleType Duplicates:**
- `HARD_NO` = `EXCLUDE` (never include)
- `HARD_YES` = `INCLUDE` (must include)
- `PREFERRED` = `BIAS` (prefer/bias)

**SkillLevel/ExperienceLevel Mismatch:**
- Frontend has `ELITE` value, backend only has `EXPERT`

**PrimaryMuscle Incomplete:**
- Backend has `ABDUCTORS` but missing from PrimaryMuscle enum
- Frontend has `adductors` but missing `abductors`

**Invalid Muscle References:**
- Test files use 'shoulders' and 'back' which don't exist in types

### Implementation Plan

**Phase 4.1: Remove MovementRuleType Duplicates** (30 min)
1. Update `app/models/enums.py` - Remove INCLUDE, EXCLUDE, BIAS
2. Update `frontend/src/types/index.ts` - Remove INCLUDE, EXCLUDE, BIAS
3. Verify no code uses these values (already confirmed)
4. No database migration needed (only 3 values in schema)

**Phase 4.2: Fix SkillLevel/ExperienceLevel** (2 hours)
1. Backend: Remove `ELITE = "elite"` from SkillLevel in enums.py
2. Frontend: Remove `ELITE = 'elite'` from both SkillLevel and ExperienceLevel
3. Database migration:
   ```python
   def upgrade():
       op.execute("UPDATE movements SET skill_level = 'expert' WHERE skill_level = 'elite'")
       # Alter enum to remove 'elite' value
   ```
4. Update scoring logic (enrich_movement_data.py) - Map ELITE to EXPERT
5. Update seed data if it contains elite values

**Phase 4.3: Add ABDUCTORS to PrimaryMuscle** (1 hour)
1. Backend: Add `ABDUCTORS = "abductors"` to PrimaryMuscle enum
2. Frontend: Add `'abductors'` to MuscleGroup type in anatomy.ts
3. Add to ZONE_MAPPING (map to lower_body zone)
4. Add to MUSCLE_DISPLAY_NAMES
5. Database migration:
   ```python
   def upgrade():
       # Add 'abductors' to enum
       # No data migration needed (no existing values)
   ```

**Phase 4.4: Fix Invalid Muscle References** (30 min)
1. Update CircuitDisplay.test.tsx - Replace 'shoulders' → 'side_delts', 'back' → 'upper_back'
2. Update CircuitDisplayExample.tsx - Same replacements
3. Update USAGE_EXAMPLES.tsx - Same replacements
4. Run frontend tests to verify no other invalid references

**Phase 4.5: Strengthen Loose Typing** (1 hour)
Replace `Record<string, unknown>` with specific interfaces:
1. `hybrid_definition` → `HybridDefinition` interface
2. `exercises_json` → `ExerciseJson[]` type
3. `exercises_completed` → `CompletedExercise[]` type
4. `raw_payload` → `PayloadData` interface

### Second-Order Effects
- Database migrations require production deployment coordination
- Seed data may need updates
- Test fixtures with elite/abductors values must be updated

### Third-Order Effects
- API contracts with external integrations may break
- Frontend visual components need re-testing with correct muscle groups
- Documentation must be updated to reflect enum changes

---

## Testing Strategy

### Unit Tests (Update Required)
- `tests/test_optimization_v2_integration.py` → Port to greedy optimizer
- `tests/test_diversity_scoring.py` → Update for unified config
- `frontend/src/components/circuit/CircuitDisplay.test.tsx` → Fix muscle references

### Integration Tests (Add Required)
- Program UI component integration tests
- Greedy optimizer A/B comparison tests
- Database migration rollback tests

### Regression Tests (Add Required)
- Frontend loading smoke tests (verify no broken imports)
- Enum consistency tests (frontend ↔ backend)
- API contract tests (schema validation)

### Performance Benchmarks
- Greedy vs OR-Tools solve time comparison
- Bundle size optimization (current: 684 kB)
- Session quality KPI scores (maintain or improve)

---

## Risk Assessment & Mitigation

| Phase | Risk Level | Mitigation |
|-------|------------|------------|
| Spinner consolidation | LOW | Feature flag for gradual rollout |
| Program UI | MEDIUM | A/B test with existing page |
| OR-Tools removal | HIGH | Keep both implementations during validation |
| Enum cleanup | HIGH | Comprehensive backup before migrations |
| Type safety | MEDIUM | TypeScript strict mode enforcement |

---

## Execution Order (Recommended)

**Week 1:**
1. Fix frontend loading issues (Phases 1.1-1.4)
2. Remove MovementRuleType duplicates (Phase 4.1)
3. Fix invalid muscle references (Phase 4.4)

**Week 2:**
4. Fix SkillLevel enum (Phase 4.2)
5. Add ABDUCTORS to PrimaryMuscle (Phase 4.3)
6. Create unified optimization config (Phase 3.1)

**Week 3:**
7. Implement greedy optimizer (Phase 3.2)
8. Migrate session generator (Phase 3.3)
9. Create program UI components (Phase 2.1)

**Week 4:**
10. Rewrite program.$programId.tsx (Phase 2.2)
11. Comprehensive testing (Phases 3.4, all regression tests)
12. Remove OR-Tools (Phase 3.5)
13. Final cleanup and documentation

---

## Success Criteria

- ✅ No frontend loading errors (Spinner standardized, imports consistent)
- ✅ Complete program UI with all data fields displayed
- ✅ Single optimization system (greedy + GlobalMovementScorer, no OR-Tools)
- ✅ No enum duplicates (MovementRuleType cleaned, SkillLevel/PrimaryMuscle consistent)
- ✅ All tests passing (unit + integration + regression)
- ✅ Performance maintained or improved (solve time < 1s)
- ✅ Database migrations successful (zero data loss)
- ✅ Frontend bundle size reduced (< 500 kB)