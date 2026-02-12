# RPE Suggestion System Implementation Plan

## Executive Summary
Implement intelligent RPE suggestions for session generation that adapt to program type, movement characteristics, training frequency, and user recovery state. This aligns with the core philosophy that **fatigue and stimulus are NOT inherent movement properties** - they are functions of **how movements are used (RPE 1-10)**.

---

## Phase 1: Configuration Updates (Week 1)

### 1.1 Update movement_scoring.yaml with MAX_HIGH_RPE_SETS_PER_SESSION
Add the user-provided configuration:
```yaml
# Max high-RPE (≥8) sets per session by pattern
max_high_rpe_sets_per_session:
  hinge: 6
  squat: 6
  lunge: 6
  olympic: 6
  horizontal_push: 12
  vertical_push: 12
  horizontal_pull: 12
  vertical_pull: 12
  # Note: These sets can be across multiple movements (e.g., 2 hinge movements × 3 sets each = 6 total)
```

### 1.2 Add RPE configuration section to optimization_config.yaml
```yaml
# ---------------------------------------------------------------------------
# RPE SUGGESTION CONFIGURATION
# ---------------------------------------------------------------------------
rpe_suggestion:
  # RPE ranges by exercise role
  warmup_rpe: [1, 3]
  main_strength_rpe: [7, 9]
  main_hypertrophy_rpe: [6, 8]
  accessory_rpe: [5, 7]
  cooldown_rpe: [1, 3]
  circuit_rpe: [5, 8]
  
  # RPE ranges by program type
  program_type_profiles:
    strength:
      primary_compound_rpe: [7.5, 9.5]
      accessory_rpe: [6, 8]
      weekly_high_rpe_sets_max: 12  # For 3-4 day/week
      microcycle_progression:
        accumulation: [6.5, 7.5]
        intensification: [7.5, 8.5]
        peaking: [8, 9.5]
        deload: [4, 5.5]
    
    hypertrophy:
      primary_compound_rpe: [6.5, 8.5]
      accessory_rpe: [6, 7.5]
      weekly_high_rpe_sets_max: 16  # For 4-5 day/week
      microcycle_progression:
        volume_phase: [7, 8]
        intensity_phase: [7.5, 8.5]
        fatigue_mgmt: [6, 7]
        deload: [4, 6]
    
    endurance:
      primary_compound_rpe: [5.5, 7.5]
      accessory_rpe: [6, 8]
      weekly_high_rpe_sets_max: 20  # For 5-6 day/week
      microcycle_progression:
        daily_undulating: true  # RPE waves through week
    
    power:
      primary_compound_rpe: [7, 8.5]
      accessory_rpe: [6, 8]
      weekly_high_rpe_sets_max: 8   # Quality-focused
      microcycle_progression:
        wave_loading: true  # RPE: 7 → 8 → 7.5 → 8.5
  
  # RPE adjustments by CNS load and discipline
  cns_discipline_adjustments:
    high_cns_olympic_powerlifting:
      rpe_cap: 8.5  # Maximum RPE for these movements
      weekly_limit: 3   # Max sets at RPE 8+
    
    moderate_cns_compound:
      rpe_cap: 9.5
      weekly_limit: 6
  
  # Recovery-based RPE reductions
  fatigue_adjustments:
    sleep_under_6h: -0.5
    sleep_under_5h: -1.0
    hrv_below_baseline_20pct: -1.0
    soreness_above_7: -1.0
    consecutive_high_rpe_days: -0.5  # After 2+ consecutive high-RPE sessions
  
  # Recovery time multipliers by RPE
  recovery_hours_by_rpe:
    rpe_6_7: 24  # Minimum hours before same pattern
    rpe_8: 48
    rpe_9: 72
    rpe_10: 96  # 4 days for max effort
```

---

## Phase 2: Database Schema Updates (Week 1)

### 2.1 Add RPE suggestion tracking to SessionExercise
```python
# New fields in SessionExercise model
suggested_rpe_min = Column(Float, nullable=True)
suggested_rpe_max = Column(Float, nullable=True)
rpe_adjustment_reason = Column(String(100), nullable=True)  # e.g., "low_sleep", "recovery_day"
```

### 2.2 Add microcycle RPE tracking
```python
# New fields in Microcycle model
microcycle_phase = Column(String(50), nullable=True)  # accumulation, intensification, peaking, deload
rpe_intensity_factor = Column(Float, nullable=True)  # 0.5 = deload, 1.0 = normal, 1.2 = peak
```

### 2.3 Add pattern recovery tracking
```python
# New table: PatternRecoveryState
__tablename__ = "pattern_recovery_states"
pattern = Column(SQLEnum(MovementPattern), nullable=False, primary_key=True)
last_trained_at = Column(DateTime, nullable=False)
last_rpe = Column(Float, nullable=False)
recovery_hours_required = Column(Integer, nullable=False)  # Dynamic based on RPE
```

---

## Phase 3: Core RPE Service Implementation (Week 2-3)

### 3.1 Create RPE Suggestion Service
**File:** `app/services/rpe_suggestion_service.py`

```python
class RPESuggestionService:
    """
    Intelligent RPE suggestion service that considers:
    - Program type and phase
    - Movement characteristics (pattern, CNS load, discipline)
    - Training frequency and weekly volume
    - User recovery state
    - Pattern recovery status
    """
    
    async def suggest_rpe_for_movement(
        self,
        movement: Movement,
        exercise_role: ExerciseRole,
        program_type: str,
        microcycle_phase: str,
        training_days_per_week: int,
        session_high_rpe_sets_count: int,
        user_recovery_state: dict,
        pattern_recovery_hours: dict,
    ) -> tuple[float, float, str]:
        """
        Returns (min_rpe, max_rpe, adjustment_reason)
        """
        
    async def suggest_rpe_for_session(
        self,
        session_type: SessionType,
        program_type: str,
        microcycle_phase: str,
        user_goals: list[Goal],
        user_recovery_state: dict,
        weekly_high_rpe_sets_count: int,
    ) -> dict[str, tuple[float, float]]:
        """
        Returns exercise_role -> (min_rpe, max_rpe) mapping
        """
    
    def _get_base_rpe_range(
        self,
        exercise_role: ExerciseRole,
        program_type: str,
        microcycle_phase: str,
    ) -> tuple[float, float]:
        """Get base RPE range from config"""
    
    def _apply_cns_discipline_cap(
        self,
        movement: Movement,
        base_min: float,
        base_max: float,
    ) -> tuple[float, float]:
        """Apply RPE caps for high-CNS movements"""
    
    def _apply_fatigue_adjustments(
        self,
        base_min: float,
        base_max: float,
        recovery_state: dict,
    ) -> tuple[float, float, str]:
        """Reduce RPE based on recovery signals"""
    
    def _check_pattern_recovery_constraint(
        self,
        movement: Movement,
        suggested_rpe: float,
        pattern_recovery_hours: dict,
    ) -> tuple[float, float]:
        """Adjust RPE if pattern hasn't recovered"""
```

### 3.2 Update Session Generator RPE Logic
**File:** `app/services/session_generator.py`

Changes in `_generate_draft_session()`:
1. Load RPE suggestion service
2. Get program type and microcycle phase
3. Call `suggest_rpe_for_session()` for exercise role mapping
4. For each selected movement:
   - Call `suggest_rpe_for_movement()` with full context
   - Apply pattern recovery constraints
   - Set `suggested_rpe_min` and `suggested_rpe_max` on SessionExercise
   - Capture `rpe_adjustment_reason`

---

## Phase 4: Recovery Mechanics Updates (Week 3-4)

### 4.1 Update Pattern Recovery Calculation
**File:** `app/services/adaptation.py`

```python
def calculate_pattern_recovery_hours(
    last_rpe: float,
    cns_load: CNSLoad,
    discipline: DisciplineType | None,
) -> int:
    """
    Calculate required recovery hours based on:
    - Last RPE (6-10 scale)
    - Movement CNS load (moderate, high, very_high)
    - Discipline (olympic/powerlifting = longer recovery)
    
    Base formula:
    - RPE 6-7: 24 hours (minimum)
    - RPE 8: 48 hours
    - RPE 9: 72 hours
    - RPE 10: 96 hours
    
    Modifiers:
    - High CNS load: +24 hours
    - Olympic/powerlifting: +24 hours
    - Isolation: -12 hours (can recover faster)
    """
```

### 4.2 Update Muscle Recovery Decay
**File:** `app/api/routes/logs.py`

Current decay: 1 point per 10 hours (hardcoded)
**Update:** Make configurable and RPE-aware

```python
# New decay logic based on last training RPE
def calculate_recovery_decay(
    recovery_level: int,
    hours_since_update: int,
    last_rpe: float,  # New parameter
) -> int:
    """
    Decay rate depends on last RPE:
    - RPE 6-7: 1 point per 8 hours
    - RPE 8: 1 point per 10 hours
    - RPE 9: 1 point per 12 hours
    - RPE 10: 1 point per 16 hours
    
    Higher RPE = slower decay (longer recovery needed)
    """
```

---

## Phase 5: Test Implementation (Week 4-5)

### 5.1 Unit Tests
**File:** `tests/test_rpe_suggestion_service.py`

Test scenarios:
1. **Program type awareness**
   - Strength program → RPE 7.5-9.5 for compounds
   - Hypertrophy program → RPE 6.5-8.5 for compounds
   - Endurance program → RPE 5.5-7.5 for compounds

2. **CNS/discipline caps**
   - Olympic movement capped at RPE 8.5
   - Powerlifting movement capped at RPE 9.5
   - Isolation movement: no cap

3. **Fatigue adjustments**
   - Sleep < 6h → RPE -0.5
   - HRV -20% → RPE -1.0
   - Consecutive high-RPE days → RPE -0.5

4. **Pattern recovery**
   - Squat trained 24h ago at RPE 8 → Ready for RPE 7+
   - Squat trained 48h ago at RPE 9 → Ready for RPE 8+
   - Hinge trained 24h ago → Reduce to RPE 6-7

5. **Frequency constraints**
   - 3-day/week: Max 12 high-RPE sets
   - 5-day/week: Max 20 high-RPE sets
   - Within session: Hinge max 6, Push max 12

### 5.2 Integration Tests
**File:** `tests/test_rpe_integration.py`

Test scenarios:
1. **Full program generation**
   - Strength program, 4 days/week
   - Verify RPE distribution follows pattern
   - Verify weekly high-RPE set limits

2. **Real-world examples** (detailed below)

---

## Phase 6: Frontend Updates (Week 5-6)

### 6.1 TypeScript Type Updates
**File:** `frontend/src/types/index.ts`

```typescript
interface SessionExercise {
  // ... existing fields
  suggestedRpeMin?: number;
  suggestedRpeMax?: number;
  rpeAdjustmentReason?: string;
  rpeRangeDisplay?: string;  // e.g., "7-8", "6.5-8.5"
}

interface RPEDisplayMode {
  simple: boolean;  // Single value
  range: boolean;   // Show range
  adaptive: boolean; // Show fatigue-adjusted
}
```

### 6.2 SessionCard Component Updates
**File:** `frontend/src/components/program/SessionCard.tsx`

Display logic:
```typescript
// Progressive disclosure
const [showRPERange, setShowRPERange] = useState(false);

// RPE display
const rpeDisplay = showRPERange 
  ? `${exercise.suggestedRpeMin}-${exercise.suggestedRpeMax}`
  : `${exercise.targetRpe}`;  // Single value default

// Adjustment indicator
const adjustmentIcon = exercise.rpeAdjustmentReason
  ? <FatigueIcon reason={exercise.rpeAdjustmentReason} />
  : null;
```

### 6.3 Fatigue Dashboard (New Component)
**File:** `frontend/src/components/program/FatigueDashboard.tsx`

Display:
- Overall fatigue score (0-100)
- Pattern recovery timers (color-coded)
- Weekly high-RPE set count vs limit
- RPE adjustment history

---

## Real-World Examples

### Example 1: Strength Program (3 Days/Week)
**User Profile:** Advanced lifter, goal: strength, 3 days/week

**Week 1 (Accumulation Phase):**
```
Monday (Upper - RPE 7.5-8.5):
  Bench Press (compound):    RPE 7.5-8.5  × 4 sets
  Incline DB Press:         RPE 6.5-7.5  × 3 sets
  Lateral Raises:           RPE 6-7       × 3 sets
  
  High-RPE sets this session: 4 (all compound)
  Weekly high-RPE sets: 12/12 ✓

Wednesday (Lower - RPE 7.5-8.5):
  Squat (compound):          RPE 7.5-8.5  × 4 sets
  Romanian Deadlift (compound): RPE 6.5-7.5  × 3 sets
  Leg Extension:              RPE 6-7       × 3 sets
  
  High-RPE sets this session: 4
  Weekly high-RPE sets: 8/12

Friday (Full Body - RPE 7-8):
  Deadlift (compound):        RPE 7-8       × 3 sets
  Overhead Press:           RPE 6.5-7.5  × 3 sets
  Bent-Over Row:            RPE 6.5-7.5  × 3 sets
  
  High-RPE sets this session: 3
  Weekly high-RPE sets: 11/12 ✓
```

**Week 4 (Peaking Phase):**
```
Monday (Upper - RPE 8-9.5):
  Bench Press:              RPE 8.5-9.5  × 3 sets  (Top sets)
  Incline DB Press:         RPE 7-8       × 2 sets
  Lateral Raises:           RPE 6-7       × 3 sets
  
  Weekly high-RPE sets: 3/12 (lower volume, higher intensity)
```

**Deload Week:**
```
All exercises: RPE 4-6, 50% volume reduction
```

---

### Example 2: Hypertrophy Program (5 Days/Week)
**User Profile:** Intermediate lifter, goal: hypertrophy, 5 days/week

**Week 2 (Volume Phase):**
```
Monday (Push - RPE 7-8):
  Bench Press:              RPE 7-8       × 4 sets
  Incline DB Press:         RPE 7-8       × 3 sets
  Lateral Raises:           RPE 6-8       × 3 sets
  Triceps Pushdown:         RPE 7-8.5    × 3 sets  (Isolation can go higher)
  
  High-RPE sets: 4 (compound) + 1 (isolation) = 5/16

Wednesday (Pull - RPE 7-8):
  Pull-Ups:                 RPE 7-8       × 4 sets
  Bent-Over Row:            RPE 7-8       × 3 sets
  Face Pulls:              RPE 7-8.5    × 3 sets
  Bicep Curls:             RPE 7-9       × 3 sets
  
  High-RPE sets: 4 + 1 = 5/16

Friday (Legs - RPE 6.5-7.5):
  Squat:                   RPE 6.5-7.5  × 4 sets
  RDL:                      RPE 6-7       × 3 sets
  Leg Press:                RPE 6-7       × 3 sets
  Leg Curl:                 RPE 7-8       × 3 sets
  
  High-RPE sets: 4/16 (fatigue management)

Saturday (Upper - RPE 6-7):
  Incline DB Press:         RPE 6-7       × 3 sets
  DB Bench:                 RPE 6-7       × 3 sets
  Lateral Raises:           RPE 6-8       × 3 sets
  
  High-RPE sets: 0/16 (active recovery)

Sunday (Shoulders/Arms - RPE 7-8):
  Overhead Press:           RPE 7-8       × 3 sets
  Lateral Raises:           RPE 7-8.5    × 3 sets
  Tricep Pushdown:         RPE 7-9       × 3 sets
  Bicep Curls:             RPE 7-9       × 3 sets
  
  High-RPE sets: 0 + 2 = 2/16 (isolation focus)
```

**Weekly Total:** 16 high-RPE sets ✓ (within 16 limit)

---

### Example 3: Olympic Weightlifting Program (4 Days/Week)
**User Profile:** Advanced, goal: explosiveness, 4 days/week

**Week 3 (Intensification Phase):**
```
Monday (Snatch Focus - RPE 6-8):
  Snatch:                  RPE 6-7.5    × 5 sets  (Quality over intensity)
  Snatch Pull:              RPE 6-7       × 3 sets
  Overhead Squat:           RPE 6.5-7    × 3 sets
  
  Olympic sets at RPE 8+: 0/3 (respecting cap)

Wednesday (C&J Focus - RPE 6-8):
  Clean:                    RPE 6-7.5    × 5 sets
  Jerk:                     RPE 6-7.5    × 4 sets
  Front Squat:              RPE 6.5-7    × 3 sets
  
  Olympic sets at RPE 8+: 0/7

Friday (Strength Accessory - RPE 7-8):
  Back Squat:               RPE 7-8       × 3 sets
  Deadlift:                 RPE 7-8       × 3 sets
  RDL:                      RPE 6.5-7.5  × 3 sets
  
  High-RPE sets: 6/8

Saturday (Power - RPE 7-8):
  Power Snatch:             RPE 6.5-7.5  × 4 sets
  Power Clean:              RPE 6.5-7.5  × 4 sets
  Box Jumps:                RPE 6-7       × 3 sets
  
  High-RPE sets: 0/8 (speed focus, lower RPE)
```

**Weekly Olympic high-RPE sets:** 0/3 ✓ (respecting cap)

---

### Example 4: Low Recovery State Adjustment

**User Profile:** Any program, poor recovery

**Scenario:**
- Sleep: 5 hours (2 nights in a row)
- HRV: -25% below baseline
- Energy rating: 3/10
- Soreness: 7/10 in quads

**Adjustments Applied:**
```
Sleep adjustment:           -1.0
HRV adjustment:            -1.0
Soreness adjustment:       -1.0
Total reduction:           -3.0

Normal RPE for Squat:    7.5-8.5
Adjusted RPE:             4.5-5.5
Reason: "low_sleep_hrv_soreness"
```

**Display to User:**
```
⚠️ RPE Adjusted Based on Recovery

Your Squat RPE reduced to 4.5-5.5 (was 7.5-8.5)
Reason: Low sleep (5h), HRV -25%, quad soreness 7/10

Focus on movement quality today. Recovery will be monitored.
```

---

## Key Design Decisions

### 1. RPE vs Static Movement Properties
- **Decision:** RPE is NOT stored as a movement property
- **Rationale:** Same movement can have different fatigue at different RPEs
- **Implementation:** RPE suggested per-session based on context

### 2. Pattern Recovery Time Calculation
- **Decision:** Use RPE-based recovery hours (24-96h range)
- **Rationale:** Higher RPE = longer recovery needed
- **Implementation:** Dynamic calculation, not static min_recovery_hours

### 3. High-RPE Set Limits
- **Decision:** Enforce weekly and per-session limits
- **Rationale:** Prevent overtraining while maximizing stimulus
- **Implementation:** MAX_HIGH_RPE_SETS_PER_SESSION configuration

### 4. Isolation vs Compound RPE Tolerance
- **Decision:** Isolations can train closer to failure (RPE 8-10)
- **Rationale:** Lower systemic fatigue, reduced injury risk
- **Implementation:** Higher RPE cap for isolation patterns

### 5. Olympic/Powerlifting RPE Caps
- **Decision:** Cap at RPE 8.5 for quality
- **Rationale:** Technique breakdown at high RPE for complex lifts
- **Implementation:** CNS/discipline adjustment in RPE service

---

## Success Metrics

### Technical Metrics
- 90% of sessions follow RPE distribution patterns
- <5% of sessions exceed MAX_HIGH_RPE_SETS_PER_SESSION
- Pattern recovery constraints enforced 100%
- Fatigue adjustments applied when recovery signals present

### User Experience Metrics
- 80% of users understand RPE adjustments (survey)
- Training adherence >85% (vs 70% baseline)
- Overtraining incidents reduced by 50%
- User satisfaction >4/5

### Performance Metrics
- Strength gains: +5% every 8 weeks (strength programs)
- Hypertrophy progression: +3% volume every 4 weeks
- Deload acceptance: >70%

---

## Implementation Timeline

| Phase | Duration | Key Deliverables |
|--------|-----------|------------------|
| 1 - Configuration | 1 week | RPE configs in YAML files |
| 2 - Database | 1 week | Schema migrations |
| 3 - Core Service | 2 weeks | RPE suggestion service |
| 4 - Recovery | 2 weeks | Updated recovery mechanics |
| 5 - Testing | 2 weeks | Unit + integration tests |
| 6 - Frontend | 2 weeks | UI components |
| **Total** | **10 weeks** | Full RPE suggestion system |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|-------|-------------|------------|-------------|
| User confusion about RPE ranges | Medium | Medium | Progressive disclosure, education tooltips |
| RPE too conservative | Medium | High | User override option, data-driven tuning |
| Recovery signal noise | High | Medium | Multiple signals required for adjustment |
| Pattern recovery tracking complexity | Medium | Low | Fallback to static hours if missing data |

---

## Future Enhancements (Post-MVP)

1. **ML-based RPE calibration** - Learn user's RPE accuracy over time
2. **Wearable integration** - Real-time HRV/recovery data
3. **Dynamic microcycle progression** - Auto-adjust based on performance
4. **Social RPE sharing** - Community benchmarks
5. **Advanced fatigue modeling** - Neural network for recovery prediction