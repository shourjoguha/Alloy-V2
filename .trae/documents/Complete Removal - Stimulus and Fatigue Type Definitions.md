# Plan: Complete Removal of Stimulus and Fatigue Type Definitions

## Executive Summary

This plan completes the removal of stimulus and fatigue factors by eliminating them from type definitions, data transfer objects, and configuration files. The previous operation removed these variables from **decision-making logic**; this operation removes them from **data structures** to create a clean architecture.

**Key Insight**: Fatigue and stimulus are NOT inherent movement properties. They are functions of **how movements are used (RPE 1-10)**. The previous "fatigue_factor" and "stimulus_factor" stored in the movement table were architectural misconceptions.

**RPE-Based Philosophy (Future)**: Fatigue management will be implemented as **session-level RPE constraints**:
- Limit main lifts with high RPE (≥8): 2 for hinge/squat/lunge/olympic, 4 for upper body
- Limit total high-RPE sets per session
- 3x3 squat at RPE 9 (strength) ≈ 3x10 squat at RPE 7 (hypertrophy) in fatigue terms

---

## Phase 1: Remove from Type Definitions

### File: `app/services/optimization_types.py`

#### Change 1.1: Remove from SolverMovement
**Lines 23-24:**
```python
# BEFORE:
@dataclass
class SolverMovement:
    movement_id: int
    name: str
    # ...
    fatigue_factor: float
    stimulus_factor: float
    primary_muscles: List[str]
    # ...

# AFTER:
@dataclass
class SolverMovement:
    movement_id: int
    name: str
    # ...
    primary_muscles: List[str]
    # ...
```

#### Change 1.2: Remove from SolverCircuit
**Lines 40-41:**
```python
# BEFORE:
@dataclass
class SolverCircuit:
    circuit_id: int
    # ...
    fatigue_factor: float
    stimulus_factor: float
    # ...

# AFTER:
@dataclass
class SolverCircuit:
    circuit_id: int
    # ...
```

#### Change 1.3: Remove from OptimizationResultV2
**Lines 86-87:**
```python
# BEFORE:
@dataclass
class OptimizationResultV2:
    # ...
    total_fatigue: float
    total_stimulus: float
    success: bool
    # ...

# AFTER:
@dataclass
class OptimizationResultV2:
    # ...
    success: bool
    # ...
```

---

## Phase 2: Update Session Generator

### File: `app/services/session_generator.py`

#### Change 2.1: Remove from _load_all_circuits()
**Lines 2014-2015:**
```python
# BEFORE:
circuit = SolverCircuit(
    circuit_id=c.id,
    name=c.name,
    # ...
    fatigue_factor=c.fatigue_factor if c.fatigue_factor else 1.0,
    stimulus_factor=c.stimulus_factor if c.stimulus_factor else 1.0,
    # ...
)

# AFTER:
circuit = SolverCircuit(
    circuit_id=c.id,
    name=c.name,
    # ...
)
```

#### Change 2.2: Remove from _to_solver_movements()
**Lines 2129-2130:**
```python
# BEFORE:
movement = SolverMovement(
    movement_id=m.id,
    name=m.name,
    # ...
    fatigue_factor=m.fatigue_factor,
    stimulus_factor=m.stimulus_factor,
    # ...
)

# AFTER:
movement = SolverMovement(
    movement_id=m.id,
    name=m.name,
    # ...
)
```

---

## Phase 3: Clean Configuration Files

### File: `app/config/optimization_config.yaml`

#### Change 3.1: Remove max_fatigue from OR-Tools config
**Line 20:**
```yaml
# BEFORE:
or_tools:
  max_fatigue: 8.0
  max_duration: 3600
  # ...

# AFTER:
or_tools:
  max_duration: 3600
  # ...
```

### File: `app/config/optimization_config_loader.py`

#### Change 3.2: Remove from ORToolsConfig dataclass
**Line 40:**
```python
# BEFORE:
@dataclass
class ORToolsConfig:
    max_fatigue: float
    max_duration: int
    # ...

# AFTER:
@dataclass
class ORToolsConfig:
    max_duration: int
    # ...
```

---

## Phase 4: Update Logs API

### File: `app/api/routes/logs.py`

#### Change 4.1: Remove from session initialization
**Lines 66-68:**
```python
# BEFORE:
session = Session(
    # ...
    total_stimulus=0.0,
    total_fatigue=0.0,
    cns_fatigue=0.0,
    # ...
)

# AFTER:
session = Session(
    # ...
    cns_fatigue=0.0,
    # ...
)
```

#### Change 4.2: Remove from stats update
**Lines 174-177:**
```python
# BEFORE:
session.total_stimulus = 0.0
session.total_fatigue = 0.0
session.cns_fatigue = stats["cns_fatigue"]

# AFTER:
session.cns_fatigue = stats["cns_fatigue"]
```

#### Change 4.3: Remove from SessionExercise
**Lines 120-121:**
```python
# BEFORE:
SessionExercise(
    # ...
    stimulus=0.0,
    fatigue=0.0,
    # ...
)

# AFTER:
SessionExercise(
    # ...
)
```

---

## Phase 5: Update Tests

### File: `tests/test_optimization_v2_integration.py`

#### Change 5.1: Remove from SolverMovement fixtures
**All test fixture definitions:**
```python
# BEFORE:
solver_movement = SolverMovement(
    movement_id=1,
    name="Test Movement",
    # ...
    fatigue_factor=1.0,
    stimulus_factor=1.0,
    # ...
)

# AFTER:
solver_movement = SolverMovement(
    movement_id=1,
    name="Test Movement",
    # ...
)
```

#### Change 5.2: Remove from SolverCircuit fixtures
**All circuit test fixtures:**
```python
# BEFORE:
solver_circuit = SolverCircuit(
    circuit_id=1,
    # ...
    fatigue_factor=1.0,
    stimulus_factor=1.0,
    # ...
)

# AFTER:
solver_circuit = SolverCircuit(
    circuit_id=1,
    # ...
)
```

#### Change 5.3: Remove from OptimizationResultV2 assertions
**Test assertions:**
```python
# BEFORE:
assert result.total_fatigue <= request.max_fatigue
assert result.total_stimulus >= request.min_stimulus

# AFTER:
# Remove these assertions entirely
```

---

## Phase 6: Run Test Suite

### Commands:
```bash
python -m pytest tests/test_optimization_v2_integration.py -v
python -m pytest tests/test_session_generator.py -v
python -m pytest tests/ -v  # Full suite if needed
```

### Expected Issues:
1. Type errors from missing required fields in test fixtures
2. Attribute errors from accessing removed fields
3. Failed assertions checking removed result fields

### Fix Strategy:
1. Update all test fixtures to match new type definitions
2. Remove assertions checking removed fields
3. Verify all tests pass

---

## Phase 7: Create Architecture Decision Record

### File: `.trae/documents/ADR-00X-Remove-Stimulus-Fatigue.md`

```markdown
# ADR-00X: Remove Stimulus and Fatigue as Movement Properties

## Status
Accepted

## Context
The system previously stored `fatigue_factor` and `stimulus_factor` as inherent movement properties in the database. These were used for:
- Movement selection optimization
- Fatigue budget constraints
- Stimulus-to-fatigue ratio (SFR) optimization objective

## Decision
Remove `fatigue_factor` and `stimulus_factor` from:
- Type definitions (SolverMovement, SolverCircuit, OptimizationResultV2)
- Session generator data transfer
- Configuration files
- Test fixtures

## Rationale
**Key Insight**: Fatigue and stimulus are NOT inherent movement properties. They are functions of **how movements are used (RPE 1-10)**.

**Examples**:
- 3x3 squat at RPE 9 (strength goal) ≈ 3x10 squat at RPE 7 (hypertrophy goal) in fatigue terms
- The "fatigue_factor" stored in the movement table was a misconception

**Future Approach**: Fatigue management will be implemented as **session-level RPE constraints**:
- Limit main lifts with high RPE (≥8): 2 for hinge/squat/lunge/olympic, 4 for upper body
- Limit total high-RPE sets per session

## Consequences
**Positive**:
- Removes architectural misconception
- Creates clean slate for RPE-based fatigue management
- Eliminates zombie configuration values
- Reduces data structure complexity

**Negative**:
- Breaks API contracts if external consumers exist
- Requires database migration in future (columns still present, marked DEPRECATED)
- Test suite requires updates

**Database**:
- Columns kept with DEPRECATED comments for backward compatibility
- Future migration (after 2-3 release cycles) will drop:
  - `movements.fatigue_factor`
  - `movements.stimulus_factor`
  - `circuits.fatigue_factor`
  - `circuits.stimulus_factor`
  - `sessions.total_stimulus`
  - `sessions.total_fatigue`

## Alternatives Considered
1. **Keep fields, mark deprecated**: Rejected - creates zombie code and maintenance hazard
2. **Keep fields, repurpose for ML features**: Rejected - contradicts RPE-based philosophy
3. **Full migration including database**: Rejected - too high risk, no migration path for existing data

## References
- Original plan: `.trae/documents/Remove Stimulus and Fatigue Constraints from Program Generation.md`
- Implementation date: 2025-02-10
```

---

## Database Schema Status

### Columns Kept (Preserved for Backward Compatibility)

**Movement Table** ([app/models/movement.py](file:///Users/shourjosmac/Documents/alloy/app/models/movement.py#L119-L122)):
```python
# Fitness Function Metrics (RL Reward Signals)
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
fatigue_factor = Column(Float, nullable=False, default=1.0)
stimulus_factor = Column(Float, nullable=False, default=1.0)
```

**Circuit Table** ([app/models/circuit.py](file:///Users/shourjosmac/Documents/alloy/app/models/circuit.py#L24-L25)):
```python
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
fatigue_factor = Column(Float, nullable=False, default=1.0)
stimulus_factor = Column(Float, nullable=False, default=1.0)
```

**Session Table** ([app/models/program.py](file:///Users/shourjosmac/Documents/alloy/app/models/program.py#L201-L203)):
```python
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
total_stimulus = Column(Float, default=0.0)
total_fatigue = Column(Float, default=0.0)
```

### Future Migration (After 2-3 Release Cycles)

**Prerequisites**:
1. Confirm no external API consumers depend on these fields
2. RPE-based fatigue management is implemented
3. Historical data analysis confirms no value in preserving

**Migration Script** (Future):
```python
# Drop deprecated columns
op.drop_column('movements', 'fatigue_factor')
op.drop_column('movements', 'stimulus_factor')
op.drop_column('circuits', 'fatigue_factor')
op.drop_column('circuits', 'stimulus_factor')
op.drop_column('sessions', 'total_stimulus')
op.drop_column('sessions', 'total_fatigue')
```

---

## Frontend Impact

### Current State
- Types already made optional ([frontend/src/types/index.ts](file:///Users/shourjosmac/Documents/alloy/frontend/src/types/index.ts))
- Usage examples already updated ([frontend/src/components/circuit/USAGE_EXAMPLES.tsx](file:///Users/shourjosmac/Documents/alloy/frontend/src/components/circuit/USAGE_EXAMPLES.tsx))

### No Action Required
Frontend changes from Phase 2.1-2.2 of original operation are sufficient. The graceful degradation pattern handles the backend no longer sending these values.

---

## Success Criteria

1. ✅ Type definitions cleaned (SolverMovement, SolverCircuit, OptimizationResultV2)
2. ✅ Session generator stops copying removed fields
3. ✅ Configuration files cleaned (no zombie values)
4. ✅ Logs API stops setting removed fields
5. ✅ All tests pass with updated fixtures
6. ✅ ADR created documenting decision
7. ✅ No AttributeError or TypeError in production

---

## Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|------|------------|-----------|------------|
| External API consumers break | Low | High | Monitor error logs; add deprecation headers |
| Database migration needed soon | Medium | Medium | Keep columns for 2-3 cycles |
| Test suite breaks | High | Low | Comprehensive test updates planned |
| Frontend display issues | Low | Low | Already handles optional fields gracefully |

---

## Execution Order

1. **Phase 1**: Type definitions (optimization_types.py)
2. **Phase 2**: Session generator (session_generator.py)
3. **Phase 3**: Configuration files (yaml, loader)
4. **Phase 4**: Logs API (logs.py)
5. **Phase 5**: Tests (test_optimization_v2_integration.py)
6. **Phase 6**: Run test suite and fix issues
7. **Phase 7**: Create ADR

---

## Context Compaction Strategy

Between phases, use:
- `context-manager` agent: Summarize completed work, store as core memory
- `knowledge-organizer` agent: Consolidate learnings, update project knowledge

This frees context space for subsequent phases while preserving critical information.
