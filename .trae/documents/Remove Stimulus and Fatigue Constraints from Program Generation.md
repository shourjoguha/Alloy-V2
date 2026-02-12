# Plan: Remove Stimulus and Fatigue Constraints from Program Generation

## Executive Summary
This plan removes stimulus_factor and fatigue_factor from **decision-making** throughout the program generation flow. This is a subtraction effort that removes these variables from the optimizer, session generator, and constraint systems while preserving the underlying data structures.

## Philosophy: Subtraction Over Addition
- Remove fatigue/stimulus as **decision-making variables** (constraints, selection criteria)
- Keep data structures intact (don't break existing data/API contracts)
- Simplify the optimization problem space to reduce over-constraint failures

---

## Phase 1: Remove from Optimization Engine (Greedy Optimizer)

### Files to Modify:
- `app/services/greedy_optimizer.py`
- `app/services/optimization_types.py`

### Changes:
1. **Remove fatigue constraint enforcement**:
   - Remove lines 233-235: max_fatigue calculation
   - Remove lines 250, 274-278: fatigue budget tracking and constraint checks
   - Remove lines 311-314: circuit fatigue constraint checks

2. **Remove stimulus constraint enforcement**:
   - Remove lines 326-327: total_stimulus calculation from result
   - Keep total_fatigue calculation for result reporting only

3. **Update OptimizationRequestV2**:
   - Remove `max_fatigue` parameter (line 55)
   - Remove `min_stimulus` parameter (line 56)

4. **Update OptimizationResultV2**:
   - Remove `total_stimulus` from result (line 89)
   - Remove `total_fatigue` from result (line 88)

### Risk: CRITICAL - Greedy optimizer will accept any movement without fatigue limits
**Mitigation**: Add set-count and time-based constraints to prevent infinite movement selection

---

## Phase 2: Remove from Session Generator

### Files to Modify:
- `app/services/session_generator.py`
- `app/config/optimization_config_loader.py`

### Changes:
1. **Remove constraint construction**:
   - Remove lines 844-845: max_fatigue and min_stimulus from optimization request

2. **Remove fatigue-based classification**:
   - Line 2255: Change `is_main` logic to only use `compound and is_complex_lift`
   - Remove `fatigue_factor > 0.6` condition

3. **Remove reasoning message**:
   - Line 2289: Remove stimulus/fatigue from coach notes

4. **Keep SolverMovement/SolverCircuit creation**:
   - Keep lines 2016-2017, 2131-2132: Keep passing these fields
   - **Rationale**: Preserve API contracts, just don't use them for decisions

5. **Remove from configuration**:
   - `app/config/optimization_config.yaml`: Remove max_fatigue: 8.0
   - `app/config/optimization_config_loader.py`: Remove max_fatigue from ORToolsConfig

---

## Phase 3: Remove from Circuit Metrics Calculation

### Files to Modify:
- `app/services/circuit_metrics.py`

### Changes:
1. **Remove fatigue_factor from circuit metrics**:
   - Line 88: Remove _apply_fatigue_modifier() call
   - Lines 154-160: Remove _calculate_base_fatigue() function
   - Lines 162-185: Remove _apply_fatigue_modifier() function

2. **Remove stimulus_factor from circuit metrics**:
   - Line 92: Remove _adjust_stimulus_for_volume() call
   - Lines 187-193: Remove _calculate_base_stimulus() function

3. **Update calculate_circuit_metrics() return**:
   - Remove `fatigue_factor` from return dict (line 40)
   - Remove `stimulus_factor` from return dict (line 41)
   - Keep other metrics (muscle_volume, muscle_fatigue as derived from sets/reps)

4. **Update muscle metrics calculation**:
   - Line 257: Change to use sets/reps instead of fatigue_factor
   - Formula: `movement_fatigue = m.sets * m.reps * 0.01` (simplified proxy)

---

## Phase 4: Remove from Workout Logging

### Files to Modify:
- `app/api/routes/logs.py`

### Changes:
1. **Remove stimulus/fatigue accumulation**:
   - Lines 92-93: Remove stimulus/fatigue stats accumulation
   - Keep cns_fatigue (uses CNSLoad enum, independent of fatigue_factor)

2. **Keep Session model fields populated with 0**:
   - Lines 178-179: Set to 0.0 instead of removing
   - **Rationale**: Preserve DB schema, just stop calculating

---

## Phase 5: Update Tests

### Files to Modify:
- `tests/test_optimization_v2_integration.py`

### Changes:
1. **Remove constraint assertions**:
   - Line 315: Remove `assert result.total_fatigue <= request.max_fatigue`
   - Lines 718-721: Remove fatigue/stimulus bound assertions

2. **Update test data**:
   - Keep movement test data with fatigue_factor/stimulus_factor
   - **Rationale**: Test data structure unchanged, just not used in decisions

3. **Add new assertions**:
   - Assert session duration within bounds
   - Assert movement count within bounds
   - Assert set count within bounds

---

## Phase 6: Frontend Updates (Graceful Degradation)

### Files to Modify:
- `frontend/src/types/index.ts`
- `frontend/src/components/circuit/` components

### Changes:
1. **Keep TypeScript types**:
   - Keep `fatigue_factor` and `stimulus_factor` in interfaces
   - Mark as optional if API might omit them

2. **Add graceful handling**:
   - Use optional chaining: `circuit.fatigue_factor ?? 1.0`
   - Display as "N/A" or hide if not present

3. **Don't break existing displays**:
   - Keep showing values if present (historical data)
   - Just don't require them for new data

---

## Phase 7: Database Schema (No Changes)

### Decision: **DO NOT DROP COLUMNS**

### Rationale:
1. **Preserve historical data**: Existing sessions have calculated values
2. **Preserve API contracts**: Frontend may still expect these fields
3. **Preserve Movement base data**: fatigue_factor/stimulus_factor are movement attributes
4. **Migration risk**: Dropping columns is irreversible

### Alternative: Deprecation Strategy
- Add comment: `# DEPRECATED: No longer used in optimization decisions`
- Future migration can remove after 2-3 release cycles

---

## Second-Order Effects

### Effect 1: Reduced Constraint Complexity
- **Positive**: Larger feasible solution space, fewer "no solution found" failures
- **Positive**: Faster optimization (fewer constraint checks)
- **Negative**: May produce less balanced sessions (no fatigue management)

### Effect 2: Main Lift Classification Changes
- **Current**: `fatigue_factor > 0.6` determines main lift
- **After**: Only `compound and is_complex_lift` determines main lift
- **Impact**: More movements classified as "main lifts"
- **Mitigation**: Add explicit main lift flag or limit main lift count in session template

### Effect 3: Emergency Mode Ineffective
- **Current**: Emergency mode increases fatigue budget by 1.5x
- **After**: Fatigue constraint doesn't exist, multiplier has no effect
- **Impact**: Emergency mode becomes a no-op
- **Mitigation**: Replace emergency mode with "fewer movements" or "longer rest periods"

### Effect 4: Loss of Training Intelligence
- **Impact**: Cannot distinguish light warmup from heavy deadlift in decision-making
- **Mitigation**: Use `cns_load`, `compound`, `is_complex_lift` as proxies for difficulty

### Effect 5: Circuit Metrics Degraded
- **Impact**: Circuit fatigue/stimulus factors no longer calculated
- **Mitigation**: Use circuit type (TABATA, AMRAP) as difficulty proxy

---

## Third-Order Effects

### Effect 1: Analytics Impact
- **Impact**: Session-level total_stimulus/total_fatigue will always be 0
- **Mitigation**: Migrate analytics to use volume, sets, reps, duration

### Effect 2: User Experience Changes
- **Impact**: Sessions may feel more intense (no fatigue limiting heavy movements)
- **Mitigation**: Add user feedback loop to adjust difficulty

### Effect 3: Data Consistency Issues
- **Impact**: Old programs have stimulus/fatigue values, new ones don't
- **Mitigation**: This is expected; analytics can handle missing values

---

## Blindspots Identified

### Blindspot 1: Muscle-Level Fatigue Calculation
- **Risk**: CircuitMetricsCalculator uses fatigue_factor for muscle-level fatigue
- **Mitigation**: Replace with sets × reps × weight formula

### Blindspot 2: ML/Scoring Components
- **Risk**: Unknown if movement_scorer.py uses these variables
- **Action**: Review movement_scorer.py before execution

### Blindspot 3: External Scripts
- **Risk**: enrich_movement_data.py and populate_circuit_metrics.py may fail
- **Mitigation**: Update scripts to skip these calculations

### Blindspot 4: Progressive Relaxation Strategy
- **Risk**: Optimization config has emergency mode with fatigue_multiplier
- **Mitigation**: Remove or repurpose this config option

---

## Testing Strategy

### Unit Tests:
1. Test greedy optimizer without fatigue/stimulus constraints
2. Test session generator without constraint construction
3. Test circuit metrics without fatigue/stimulus calculation

### Integration Tests:
1. Test full program generation flow
2. Test workout logging
3. Test all API endpoints return valid responses

### Regression Tests:
1. Compare old vs. new program generation quality
2. Measure "no solution found" rate (should decrease)
3. Verify session duration still within bounds

### Rollback Plan:
1. Git revert all changes
2. Database schema unchanged (no rollback needed)
3. Frontend changes can be deployed independently

---

## Execution Order

1. **Phase 1**: Greedy optimizer (core decision logic)
2. **Phase 2**: Session generator (connects optimizer to session)
3. **Phase 3**: Circuit metrics (supports session generation)
4. **Phase 4**: Workout logging (doesn't affect generation)
5. **Phase 5**: Tests (validate changes)
6. **Phase 6**: Frontend (graceful degradation, not critical path)
7. **Phase 7**: Database (no changes, documentation only)

---

## Estimated Impact

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Files modified | - | 7 | +7 |
| Lines removed | - | ~100 | -100 |
| Decision variables | 13 | 11 | -2 |
| Constraint checks | 3 | 1 | -2 |
| Risk of "no solution" | High | Lower | Improved |
| Session balance | High | Unknown | To be measured |

---

## Success Criteria

1. ✅ Program generation succeeds without stimulus/fatigue constraints
2. ✅ No AttributeError crashes in any code path
3. ✅ Frontend still displays data gracefully
4. ✅ Test suite passes (with updated assertions)
5. ✅ "No solution found" rate decreases
6. ✅ Session duration remains within target bounds