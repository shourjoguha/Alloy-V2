# Circuit Metrics Normalization Implementation Plan

## Overview

Create a unified metrics system that enables circuits to be treated as "super-movements" by optimizer, allowing smarter circuit programming with comparable fatigue, stimulus, and recovery metrics.

---

## Phase 1: Database Schema Update

### 1.1 Extend CircuitTemplate Model

Add normalized metrics fields to [app/models/circuit.py](file:///Users/shourjosmac/Documents/Gainsly/app/models/circuit.py):

```python
# Fitness Function Metrics (parallel to Movement model)
fatigue_factor = Column(Float, nullable=False, default=1.0)        # Cumulative fatigue per circuit completion
stimulus_factor = Column(Float, nullable=False, default=1.0)       # Cumulative stimulus per circuit
min_recovery_hours = Column(Integer, nullable=False, default=24)      # Recovery time after circuit

# Muscle-level metrics (normalized)
muscle_volume = Column(JSON, nullable=False, default=dict)        # {muscle: total_volume}
muscle_fatigue = Column(JSON, nullable=False, default=dict)      # {muscle: total_fatigue}

# Circuit-specific metrics
total_reps = Column(Integer, nullable=True)                       # Total reps across all exercises × rounds
estimated_work_seconds = Column(Integer, nullable=True)            # Total work time (excl rest)
effective_work_volume = Column(Float, nullable=True)             # Weighted work volume metric
```

### 1.2 Create Migration

Generate alembic migration to add these columns to `circuit_templates` table with appropriate indexes for querying.

---

## Phase 2: Circuit Metrics Calculation Service

### 2.1 Create CircuitMetricsCalculator Service

New service: [app/services/circuit_metrics.py](file:///Users/shourjosmac/Documents/Gainsly/app/services/circuit_metrics.py)

```python
class CircuitMetricsCalculator:
    async def calculate_circuit_metrics(
        self,
        db: AsyncSession,
        circuit: CircuitTemplate,
        rounds: int = None,
        duration_seconds: int = None
    ) -> dict[str, Any]:
        """Calculate all normalized metrics for a circuit."""
```

**Calculation Logic:**

1. **Aggregate Movement Metrics** (for each exercise in circuit):
   - Fetch movement data (fatigue_factor, stimulus_factor, primary_muscle, secondary_muscles)
   - Calculate per-exercise contribution

2. **Apply Circuit Multipliers:**
   ```
   total_reps = sum(exercise.reps or 1 for exercise in exercises) * rounds
   estimated_work_seconds = sum(
       (exercise.duration_seconds or 0) + 
       (exercise.reps or 10) * 3  # assume 3 sec/rep
   ) * rounds
   ```

3. **Calculate Fatigue Factor:**
   ```
   circuit_fatigue = sum(movement.fatigue_factor for movement in exercises) / len(exercises)
   # Apply intensity modifier based on circuit type:
   - ROUNDS_FOR_TIME: +15% (time pressure)
   - AMRAP: +15% (continuous work)
   - LADDER: +10% (increasing intensity)
   - EMOM: baseline (no modifier)
   ```

4. **Calculate Stimulus Factor:**
   ```
   circuit_stimulus = sum(movement.stimulus_factor for movement in exercises) / len(exercises)
   # Adjust for total work volume:
   circuit_stimulus *= (effective_work_volume / baseline_volume)
   ```

5. **Calculate Muscle-Level Metrics:**
   ```
   for each exercise in exercises × rounds:
       primary_muscle: add exercise.fatigue_factor × rounds
       each secondary_muscle: add (exercise.fatigue_factor × rounds) × 0.5
   
   Normalize to 0-1 scale for comparable muscle targeting
   ```

6. **Determine Min Recovery Hours:**
   ```
   base_recovery = max(movement.min_recovery_hours for movement in exercises)
   # Circuit type modifiers:
   - ROUNDS_FOR_TIME/AMRAP: +12 hours
   - AMRAP: +8 hours
   - EMOM: +4 hours
   ```

### 2.2 Circuit Type-Specific Calculations

**AMRAP:**
- Work time = default_duration_seconds
- Intensity = high (continuous effort)
- Round estimate = (total_reps / work_time) × target_time
- Rounds may be available in circuit.default_rounds or manually specified

**EMOM:**
- Work time = default_duration_seconds
- Intensity = high (1 min work, 1 min rest)
- Total reps calculated from exercises_json
- Rounds may be available in circuit.default_rounds or manually specified

**LADDER:**
- Work time increases with each rung
- Intensity = progressive
- Total reps = sum of arithmetic progression
- Rounds may be available in circuit.default_rounds or manually specified

**ROUNDS_FOR_TIME:**
- Work time = default_duration_seconds
- Intensity = sustained
- Total reps = exercises.reps × rounds
- Rounds available in circuit.default_rounds

---

## Phase 3: One-Time Population Script

### 3.1 Create Migration Script

Script: [scripts/populate_circuit_metrics.py](file:///Users/shourjosmac/Documents/Gainsly/scripts/populate_circuit_metrics.py)

```python
async def populate_all_circuit_metrics():
    """One-time script to calculate and update all existing circuits."""
```

**Process:**
1. Load all CircuitTemplate records
2. For each circuit:
   - Parse exercises_json
   - Use CircuitMetricsCalculator to compute all metrics
   - Update circuit with calculated values
   - Handle missing circuit.default_rounds (log for manual inspection)
3. Commit in batches (100 circuits at a time)
4. Log progress and any errors (missing movements, invalid data)

**Validation:**
- Handle circuits with movement_id = None (use name lookup or skip)
- Log circuits that can't be calculated (missing required data)
- Report summary: total processed, success count, error count

---

## Phase 4: Optimizer Integration

### 4.1 Extend Optimization Engine

Update [app/services/optimization.py](file:///Users/shourjosmac/Documents/Gainsly/app/services/optimization.py):

```python
@dataclass
class SolverCircuit:
    """Normalized circuit for optimization solver (parallel to SolverMovement)."""
    id: int
    name: str
    primary_muscle: str  # Dominant muscle group
    fatigue_factor: float
    stimulus_factor: float
    effective_work_volume: float
    circuit_type: CircuitType
    duration_seconds: int

@dataclass
class OptimizationRequest:
    # Add to existing fields:
    available_circuits: List[SolverCircuit]  # NEW
    allow_circuits: bool = True  # NEW
```

### 4.2 Modify Constraint Solver

Update `solve_session()` to include circuits:

```python
# Combine movements and circuits in variable pool
all_variables = []
movement_vars = {}  # existing
circuit_vars = {}  # NEW

for c in request.available_circuits:
    circuit_vars[c.id] = model.NewBoolVar(f'circuit_{c.id}')
    all_variables.append(circuit_vars[c.id])

# Volume targeting includes circuits
for muscle, target_sets in request.target_muscle_volumes.items():
    # Add circuit variables to relevant_movements
    relevant_circuits = [circuit_vars[c.id] for c in available_circuits 
                       if c.primary_muscle == muscle]
    model.Add(sum(relevant_movements + relevant_circuits) * 3 >= target_sets)

# Fatigue constraint includes circuits
fatigue_expr = (
    sum(movement_vars[m.id] * m.fatigue_factor for m in available_movements if m.id in movement_vars) +
    sum(circuit_vars[c.id] * c.fatigue_factor for c in available_circuits if c.id in circuit_vars)
)
```

### 4.3 Objective Function with Circuits

```python
stimulus_expr = (
    sum(movement_vars[m.id] * m.stimulus_factor for m in available_movements if m.id in movement_vars) +
    sum(circuit_vars[c.id] * c.stimulus_factor for c in available_circuits if c.id in circuit_vars)
)
model.Maximize(stimulus_expr)
```

---

## Phase 5: Session Generator Integration

### 5.1 Add Circuit Selection Logic

Update [app/services/session_generator.py](file:///Users/shourjosmac/Documents/Gainsly/app/services/session_generator.py):

```python
async def _load_available_circuits(
    self, db: AsyncSession, session_type: SessionType
) -> List[SolverCircuit]:
    """Load circuits suitable for session type."""
    # Query circuits with tags matching discipline
    # Convert to SolverCircuit using pre-calculated metrics
    # Filter by circuit_type appropriateness
```

### 5.2 Hybrid Session Generation

Modify session generation to support mixed circuits + movements:

```python
def _generate_draft_session():
    # Existing: load movements
    # NEW: also load circuits
    
    # If session_type allows circuits (CROSSFIT, METCON, CONDITIONING):
    #   Include both movements and circuits in solver pool
    # Else:
    #   Use only movements
    
    # Solve with combined pool
    result = optimizer.solve_session(request_with_circuits)
    
    # Post-process: separate circuits from movements
    #   Circuit → set main_circuit_id
    #   Movements → set main_json, accessory_json
```

### 5.3 Update Session Volume Calculation

Modify [`_calculate_session_volume()`](file:///Users/shourjosmac/Documents/Gainsly/app/services/session_generator.py#L421) to handle circuits:

```python
async def _calculate_session_volume(self, db: AsyncSession, session: Session) -> dict[str, int]:
    # Existing: process movements from main_json, accessory_json, finisher_json
    
    # NEW: Process circuits
    if session.main_circuit_id:
        circuit = await db.get(CircuitTemplate, session.main_circuit_id)
        # Use pre-calculated circuit.muscle_volume
        for muscle, volume in circuit.muscle_volume.items():
            current_session_volume[muscle] = current_session_volume.get(muscle, 0) + volume
    
    if session.finisher_circuit_id:
        circuit = await db.get(CircuitTemplate, session.finisher_circuit_id)
        for muscle, volume in circuit.muscle_volume.items():
            current_session_volume[muscle] = current_session_volume.get(muscle, 0) + (volume // 2)  # finisher = half volume
```

---

## Phase 6: Validation & Testing

### 6.1 Unit Tests

Create test suite for CircuitMetricsCalculator:
- Test each circuit type (AMRAP, EMOM, LADDER, ROUNDS_FOR_TIME)
- Test muscle volume aggregation
- Test fatigue calculation with various exercise combinations
- Edge cases: empty circuits, missing movements, zero reps
- Test missing default_rounds handling

### 6.2 Integration Tests

- Session generation with circuits
- Optimizer selection with mixed movements + circuits
- Volume tracking with circuits
- Recovery calculations with circuits

### 6.3 Manual Verification

- Compare calculated metrics against expected values for sample circuits
- Verify circuits appear in appropriate session types
- Check fatigue/recovery tracking accuracy

---

## Summary of Benefits

1. **Unified Programming**: Circuits treated as first-class entities in optimizer
2. **Comparable Metrics**: Fatigue, stimulus, recovery work for both movements and circuits
3. **Smart Selection**: Program builder can intelligently choose circuits or movements
4. **Accurate Tracking**: Muscle volume, fatigue, recovery work correctly for circuits
5. **Fast Queries**: Pre-calculated metrics avoid runtime computation
6. **Maintainable**: Schema extension, calculation logic clearly separated
7. **Backwards Compatible**: Existing movement-based sessions unaffected

---

## Files to Create/Modify

**New Files:**
- `app/services/circuit_metrics.py` - Circuit metrics calculation service
- `scripts/populate_circuit_metrics.py` - One-time migration script
- `tests/test_circuit_metrics.py` - Unit tests

**Modified Files:**
- `app/models/circuit.py` - Add metrics columns
- `app/services/optimization.py` - Add SolverCircuit, extend request
- `app/services/session_generator.py` - Load circuits, handle in volume calc
- `alembic/versions/xxx_add_circuit_metrics.py` - Database migration

---

## Implementation Order

1. Phase 1 (Schema) → 1 migration + 1 model update
2. Phase 2 (Calculation) → 1 new service file
3. Phase 3 (Population) → Run script once (handle missing rounds data)
4. Phase 4 (Optimizer) → Extend 2 service files
5. Phase 5 (Session Gen) → Update 1 service file
6. Phase 6 (Testing) → Test suite + validation

**Estimated Effort:** 2-3 days implementation, 1 day testing
