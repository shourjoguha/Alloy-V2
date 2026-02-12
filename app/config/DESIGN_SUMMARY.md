# Optimization Config Loader Design Summary

## Overview

I've designed a comprehensive configuration loading system for the unified `optimization_config.yaml` that provides Pydantic validation, hot-reload support, type-safe access, and backward compatibility.

## Files Created

### 1. [optimization_config_loader.py](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config_loader.py) (~1100 lines)

The main configuration loader module with:

**Pydantic Models (13+ models):**
- `OptimizationConfig` - Root configuration model
- `ORToolsConfig` - OR-Tools solver settings
- `DiversityOptimizerConfig` - Diversity optimizer settings
- `HardConstraints` - Time, variety, user, safety constraints
- `RepSetRanges` - Warmup, circuit, lifting, cardio, mobility ranges
- `CircuitConfig` - Circuit-specific settings
- `GlobalConfig` - Normalization, tiebreaker, relaxation settings
- `Metadata` - Configuration metadata and versioning
- `RepSetRange`, `TimeConstraints`, `VarietyConstraints`, `UserRules`, `SafetyConstraints`
- `NormalizationConfig`, `TiebreakerConfig`, `RelaxationConfig`

**Enums (7 enums):**
- `SolverStrategy` - or_tools, diversity_optimizer, legacy, hybrid
- `ScoringMethod` - diversity_based, ml_based, hybrid, legacy
- `NormalizationMethod` - min_max, z_score, robust, none
- `TiebreakerStrategy` - priority_hierarchy, random, score_sum, custom
- `RelaxationStrategy` - soft_constraints, penalty_based, constraint_relaxation, none
- `CircuitType` - amrap, emom, for_time, rounds, tabata
- `FatigueLevel` - low, medium, high

**Core Classes:**
- `OptimizationConfigLoader` - Main loader with hot-reload support
- `ReloadStatistics` - Statistics tracking for reloads
- `LegacyConfigAdapter` - Backward compatibility adapter
- `ConfigReloadCallback` - Protocol for reload callbacks

**Convenience Functions:**
- `get_optimization_config_loader()` - Singleton loader access
- `get_optimization_config()` - Get current config
- `reload_optimization_config()` - Manual reload
- `reset_optimization_config_loader()` - Reset singleton

**Custom Exceptions:**
- `OptimizationConfigError` - Base exception
- `OptimizationConfigValidationError` - Validation errors
- `OptimizationConfigLoadError` - Load errors
- `OptimizationConfigNotFoundError` - File not found

### 2. [optimization_config.yaml](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config.yaml)

Sample configuration file with all sections:
- Metadata (version, author, description, environment)
- OR-Tools solver configuration
- Diversity optimizer configuration
- Hard constraints (time, variety, user rules, safety)
- Rep/set ranges for different movement types
- Circuit configuration
- Global configuration (normalization, tiebreaker, relaxation)

### 3. [optimization_config_examples.py](file:///Users/shourjosmac/Documents/alloy/app/config/optimization_config_examples.py) (~350 lines)

Comprehensive usage examples covering:
- Basic configuration access
- Solver configuration access
- Constraints configuration
- Rep/set ranges
- Advanced configuration options
- Hot-reload with callbacks
- Manual reload operations
- Custom loader instances
- Error handling
- Backward compatibility usage
- Custom model creation
- Thread-safe access patterns

### 4. [MIGRATION_GUIDE.md](file:///Users/shourjosmac/Documents/alloy/app/config/MIGRATION_GUIDE.md)

Complete migration guide with:
- Overview of new system
- Step-by-step migration instructions
- Code change examples
- Backward compatibility patterns
- Testing strategies
- Troubleshooting guide
- Best practices

### 5. [test_optimization_config_loader.py](file:///Users/shourjosmac/Documents/alloy/app/config/test_optimization_config_loader.py)

Unit tests covering:
- Model validation tests
- Configuration loader tests
- Backward compatibility tests
- Activity distribution integration tests

### 6. Updated Files

**[activity_distribution.py](file:///Users/shourjosmac/Documents/alloy/app/config/activity_distribution.py):**
- Added backward compatibility functions
- `get_or_tools_max_fatigue()`
- `get_or_tools_solver_timeout_seconds()`
- `get_or_tools_min_sets_per_movement()`
- `get_or_tools_max_sets_per_movement()`
- `get_or_tools_volume_target_reduction_pct()`
- Legacy constants marked as deprecated

**[__init__.py](file:///Users/shourjosmac/Documents/alloy/app/config/__init__.py):**
- Updated documentation to reflect new configuration system
- Added lazy import hint for optimization config

## Key Features

### 1. Pydantic Validation

All configuration models use Pydantic for automatic validation:

```python
from app.config.optimization_config_loader import get_optimization_config

config = get_optimization_config()
# All values are guaranteed to be valid and type-safe
timeout = config.or_tools.timeout_seconds  # int, validated
```

### 2. Hot-Reload Support

Configuration changes are detected and reloaded without restart:

```python
loader = get_optimization_config_loader(enable_hot_reload=True)

# Register callback for reload notifications
def on_reload(new_config):
    print(f"Config reloaded: {new_config.metadata.version}")

loader.register_reload_callback(on_reload)

# Reload statistics
stats = loader.get_reload_statistics()
print(f"Reloads: {stats.total_reloads}")
```

### 3. Type-Safe Access

Full IDE support with type hints:

```python
from app.config.optimization_config_loader import (
    OptimizationConfig,
    get_optimization_config,
)

def solve(config: OptimizationConfig) -> Solution:
    # IDE autocompletion for all config fields
    timeout = config.or_tools.timeout_seconds
    max_fatigue = config.or_tools.max_fatigue
    ...
```

### 4. Backward Compatibility

Existing code continues to work during migration:

```python
# Old way still works (deprecated)
from app.config.activity_distribution import or_tools_max_fatigue
max_fatigue = or_tools_max_fatigue

# New recommended way
from app.config.activity_distribution import get_or_tools_max_fatigue
max_fatigue = get_or_tools_max_fatigue()  # Reads from YAML

# Direct new way
from app.config.optimization_config_loader import get_optimization_config
config = get_optimization_config()
max_fatigue = config.or_tools.max_fatigue
```

### 5. Thread-Safe Access

Safe concurrent access with context manager:

```python
with loader.get_config_context() as config:
    # Thread-safe access within this block
    timeout = config.or_tools.timeout_seconds
```

### 6. Comprehensive Error Messages

Clear validation errors with context:

```
OptimizationConfigValidationError: Validation failed with 2 error(s):
  - or_tools.min_sets_per_movement: must be >= 0 (type: greater_than_equal)
  - or_tools.max_sets_per_movement: min_sets_per_movement (5) must be <= max_sets_per_movement (2)
```

## Integration with Existing Pattern

The new loader follows the same pattern as the existing `YAMLConfigLoader`:

| Feature | Existing (YAMLConfigLoader) | New (OptimizationConfigLoader) |
|---------|----------------------------|-------------------------------|
| Validation | Dataclass assertions | Pydantic models |
| Type Safety | Runtime checks | Compile-time + runtime |
| Hot-Reload | Yes | Yes |
| Thread-Safe | Yes (RLock) | Yes (RLock) |
| Callbacks | Yes | Yes |
| Statistics | No | Yes |
| Error Messages | Generic | Detailed |

## Migration Path

1. **Phase 1: Existing code works**
   - Legacy constants remain available
   - Getter functions provide bridge to new config
   - No changes required to existing code

2. **Phase 2: Gradual migration**
   - New code uses `get_optimization_config()`
   - Existing code updated incrementally
   - Legacy constants deprecated but functional

3. **Phase 3: Full migration**
   - All code uses new system
   - Legacy constants removed
   - Getter functions deprecated

## Usage Examples

### Basic Access

```python
from app.config.optimization_config_loader import get_optimization_config

config = get_optimization_config()
print(f"Version: {config.metadata.version}")
print(f"Timeout: {config.or_tools.timeout_seconds}s")
print(f"Max fatigue: {config.or_tools.max_fatigue}")
```

### With Hot-Reload

```python
from app.config.optimization_config_loader import (
    get_optimization_config_loader,
    OptimizationConfig,
)

def on_reloaded(new_config: OptimizationConfig):
    print(f"Config updated to v{new_config.metadata.version}")

loader = get_optimization_config_loader(enable_hot_reload=True)
loader.register_reload_callback(on_reloaded)
```

### Backward Compatibility

```python
# Using activity_distribution bridge
from app.config.activity_distribution import get_or_tools_max_fatigue

max_fatigue = get_or_tools_max_fatigue()
```

## Configuration Structure

```yaml
optimization_config.yaml
├── metadata              # Version, author, environment
├── or_tools             # OR-Tools solver settings
├── diversity_optimizer   # Diversity optimizer settings
├── hard_constraints      # Time, variety, user, safety
├── rep_set_ranges       # Warmup, circuit, lifting, cardio, mobility
├── circuit_config        # Circuit-specific settings
└── global_config        # Normalization, tiebreaker, relaxation
```

## Testing

Run the test suite:

```bash
cd /Users/shourjosmac/Documents/alloy
python -m pytest app/config/test_optimization_config_loader.py -v
```

## Dependencies

Required packages:
- `pydantic` - Data validation
- `pydantic-settings` - Settings management
- `yaml` - YAML parsing
- `pyyaml` - YAML implementation

Install if needed:
```bash
pip install pydantic pydantic-settings pyyaml
```

## Summary

The new configuration system provides:

- Type-safe configuration access with Pydantic
- Hot-reload support for production updates
- Thread-safe concurrent access
- Comprehensive validation with detailed errors
- Full backward compatibility during migration
- Clear migration path and documentation
- Extensive examples and tests

All while following the existing `config_loader.py` patterns and maintaining consistency with the codebase.
