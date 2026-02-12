# ADR-001: Remove Stimulus and Fatigue as Movement Properties

## Status
Accepted

## Context

The Alloy optimization system previously treated `fatigue_factor` and `stimulus_factor` as inherent properties of movements, stored directly in the database schema. These factors were used throughout the system for:

- Movement selection optimization in the constraint solver
- Fatigue budget constraints in program generation
- Stimulus-to-fatigue ratio (SFR) optimization objectives
- Circuit metrics calculations
- Workout logging and analytics

The original architecture treated fatigue and stimulus as static attributes of exercises, where a movement like "Barbell Back Squat" would have fixed values for fatigue_factor (e.g., 0.9) and stimulus_factor (e.g., 0.95) regardless of how it was performed.

This approach led to several architectural problems:

1. **Fundamental misconception**: Fatigue and stimulus are not inherent movement properties
2. **Static vs. dynamic reality**: The same movement performed at RPE 7 vs. RPE 9 produces vastly different fatigue and stimulus
3. **Over-constrained optimization**: The constraint solver frequently failed to find feasible solutions due to fatigue limits
4. **Loss of training intelligence**: The system couldn't distinguish between a warmup squat and a max-effort squat

## Decision

Remove `fatigue_factor` and `stimulus_factor` as decision-making variables from the optimization system. These fields are deprecated in the database schema and removed from:

- Type definitions ([app/services/optimization_types.py](file:///Users/shourjosmac/Documents/alloy/app/services/optimization_types.py))
- Optimization decision logic ([app/services/greedy_optimizer.py](file:///Users/shourjosmac/Documents/alloy/app/services/greedy_optimizer.py))
- Session generator data transfer ([app/services/session_generator.py](file:///Users/shourjosmac/Documents/alloy/app/services/session_generator.py))
- Configuration files ([app/config/optimization_config.yaml](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml))
- API responses ([app/api/routes/settings.py](file:///Users/shourjosmac/Documents/alloy/app/api/routes/settings.py))

The database columns are preserved for backward compatibility but marked as deprecated.

## Rationale

### Key Architectural Insight

**Fatigue and stimulus are NOT inherent movement properties. They are functions of how movements are used (RPE 1-10).**

This insight fundamentally changes the approach to fatigue management. Consider these examples:

| Movement | Sets × Reps | RPE | Fatigue | Stimulus |
|----------|-------------|-----|---------|----------|
| Barbell Squat | 3 × 3 | 9 | High | High |
| Barbell Squat | 3 × 10 | 7 | Medium | High |
| Barbell Squat | 3 × 5 | 6 | Low | Medium |
| Barbell Squat | 3 × 15 | 8 | High | High |

Under the old system, all four variations would have the same `fatigue_factor` and `stimulus_factor` values, which is clearly incorrect. A 3×3 squat at RPE 9 (strength training) produces similar fatigue to a 3×10 squat at RPE 7 (hypertrophy training), despite very different training objectives.

### Problems with the Previous Approach

1. **Static values ignore intensity**: A 50% 1RM squat and a 95% 1RM squat have identical fatigue_factor values
2. **No context for training goals**: Strength training (low volume, high intensity) vs. hypertrophy training (high volume, moderate intensity) treated identically
3. **Over-constrained optimization**: The optimizer frequently failed to find feasible solutions because fatigue limits were too restrictive
4. **Loss of training intelligence**: The system couldn't make intelligent decisions based on training objectives

### RPE-Based Philosophy (Future Implementation)

Fatigue management will be implemented as **session-level RPE constraints**:

```python
# Example RPE-based fatigue constraints
MAX_HIGH_RPE_SETS_PER_SESSION = {
    "hinge": 2,      # Deadlift variations
    "squat": 2,      # Squat variations
    "lunge": 2,      # Lunge variations
    "olympic": 2,    # Olympic lifts
    "horizontal_push": 4,  # Bench press, etc.
    "vertical_push": 4,    # Overhead press, etc.
    "horizontal_pull": 4,  # Rows, etc.
    "vertical_pull": 4,    # Pull-ups, etc.
}

# High RPE threshold
HIGH_RPE_THRESHOLD = 8  # RPE 8-10 considered "high intensity"
```

This approach provides:

1. **Context-aware fatigue management**: Respects training objectives (strength vs. hypertrophy)
2. **Dynamic adaptation**: Fatigue scales with actual intensity (RPE), not movement type
3. **Simpler optimization**: Fewer constraint variables, larger feasible solution space
4. **Realistic training modeling**: Aligns with how athletes actually manage fatigue

## Consequences

### Positive

- **Removes architectural misconception**: System no longer treats fatigue/stimulus as static properties
- **Creates clean slate for RPE-based fatigue management**: Foundation for future implementation
- **Larger feasible solution space**: Fewer "no solution found" failures in optimization
- **Faster optimization**: Fewer constraint checks to evaluate
- **Eliminates zombie configuration values**: Configuration files cleaned of obsolete settings
- **Reduces data structure complexity**: Removes unnecessary fields from type definitions

### Negative

- **Breaks API contracts if external consumers exist**: Any external API consumers expecting these fields will break
- **Requires database migration in future**: Columns still present in schema, marked as deprecated
- **Test suite requires updates**: Multiple test files need fixture updates
- **Loss of some historical analytics**: Session-level total_stimulus/total_fatigue will always be 0 for new sessions
- **Temporary capability gap**: RPE-based fatigue management not yet implemented, system has no fatigue management currently

### Database Schema Impact

Columns preserved for backward compatibility with deprecation markers:

**Movement Table** ([app/models/movement.py#L119-L122](file:///Users/shourjosmac/Documents/alloy/app/models/movement.py#L119-L122)):
```python
# Fitness Function Metrics (RL Reward Signals)
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
fatigue_factor = Column(Float, nullable=False, default=1.0)  # Systemic fatigue cost (for SFR)
stimulus_factor = Column(Float, nullable=False, default=1.0) # Raw hypertrophy/strength stimulus (for SFR)
```

**Circuit Table** ([app/models/circuit.py#L24-L25](file:///Users/shourjosmac/Documents/alloy/app/models/circuit.py#L24-L25)):
```python
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
fatigue_factor = Column(Float, nullable=False, default=1.0)
stimulus_factor = Column(Float, nullable=False, default=1.0)
```

**Session Table** ([app/models/program.py#L255-L256](file:///Users/shourjosmac/Documents/alloy/app/models/program.py#L255-L256)):
```python
# DEPRECATED: No longer used in optimization decisions. Preserved for backward compatibility.
total_stimulus = Column(Float, nullable=True)
total_fatigue = Column(Float, nullable=True)
```

**Future Migration** (after 2-3 release cycles):
```python
# Drop deprecated columns when safe
op.drop_column('movements', 'fatigue_factor')
op.drop_column('movements', 'stimulus_factor')
op.drop_column('circuits', 'fatigue_factor')
op.drop_column('circuits', 'stimulus_factor')
op.drop_column('sessions', 'total_stimulus')
op.drop_column('sessions', 'total_fatigue')
```

## Files Modified

### Backend Files

| File | Changes |
|------|---------|
| [app/services/optimization_types.py](file:///Users/shourjosmac/Documents/alloy/app/services/optimization_types.py) | Removed fatigue_factor, stimulus_factor from SolverMovement, SolverCircuit, OptimizationResultV2 |
| [app/services/greedy_optimizer.py](file:///Users/shourjosmac/Documents/alloy/app/services/greedy_optimizer.py) | Removed fatigue constraint enforcement and stimulus calculation |
| [app/services/session_generator.py](file:///Users/shourjosmac/Documents/alloy/app/services/session_generator.py) | Removed field copying to SolverMovement/SolverCircuit (lines 2014-2015, 2129-2130) |
| [app/config/optimization_config.yaml](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml) | Removed max_fatigue from OR-Tools config |
| [app/config/optimization_config_loader.py](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config_loader.py) | Removed max_fatigue from ORToolsConfig dataclass |
| [app/api/routes/settings.py](file:///Users/shourjosmac/Documents/alloy/app/api/routes/settings.py) | Removed fatigue_factor, stimulus_factor from API responses (multiple locations) |
| [app/api/routes/logs.py](file:///Users/shourjosmac/Documents/alloy/app/api/routes/logs.py) | Removed total_stimulus, total_fatigue from session initialization and stats updates |
| [app/models/movement.py](file:///Users/shourjosmac/Documents/alloy/app/models/movement.py) | Added DEPRECATED comment to fatigue_factor, stimulus_factor columns |
| [app/models/circuit.py](file:///Users/shourjosmac/Documents/alloy/app/models/circuit.py) | Added DEPRECATED comment to fatigue_factor, stimulus_factor columns |
| [app/models/program.py](file:///Users/shourjosmac/Documents/alloy/app/models/program.py) | Added DEPRECATED comment to total_stimulus, total_fatigue columns |

### Frontend Files

| File | Changes |
|------|---------|
| [frontend/src/types/index.ts](file:///Users/shourjosmac/Documents/alloy/frontend/src/types/index.ts) | Marked fatigue_factor, stimulus_factor as optional for backward compatibility |
| [frontend/src/components/circuit/USAGE_EXAMPLES.tsx](file:///Users/shourjosmac/Documents/alloy/frontend/src/components/circuit/USAGE_EXAMPLES.tsx) | Updated examples to handle optional fields gracefully |
| [frontend/src/components/circuit/CircuitDisplay.test.tsx](file:///Users/shourjosmac/Documents/alloy/frontend/src/components/circuit/CircuitDisplay.test.tsx) | Updated test fixtures for optional fields |
| [frontend/src/components/circuit/CircuitDisplayExample.tsx](file:///Users/shourjosmac/Documents/alloy/frontend/src/components/circuit/CircuitDisplayExample.tsx) | Updated examples with graceful degradation |

### Script Files

| File | Changes |
|------|---------|
| [scripts/enrich_movement_data.py](file:///Users/shourjosmac/Documents/alloy/scripts/enrich_movement_data.py) | Script still calculates these values for backward compatibility but no longer used in optimization |
| [scripts/tools/movement_manager.py](file:///Users/shourjosmac/Documents/alloy/scripts/tools/movement_manager.py) | Movement creation still accepts these fields for backward compatibility |

## Alternatives Considered

### Alternative 1: Keep Fields, Mark as Deprecated
**Rejected** - Creates zombie code and maintenance hazard. Keeping unused fields in active code paths increases technical debt and can confuse developers.

### Alternative 2: Keep Fields, Repurpose for ML Features
**Rejected** - Contradicts RPE-based philosophy. Using these fields as ML features would perpetuate the misconception that fatigue/stimulus are inherent properties.

### Alternative 3: Full Migration Including Database
**Rejected** - Too high risk, no migration path for existing data. Dropping database columns immediately would:
- Break existing API contracts
- Lose historical data integrity
- Require immediate frontend updates
- Have no rollback path

### Alternative 4: Keep Fields for Legacy Code, Remove from New Code
**Partially Adopted** - Database columns preserved, but fields removed from active decision-making code. This provides a compromise that maintains backward compatibility while eliminating the architectural misconception from core logic.

## RPE-Based Fatigue Management Philosophy

### Core Principles

1. **Fatigue is a function of intensity (RPE)**, not movement type
2. **Training objectives determine appropriate fatigue levels**:
   - Strength: Low volume, high intensity (RPE 8-10)
   - Hypertrophy: High volume, moderate intensity (RPE 6-8)
   - Endurance: Very high volume, low intensity (RPE 4-6)
3. **Session-level constraints ensure manageable fatigue**:
   - Limit high-RPE sets per movement pattern
   - Limit total high-RPE sets per session
   - Consider rest periods and recovery needs

### Proposed Implementation (Future)

```python
class RPEFatigueManager:
    """Manages fatigue based on Rate of Perceived Exertion."""

    HIGH_RPE_THRESHOLD = 8  # RPE 8-10 considered high intensity

    PATTERN_LIMITS = {
        "hinge": 2,      # Deadlift and variations
        "squat": 2,      # Squat and variations
        "lunge": 2,      # Lunge and variations
        "olympic": 2,    # Olympic lifts
        "horizontal_push": 4,
        "vertical_push": 4,
        "horizontal_pull": 4,
        "vertical_pull": 4,
    }

    def is_high_rpe_set(self, target_rpe: float) -> bool:
        """Determine if a set is high-intensity based on RPE."""
        return target_rpe >= self.HIGH_RPE_THRESHOLD

    def get_pattern_limit(self, pattern: str) -> int:
        """Get the maximum high-RPE sets for a movement pattern."""
        return self.PATTERN_LIMITS.get(pattern, 4)

    def calculate_session_fatigue(self, exercises: List[SessionExercise]) -> Dict:
        """Calculate fatigue metrics for a session based on RPE."""
        pattern_counts = defaultdict(int)
        high_rpe_sets = 0

        for exercise in exercises:
            movement = exercise.movement
            if self.is_high_rpe_set(exercise.target_rpe):
                pattern_counts[movement.pattern] += 1
                high_rpe_sets += exercise.target_sets

        return {
            "pattern_counts": dict(pattern_counts),
            "high_rpe_sets": high_rpe_sets,
            "exceeds_limits": any(
                count > self.get_pattern_limit(pattern)
                for pattern, count in pattern_counts.items()
            )
        }
```

### Benefits of RPE-Based Approach

1. **Training objective aware**: Respects whether user is training for strength, hypertrophy, or endurance
2. **Intensity adaptive**: Fatigue scales with actual effort, not movement type
3. **Simple constraints**: Easy to understand and enforce
4. **Scientifically grounded**: Based on established principles of sports science
5. **User feedback compatible**: Can incorporate actual logged RPE values for adaptive training

## References

- Related plan documents:
  - [Remove Stimulus and Fatigue Constraints from Program Generation.md](file:///Users/shourjosmac/Documents/alloy/.trae/documents/Remove%20Stimulus%20and%20Fatigue%20Constraints%20from%20Program%20Generation.md)
  - [Complete Removal - Stimulus and Fatigue Type Definitions.md](file:///Users/shourjosmac/Documents/alloy/.trae/documents/Complete%20Removal%20-%20Stimulus%20and%20Fatigue%20Type%20Definitions.md)
- Implementation date: 2026-02-10
- Architecture cleanup documentation: [docs/cleanup_2026-02-10.md](file:///Users/shourjosmac/Documents/alloy/docs/cleanup_2026-02-10.md)
- Movement scoring configuration: [app/config/movement_scoring.yaml](file:///Users/shourjosmac/Documents/alloy/app/config/movement_scoring.yaml) (contains RPE target ranges)
- Movement enrichment script: [scripts/enrich_movement_data.py](file:///Users/shourjosmac/Documents/alloy/scripts/enrich_movement_data.py) (original calculation logic)

## Success Criteria

- Type definitions cleaned (SolverMovement, SolverCircuit, OptimizationResultV2)
- Session generator stops copying removed fields to solver objects
- Configuration files cleaned of zombie values
- Logs API stops setting deprecated fields
- All tests pass with updated fixtures
- No AttributeError or TypeError in production
- Optimization produces feasible solutions more frequently
- Frontend handles optional fields gracefully

## Risk Assessment

| Risk | Likelihood | Severity | Mitigation |
|------|------------|-----------|------------|
| External API consumers break | Low | High | Monitor error logs; add deprecation headers |
| Database migration needed soon | Medium | Medium | Keep columns for 2-3 release cycles |
| Test suite breaks | High | Low | Comprehensive test updates planned |
| Frontend display issues | Low | Low | Optional field handling already implemented |
| Loss of training intelligence | Medium | Medium | RPE-based fatigue management planned for future implementation |

## Migration Path

### Phase 1: Decision Logic Removal (Completed)
- Remove from optimization decision-making
- Remove from session generator
- Remove from configuration files
- Mark database columns as deprecated

### Phase 2: Code Cleanup (In Progress)
- Update type definitions
- Update API responses
- Update test fixtures
- Update frontend types for graceful degradation

### Phase 3: Database Migration (Future, 2-3 release cycles)
- Confirm no external API consumers
- Implement RPE-based fatigue management
- Drop deprecated columns via migration script

### Phase 4: RPE-Based Fatigue Management (Future)
- Implement RPEFatigueManager class
- Add session-level RPE constraints to optimizer
- Incorporate logged RPE values for adaptive training
- Update documentation and user guides
