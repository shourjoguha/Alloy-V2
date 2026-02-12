# Diversity-Based Movement Scoring System Implementation Plan

## Overview
Replace stimulus/fatigue constraint-based optimization with configurable decision tree scoring system for movement selection.

---

## Phase 1: Configuration Infrastructure (1-2 days)

### 1.1 Create YAML Configuration Schema
**File**: `app/config/movement_scoring.yaml`

**Key Sections**:
- `scoring_dimensions`: 6-level priority hierarchy (pattern_alignment, muscle_coverage, discipline_preference, compound_bonus, specialization, goal_alignment, time_utilization)
- `pattern_compatibility_matrix`: Pattern substitution rules (squat ↔ hinge ↔ lunge, etc.)
- `muscle_relationships`: Primary/synergist/related muscle mappings
- `goal_profiles`: Goal-specific weight modifiers (strength, hypertrophy, endurance, fat_loss, explosiveness, speed, calisthenics)
- `discipline_modifiers`: Olympic (explosiveness), Plyometric (speed), Calisthenics (calisthenics)
- `hard_constraints`: Equipment, variety, time, user movement rules
- `rep_set_ranges`: Per-block ranges (warmup, main/strength, main/hypertrophy, accessory, cooldown) - circuits exempt
- `global_config`: Normalization, tie-breaking, relaxation strategy, debug settings

### 1.2 Create Configuration Loader
**File**: `app/ml/scoring/config_loader.py`

**Classes**:
- `YAMLConfigLoader`: Load, validate, and hot-reload YAML config
- Methods: `load_config()`, `reload_config()`, `validate_schema()`

---

## Phase 2: Scoring Engine (2-3 days)

### 2.1 Create Decision Tree Scorer
**File**: `app/ml/scoring/movement_scorer.py`

**Classes**:
- `ScoringRule`: Single rule (condition + score)
- `ScoringDimension`: Complete dimension with rules and weight
- `ScoringResult`: Score breakdown with dimension scores and qualification status
- `GlobalMovementScorer`: Main scorer class

**Key Methods**:
- `score_movement(movement, context)`: Evaluate all enabled dimensions in priority order
- `_evaluate_dimension(dimension, movement, context)`: Apply dimension's rules
- `_apply_goal_modifiers(scores, user_goals)`: Adjust scores based on goal-specific modifiers

**Normalization**:
- User discipline preferences (1-5 scale) → 0-1 float (divide by 5.0)
- All discipline weights normalized to sum = 1.0
- Variance contribution logged for each dimension

### 2.2 Create Metrics Tracker
**File**: `app/ml/scoring/scoring_metrics.py`

**Classes**:
- `ScoringMetrics`: Single session metrics (success, movement_count, time_utilization, pattern_diversity, muscle_coverage, dimension_scores)
- `ScoringMetricsTracker`: Collection and analysis

**Key Methods**:
- `record_session(result, context)`: Store metrics in structured log format
- `get_success_rate()`: (successful sessions / total sessions)
- `get_dimension_effectiveness()`: Analyze which dimensions work best

**Success Rate Definition** (sessions meeting ALL criteria):
1. Structural completeness: warmup + main + (accessory/finisher) + cooldown
2. Movement count: ≥8 (regular/cardio/conditioning), ≤15 (finisher = 1 unit)
3. Time utilization: ±5% of target duration
4. Pattern diversity: Depends on session type (no hard number)
5. Muscle coverage: No major muscle group missed in microcycle
6. Hard constraint compliance: Equipment, variety, time, user rules

---

## Phase 3: Optimization Service Integration (2-3 days)

### 3.1 Create New Optimization Service
**File**: `app/services/optimization_v2.py`

**Classes**:
- `DiversityOptimizationService`: Main optimization service

**Key Methods**:
- `solve_session_with_diversity_scoring(request)`: Solve using new scoring system
- `_build_objective_function(movement_vars, context)`: Use GlobalMovementScorer
- `_apply_hard_constraints(model, movement_vars, sets_vars, request)`: Equipment, variety, time
- `_progressive_relaxation(model, request)`: 6-step relaxation

**Progressive Relaxation Steps**:
1. Expand pattern compatibility matrix
2. Include synergist muscles
3. Reduce discipline weight (0.7× multiplier)
4. Accept isolation movements
5. Accept generic movements
6. Emergency selection (minimal constraints)

### 3.2 Modify Session Generator
**File**: `app/services/session_generator.py`

**Changes**:
- Replace `OptimizationService` import with `DiversityOptimizationService`
- Modify `_generate_draft_session_offline()` to call new optimizer
- Pass `disciplines_json` context to optimizer (currently loaded but not used)
- Update optimization request to include user settings, goals, preferences

### 3.3 Integrate Discipline Preferences
**File**: `app/services/optimization_v2.py`

**Implementation**:
- Load `disciplines_json` from context
- Normalize discipline preferences (1-5 → 0-1)
- Apply goal-specific modifiers:
  - Explosiveness goal → olympic_weightlifting ×1.5
  - Speed goal → plyometric ×1.5
  - Calisthenics goal → calisthenics ×1.5
- Normalize all discipline weights to sum = 1.0

---

## Phase 4: Session Quality KPIs (1-2 days)

### 4.1 Implement Block-Specific Movement Counts
**File**: `app/ml/scoring/session_quality_kpi.py`

**Classes**:
- `SessionQualityKPI`: Block-specific validation

**Rules**:
- Warmup: 2-5 movements
- Cooldown: 2-5 movements
- Main: 2-5 (strength/hypertrophy/cardio), 6-10 (endurance)
- Accessory: 2-4 movements
- Finisher: 1 unit (circuit counted as whole, not individual movements)

### 4.2 Implement Movement Variety KPIs
**File**: `app/ml/scoring/variety_kpi.py`

**Classes**:
- `MovementVarietyKPI`: Track variety across microcycle

**Methods**:
- `check_pattern_rotation(current_session, previous_sessions)`: No pattern repeats within 2 sessions of SAME TYPE (CARDIO/CONDITIONING/REGULAR)
- `calculate_unique_movements_in_microcycle(microcycle)`: % unique movements

### 4.3 Implement Muscle Coverage KPIs
**File**: `app/ml/scoring/muscle_coverage_kpi.py`

**Classes**:
- `MuscleCoverageKPI`: Track muscle group coverage

**Methods**:
- `check_microcycle_coverage(microcycle_sessions)`: Ensure no major muscle group missed
- Major muscles: quadriceps, hamstrings, glutes, chest, lats, upper_back, shoulders

---

## Phase 5: Testing & Validation (2-3 days)

### 5.1 Unit Tests
**File**: `tests/test_diversity_scoring.py`

**Test Cases**:
- `test_global_movement_scorer_basic_scoring()`: Basic scoring logic
- `test_discipline_normalization()`: 1-5 → 0-1 normalization
- `test_goal_modifiers()`: Explosiveness → olympic boost, Speed → plyometric boost
- `test_pattern_compatibility()`: Squat ↔ hinge ↔ lunge rotation
- `test_progressive_relaxation()`: 6-step relaxation

### 5.2 Integration Tests
**File**: `tests/test_optimization_v2_integration.py`

**Test Cases**:
- `test_generate_session_with_diversity_scoring()`: Full session generation
- `test_discipline_preferences_influence()`: Verify discipline weights affect selection
- `test_goal_conflict_resolution()`: Strength + Endurance weight reduction
- `test_circuit_exemption()`: Circuits bypass rep_set_ranges
- `test_success_rate_calculation()`: Verify all 6 criteria

### 5.3 Validation Against Program 240
**File**: `tests/test_program_240_validation.py`

**Test Cases**:
- Verify all sessions have warmup + main + (accessory/finisher) + cooldown
- Verify movement counts meet block-specific thresholds
- Verify pattern rotation by session type (REGULAR/CARDIO/CONDITIONING)
- Verify muscle coverage across microcycle
- Verify Olympic preference (level 2) with explosiveness goal increases olympic movement selection

---

## Phase 6: Migration & Rollout (1-2 days)

### 6.1 Feature Flag Implementation
**File**: `app/config/features.py`

**Configuration**:
```python
FEATURE_FLAGS = {
    "use_diversity_scoring": False,  # Start False, enable after testing
    "enable_metrics_logging": True,  # Start logging immediately
}
```

### 6.2 Gradual Rollout Strategy
**Week 1**: Feature flag = False, metrics logging = True (collect baseline data)
**Week 2**: Feature flag = True for test users only
**Week 3**: Feature flag = True for all users, monitor success rates

### 6.3 Rollback Plan
**If New System Fails**:
1. Set `FEATURE_FLAGS["use_diversity_scoring"] = False` (instant rollback)
2. If that fails, checkout `backup/pre-diversity-scoring-stable` branch
3. If that fails, restore database: `psql -U gainsly -d gainslydb < backup_before_diversity_scoring_20260209_004106.sql`

---

## Phase 7: API Endpoints (1 day)

### 7.1 Config Management Endpoints
**File**: `app/api/routes/scoring_config.py`

**Endpoints**:
- `GET /scoring/config`: View current config (admin only)
- `POST /scoring/config/reload`: Hot-reload config (admin only)
- `POST /scoring/config/validate`: Validate YAML schema (admin only)

### 7.2 Metrics Endpoints
**File**: `app/api/routes/scoring_metrics.py`

**Endpoints**:
- `GET /scoring/metrics/{user_id}`: Get scoring metrics (admin only)
- `GET /scoring/metrics/summary`: Aggregate metrics across all users (admin only)

---

## Key Implementation Details

### Equipment Constraint Collection
**Current State**: Equipment constraints collected from `UserProfile.equipment_available` field (JSON field in user.py:179)
**Implementation**: Add to optimization request context as hard filter

### Goal Conflict Resolution
**Approach**:
- **High severity** (strength vs endurance): Block program creation, require separate days
- **Medium severity** (strength vs hypertrophy): Show warning, apply 30% weight reduction to both goals
- **Low severity** (endurance vs fat_loss): Proceed with adjustment (fat_loss favors cardio, endurance favors finishers)

### Variable Hierarchy Normalization
**Approach**:
- Calculate each dimension's contribution to final score
- Log variance contribution for analysis
- Use z-score normalization (mean=0, std=1) for comparison

### Rep/Set Range Per-Block Configuration
**Implementation**:
- Program-wide defaults in YAML
- Individual sessions reference these defaults
- Circuits exempt (use circuit_macro and circuit_melted data)
- Goal-specific main block ranges (strength: 4-6 sets, 2-5 reps; hypertrophy: 3-4 sets, 6-12 reps)

---

## Files to Create (15 files)
1. `app/config/movement_scoring.yaml` - Main configuration
2. `app/ml/scoring/config_loader.py` - Config loader
3. `app/ml/scoring/movement_scorer.py` - Decision tree scorer
4. `app/ml/scoring/scoring_metrics.py` - Metrics tracker
5. `app/ml/scoring/session_quality_kpi.py` - Quality KPIs
6. `app/ml/scoring/variety_kpi.py` - Variety KPIs
7. `app/ml/scoring/muscle_coverage_kpi.py` - Muscle coverage KPIs
8. `app/services/optimization_v2.py` - New optimization service
9. `app/config/features.py` - Feature flags
10. `app/api/routes/scoring_config.py` - Config management API
11. `app/api/routes/scoring_metrics.py` - Metrics API
12. `tests/test_diversity_scoring.py` - Unit tests
13. `tests/test_optimization_v2_integration.py` - Integration tests
14. `tests/test_program_240_validation.py` - Program 240 validation
15. `tests/conftest_scoring.py` - Scoring test fixtures

## Files to Modify (3 files)
1. `app/services/session_generator.py` - Replace optimization service
2. `app/services/program.py` - Add goal conflict resolution
3. `app/config/heuristics.py` - Keep for reference, mark deprecated

---

## Timeline Estimate
- **Phase 1-2**: 3-5 days
- **Phase 3**: 2-3 days
- **Phase 4**: 1-2 days
- **Phase 5**: 2-3 days
- **Phase 6**: 1-2 days
- **Phase 7**: 1 day

**Total**: 10-16 days

---

## Cloud Hosting (Future Task)
- **Current approach**: Local YAML file with hot-reload
- **Future migration**: Render + Netlify + Supabase (simplest, cheapest for <100 users)
- **Migration path**: Export from local YAML → Supabase Storage → S3 (if needed)

---

## Rollback Confirmation
✅ Database backup: `backup_before_diversity_scoring_20260209_004106.sql` (6.9MB)
✅ Git backup: `backup/pre-diversity-scoring-stable` pushed to origin
✅ Feature branch: `feature/diversity-scoring-system` ready

**Rollback Steps**:
1. Disable feature flag: `FEATURE_FLAGS["use_diversity_scoring"] = False`
2. If needed, checkout backup branch: `git checkout backup/pre-diversity-scoring-stable`
3. If needed, restore database: `docker exec alloy psql -U gainsly -d gainslydb < backup_before_diversity_scoring_20260209_004106.sql`