# Phase 3 RPE Implementation Context Summary
**Preserved for Phase 4: SessionGenerator Integration**

---

## Executive Summary

Phase 3 implements the **RPESuggestionService** with intelligent RPE calculation logic. This service will be integrated into SessionGenerator in Phase 4. The implementation is built on the core philosophy that **fatigue and stimulus are NOT inherent movement properties** - they are functions of **how movements are used (RPE 1-10)**.

---

## Phases 1-2: Completed Work

### Configuration Files Updated

**File:** [`/Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml`](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml)

```yaml
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
      weekly_high_rpe_sets_max: 12
      microcycle_progression:
        accumulation: [6.5, 7.5]
        intensification: [7.5, 8.5]
        peaking: [8, 9.5]
        deload: [4, 5.5]

    hypertrophy:
      primary_compound_rpe: [6.5, 8.5]
      accessory_rpe: [6, 7.5]
      weekly_high_rpe_sets_max: 16
      microcycle_progression:
        volume_phase: [7, 8]
        intensity_phase: [7.5, 8.5]
        fatigue_mgmt: [6, 7]
        deload: [4, 6]

    endurance:
      primary_compound_rpe: [5.5, 7.5]
      accessory_rpe: [6, 8]
      weekly_high_rpe_sets_max: 20
      microcycle_progression:
        daily_undulating: true

    power:
      primary_compound_rpe: [7, 8.5]
      accessory_rpe: [6, 8]
      weekly_high_rpe_sets_max: 8
      microcycle_progression:
        wave_loading: true

  # RPE adjustments by CNS load and discipline
  cns_discipline_adjustments:
    high_cns_olympic_powerlifting:
      rpe_cap: 8.5
      weekly_limit: 3

    moderate_cns_compound:
      rpe_cap: 9.5
      weekly_limit: 6

  # Recovery-based RPE reductions
  fatigue_adjustments:
    sleep_under_6h: -0.5
    sleep_under_5h: -1.0
    hrv_below_baseline_20pct: -1.0
    soreness_above_7: -1.0
    consecutive_high_rpe_days: -0.5

  # Recovery time (hours) by RPE level
  recovery_hours_by_rpe:
    rpe_6_7: 24
    rpe_8: 48
    rpe_9: 72
    rpe_10: 96
```

**Configuration Loader:** [`/Users/shourjosmac/Documents/alloy/app/config/optimization_config_loader.py`](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config_loader.py#L144-L270)

Key dataclasses defined:
- `MicrocycleProgressionConfig` (L147-L158)
- `ProgramTypeRPEProfile` (L161-L182)
- `CNSDisciplineAdjustmentsConfig` (L185-L200)
- `FatigueAdjustmentsConfig` (L203-L224)
- `RecoveryHoursByRPEConfig` (L227-L240)
- `RPESuggestionConfig` (L243-L270)

### Database Schema Created

**File:** [`/Users/shourjosmac/Documents/alloy/app/models/program.py`](file:///Users/shourjosmac/Documents/alloy/app/models/program.py)

#### SessionExercise Model (L225-L274)
```python
class SessionExercise(Base):
    # ... existing fields ...
    
    # RPE Suggestion Tracking (NEW - Phase 2)
    suggested_rpe_min = Column(Float, nullable=True)
    suggested_rpe_max = Column(Float, nullable=True)
    rpe_adjustment_reason = Column(String(100), nullable=True)
```

#### Microcycle Model (L113-L147)
```python
class Microcycle(Base):
    # ... existing fields ...
    
    # RPE Tracking (NEW - Phase 2)
    microcycle_phase = Column(String(50), nullable=True)  # accumulation, intensification, peaking, deload
    rpe_intensity_factor = Column(Float, nullable=True)  # 0.5 = deload, 1.0 = normal, 1.2 = peak
```

#### PatternRecoveryState Model (L277-L300)
```python
class PatternRecoveryState(Base):
    """Tracks recovery status for each movement pattern."""
    __tablename__ = "pattern_recovery_states"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, primary_key=True)
    pattern = Column(SQLEnum(MovementPattern), nullable=False, primary_key=True)
    
    # Recovery tracking
    last_trained_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_rpe = Column(Float, nullable=False, default=7.0)
    recovery_hours_required = Column(Integer, nullable=False, default=24)
    
    # Recovery status
    recovery_percentage = Column(Float, nullable=True, default=0.0)
    is_ready = Column(Boolean, nullable=False, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## Phase 3: RPESuggestionService Implementation

### Service Location
**File to create:** `/Users/shourjosmac/Documents/alloy/app/services/rpe_suggestion_service.py`

### Core Methods Required

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

### Key Requirements

#### 1. Program-Type-Aware RPE Profiles

| Program Type | Primary Compound RPE | Accessory RPE | Weekly High-RPE Sets Max |
|--------------|---------------------|---------------|-------------------------|
| Strength | 7.5-9.5 | 6-8 | 12 |
| Hypertrophy | 6.5-8.5 | 6-7.5 | 16 |
| Endurance | 5.5-7.5 | 6-8 | 20 |
| Power | 7-8.5 | 6-8 | 8 |

#### 2. CNS/Discipline Caps

| Discipline Type | RPE Cap | Weekly Limit |
|----------------|----------|--------------|
| Olympic/Powerlifting (High CNS) | 8.5 | 3 sets at RPE 8+ |
| Compound (Moderate CNS) | 9.5 | 6 sets at RPE 8+ |
| Isolation | No cap | No limit |

#### 3. Fatigue Adjustments

| Signal | Adjustment |
|--------|-------------|
| Sleep < 6h | -0.5 RPE |
| Sleep < 5h | -1.0 RPE |
| HRV < baseline by 20% | -1.0 RPE |
| Soreness > 7/10 | -1.0 RPE |
| Consecutive high-RPE days (2+) | -0.5 RPE |

#### 4. Recovery Hours by RPE

| RPE Level | Recovery Hours |
|-----------|----------------|
| 6-7 | 24 hours |
| 8 | 48 hours |
| 9 | 72 hours |
| 10 | 96 hours |

---

## RPE Training Methodology Research (Compacted)

### Scientific Basis

**RPE Scale Definition:** Subjective 1-10 scale measuring effort based on "Reps in Reserve" (RIR)
- RPE 10 = 0 RIR (could not do another rep)
- RPE 9 = 1 RIR
- RPE 8 = 2 RIR
- RPE 7 = 3 RIR
- RPE 6 = 4 RIR

### Key Research Findings

1. **Autoregulation Superiority** (Florida Atlantic University, 2024)
   - RPE-based training achieved 15% greater strength gains vs percentage-based
   - Lower reported fatigue and better adherence
   - Automatically adjusts for daily variations (5-15% strength fluctuation)

2. **RIR vs Traditional RPE** (Hackett et al., Zourdos et al.)
   - Traditional RPE scales underreport even at failure
   - RIR-based estimation shows high accuracy (r=0.93-0.95)
   - Accuracy improves as sets approach failure

3. **Optimal RPE Ranges by Goal** (PMC4961270, 2016)
   - **Strength:** RPE 6-8 (2-4 RIR) for main movements
   - **Hypertrophy:** RPE 7-9 (1-3 RIR) with adequate rest
   - **Endurance:** RPE 9-10 (0-1 RIR) for 12+ rep sets
   - **Power:** RPE cap of 4 for velocity-focused work

4. **Learning Curve** (NSCA Position Stand, 2024)
   - 4-8 weeks to develop accurate RPE assessment
   - Monitor bar speed changes for calibration
   - Periodic sets to failure improve accuracy

5. **Systematic Review 2025** (Frontiers in Sports & Active Living)
   - 18 studies (2009-2023) show moderate positive correlation
   - OMNI-RES and RIR scales validated with movement velocity
   - Equations developed to estimate %1RM from RPE

6. **Network Meta-Analysis 2025** (ScienceDirect)
   - Autoregulated methods (APRE, RPE, VBRT) > PBRT for strength
   - SUCRA rankings: APRE (93%), RPE (66.8%), VBRT (27%), PBRT (13.2%)
   - RPE-based training significantly more effective than percentage-based

### Practical Guidelines

1. **Microcycle Progression**
   - Accumulation: RPE 6.5-7.5 (volume focus)
   - Intensification: RPE 7.5-8.5 (intensity increase)
   - Peaking: RPE 8-9.5 (max effort)
   - Deload: RPE 4-6 (50% volume reduction)

2. **Wave Loading Pattern** (Power programs)
   - Day 1: RPE 7
   - Day 2: RPE 8
   - Day 3: RPE 7.5
   - Day 4: RPE 8.5

3. **Daily Undulation** (Endurance programs)
   - RPE waves through week: 6 → 7 → 8 → 7 → 6 → 8 → 7

4. **High-RPE Set Limits** (Injury Prevention)
   - Squat/Hinge/Lunge patterns: Max 6 high-RPE sets per session
   - Push/Pull patterns: Max 12 high-RPE sets per session
   - Olympic movements: Max 3 high-RPE sets per week (quality focus)

---

## Related Models and Enums

### Movement Model
**File:** [`/Users/shourjosmac/Documents/alloy/app/models/movement.py`](file:///Users/shourjosmac/Documents/alloy/app/models/movement.py#L96-L184)

Key fields for RPE calculation:
- `pattern`: MovementPattern (squat, hinge, horizontal_push, etc.)
- `cns_load`: CNSLoad (very_low, low, moderate, high, very_high)
- `disciplines`: List of DisciplineType (olympic, powerlifting, bodybuilding, etc.)
- `compound`: Boolean (compound vs isolation)
- `is_complex_lift`: Boolean (requires confirmation for safety)

### Enums
**File:** [`/Users/shourjosmac/Documents/alloy/app/models/enums.py`](file:///Users/shourjosmac/Documents/alloy/app/models/enums.py)

```python
class MovementPattern(str, Enum):
    SQUAT = "squat"
    HINGE = "hinge"
    HORIZONTAL_PUSH = "horizontal_push"
    VERTICAL_PUSH = "vertical_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PULL = "vertical_pull"
    CARRY = "carry"
    CORE = "core"
    LUNGE = "lunge"
    ROTATION = "rotation"
    PLYOMETRIC = "plyometric"
    OLYMPIC = "olympic"
    ISOLATION = "isolation"
    MOBILITY = "mobility"
    STRETCH = "stretch"
    ISOMETRIC = "isometric"
    CONDITIONING = "conditioning"
    CARDIO = "cardio"

class CNSLoad(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

class Goal(str, Enum):
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    ENDURANCE = "endurance"
    FAT_LOSS = "fat_loss"
    MOBILITY = "mobility"
    EXPLOSIVENESS = "explosiveness"
    SPEED = "speed"
```

### RecoverySignal Model
**File:** [`/Users/shourjosmac/Documents/alloy/app/models/logging.py`](file:///Users/shourjosmac/Documents/alloy/app/models/logging.py#L147-L179)

Used for fatigue adjustments:
- `hrv`: Heart Rate Variability
- `resting_hr`: Resting heart rate
- `sleep_score`: Sleep quality score (0-100)
- `sleep_hours`: Sleep duration
- `readiness`: Overall readiness score (0-100)

---

## Integration Points for Phase 4

### SessionGenerator Service
**File:** [`/Users/shourjosmac/Documents/alloy/app/services/session_generator.py`](file:///Users/shourjosmac/Documents/alloy/app/services/session_generator.py)

Current structure:
- `generate_session_exercises()` method (L47-L138)
- `_generate_draft_session()` method (L84+)
- `_convert_optimization_result_to_content()` method (L87)

**Phase 4 Integration Requirements:**
1. Load RPESuggestionService in SessionGenerator.__init__()
2. Call `suggest_rpe_for_session()` in `_generate_draft_session()`
3. For each selected movement, call `suggest_rpe_for_movement()`
4. Set `suggested_rpe_min`, `suggested_rpe_max`, `rpe_adjustment_reason` on SessionExercise
5. Save RPE suggestions to database via `_save_session_exercises()`

### Program Service
**File:** [`/Users/shourjosmac/Documents/alloy/app/services/program.py`](file:///Users/shourjosmac/Documents/alloy/app/services/program.py)

May need updates to:
- Pass microcycle_phase to session generation
- Track weekly high-RPE set counts
- Update pattern recovery states after session completion

---

## Key Design Decisions

### 1. RPE vs Static Movement Properties
**Decision:** RPE is NOT stored as a movement property
**Rationale:** Same movement can have different fatigue at different RPEs
**Implementation:** RPE suggested per-session based on context

### 2. Pattern Recovery Time Calculation
**Decision:** Use RPE-based recovery hours (24-96h range)
**Rationale:** Higher RPE = longer recovery needed
**Implementation:** Dynamic calculation, not static min_recovery_hours

### 3. High-RPE Set Limits
**Decision:** Enforce weekly and per-session limits
**Rationale:** Prevent overtraining while maximizing stimulus
**Implementation:** weekly_high_rpe_sets_max configuration

### 4. Isolation vs Compound RPE Tolerance
**Decision:** Isolations can train closer to failure (RPE 8-10)
**Rationale:** Lower systemic fatigue, reduced injury risk
**Implementation:** Higher RPE cap for isolation patterns

### 5. Olympic/Powerlifting RPE Caps
**Decision:** Cap at RPE 8.5 for quality
**Rationale:** Technique breakdown at high RPE for complex lifts
**Implementation:** CNS/discipline adjustment in RPE service

---

## Example RPE Calculations

### Example 1: Strength Program, Monday Upper Session
**Context:**
- Program type: Strength
- Microcycle phase: Accumulation
- Movement: Bench Press (compound, moderate CNS)
- Exercise role: main

**Calculation:**
1. Base RPE from program profile: [7.5, 9.5]
2. Apply microcycle phase (accumulation): [6.5, 7.5]
3. Apply CNS cap (moderate): No cap (RPE 9.5 limit)
4. Check recovery: User well-rested (no adjustment)
5. Check pattern recovery: horizontal_push last trained 48h ago at RPE 7 → ready

**Result:** RPE 6.5-7.5, reason: "normal"

### Example 2: Olympic Weightlifting, Poor Recovery
**Context:**
- Program type: Power
- Movement: Snatch (olympic, very high CNS)
- Exercise role: main
- User recovery: sleep 5h, HRV -25%, quad soreness 7/10

**Calculation:**
1. Base RPE from program profile: [7, 8.5]
2. Apply CNS cap (olympic): Cap at 8.5
3. Apply fatigue adjustments:
   - Sleep < 5h: -1.0
   - HRV -20%: -1.0
   - Soreness > 7: -1.0
   - Total: -3.0
4. Adjusted RPE: [7-3.0, 8.5-3.0] = [4, 5.5]
5. Clamp to valid range: [4, 5.5] (minimum RPE 4)

**Result:** RPE 4-5.5, reason: "low_sleep_hrv_soreness"

### Example 3: Hypertrophy, High Volume Week
**Context:**
- Program type: Hypertrophy
- Microcycle phase: Volume phase
- Weekly high-RPE sets count: 14/16
- Movement: Bicep Curls (isolation, low CNS)
- Exercise role: accessory

**Calculation:**
1. Base RPE from exercise role (accessory): [5, 7]
2. Apply microcycle phase (volume): [7, 8]
3. Apply CNS cap (isolation): No cap
4. Check weekly limit: 14/16 sets, approaching limit
5. Pattern recovery: isolation last trained 24h ago at RPE 8 → not fully recovered

**Result:** RPE 6-7, reason: "weekly_limit_recovery"

---

## Testing Requirements

### Unit Tests
**File to create:** `/Users/shourjosmac/Documents/alloy/tests/test_rpe_suggestion_service.py`

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

## References

1. **Implementation Plan:** `/Users/shourjosmac/Documents/alloy/.trae/documents/RPE Suggestion System Implementation Plan.md`
2. **Config File:** `/Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml`
3. **Config Loader:** `/Users/shourjosmac/Documents/alloy/app/config/optimization_config_loader.py`
4. **Models:** `/Users/shourjosmac/Documents/alloy/app/models/program.py`
5. **Session Generator:** `/Users/shourjosmac/Documents/alloy/app/services/session_generator.py`
6. **Optimization Types:** `/Users/shourjosmac/Documents/alloy/app/services/optimization_types.py`
7. **WARP Documentation:** `/Users/shourjosmac/Documents/alloy/docs/WARP.md`

---

**End of Phase 3 Context Summary**
**Preserved for Phase 4: SessionGenerator Integration**
