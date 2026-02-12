# Optimization Configuration Migration Guide

This guide helps you migrate from the legacy configuration system to the new unified `optimization_config.yaml` with Pydantic-based validation.

## Table of Contents

1. [Overview](#overview)
2. [What's New](#whats-new)
3. [Migration Steps](#migration-steps)
4. [Code Changes](#code-changes)
5. [Backward Compatibility](#backward-compatibility)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The new configuration system provides:

- **Pydantic Validation**: Type-safe configuration with automatic validation
- **Hot-Reload Support**: Configuration changes apply without restart
- **Centralized Location**: All optimization config in one file
- **Better Error Messages**: Clear validation errors with detailed context
- **Thread-Safe Access**: Safe concurrent configuration access

---

## What's New

### New File Structure

```
app/config/
├── optimization_config.yaml          # New: Unified optimization config
├── optimization_config_loader.py      # New: Pydantic-based loader
├── optimization_config_examples.py    # New: Usage examples
├── activity_distribution.py           # Updated: Backward compatibility
└── settings.py                       # Unchanged: Environment settings
```

### New Pydantic Models

- `OptimizationConfig`: Main configuration model
- `ORToolsConfig`: OR-Tools solver settings
- `DiversityOptimizerConfig`: Diversity optimizer settings
- `HardConstraints`: Time, variety, user, safety constraints
- `RepSetRanges`: Warmup, circuit, lifting, cardio, mobility ranges
- `CircuitConfig`: Circuit-specific settings
- `GlobalConfig`: Normalization, tiebreaker, relaxation settings

---

## Migration Steps

### Step 1: Review the New Configuration File

Review the new `optimization_config.yaml` to understand the structure:

```yaml
metadata:
  version: "1.0.0"
  author: "Development Team"
  description: "Unified optimization configuration"

or_tools:
  enabled: true
  timeout_seconds: 60
  max_fatigue: 8.0
  # ... more settings

diversity_optimizer:
  enabled: false
  scoring_method: "diversity_based"
  # ... more settings

hard_constraints:
  time:
    enforce: true
    max_time_per_block_minutes: 45
    # ... more settings

# ... more sections
```

### Step 2: Update Your Code

#### Old Way (Legacy Direct Import)

```python
from app.config.activity_distribution import (
    or_tools_max_fatigue,
    or_tools_solver_timeout_seconds,
)

max_fatigue = or_tools_max_fatigue
timeout = or_tools_solver_timeout_seconds
```

#### New Way (Type-Safe Access)

```python
from app.config.optimization_config_loader import get_optimization_config

config = get_optimization_config()
max_fatigue = config.or_tools.max_fatigue
timeout = config.or_tools.timeout_seconds
```

### Step 3: Update Service Code

Find code that uses OR-Tools settings and update it:

```python
# Before
from app.config.activity_distribution import or_tools_solver_timeout_seconds

solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = or_tools_solver_timeout_seconds

# After
from app.config.optimization_config_loader import get_optimization_config

config = get_optimization_config()
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = config.or_tools.timeout_seconds
```

### Step 4: Add Hot-Reload Callbacks (Optional)

If you need to react to configuration changes:

```python
from app.config.optimization_config_loader import (
    get_optimization_config_loader,
    OptimizationConfig,
)

def on_config_reloaded(new_config: OptimizationConfig) -> None:
    """Handle configuration reload."""
    print(f"Config reloaded to version: {new_config.metadata.version}")
    # Update your internal state if needed

loader = get_optimization_config_loader()
loader.register_reload_callback(on_config_reloaded)
```

---

## Code Changes

### Common Migration Patterns

#### Pattern 1: Simple Value Access

**Before:**
```python
from app.config.activity_distribution import or_tools_max_fatigue

if movement_fatigue > or_tools_max_fatigue:
    return False
```

**After:**
```python
from app.config.optimization_config_loader import get_optimization_config

config = get_optimization_config()
if movement_fatigue > config.or_tools.max_fatigue:
    return False
```

#### Pattern 2: Configuration Validation

**Before:**
```python
# No validation, runtime errors possible
timeout = or_tools_solver_timeout_seconds  # Could be invalid
```

**After:**
```python
# Pydantic validates on load
config = get_optimization_config()
timeout = config.or_tools.timeout_seconds  # Guaranteed valid
```

#### Pattern 3: Nested Configuration Access

**Before:**
```python
# Had to access multiple constants
from app.config.activity_distribution import (
    or_tools_min_sets_per_movement,
    or_tools_max_sets_per_movement,
)

sets_range = (or_tools_min_sets_per_movement, or_tools_max_sets_per_movement)
```

**After:**
```python
# Single access point
config = get_optimization_config()
sets_range = (
    config.or_tools.min_sets_per_movement,
    config.or_tools.max_sets_per_movement,
)
```

---

## Backward Compatibility

### Using Legacy Constants (Deprecated)

Legacy constants are still available but deprecated:

```python
from app.config.activity_distribution import (
    or_tools_max_fatigue,  # Deprecated
    or_tools_solver_timeout_seconds,  # Deprecated
)

# This still works but will be removed in future
max_fatigue = or_tools_max_fatigue
```

### Using Backward Compatibility Functions

For gradual migration, use the getter functions:

```python
from app.config.activity_distribution import get_or_tools_max_fatigue

# Reads from optimization_config.yaml if available
# Falls back to legacy constant otherwise
max_fatigue = get_or_tools_max_fatigue()
```

### Using Legacy Adapter

The `LegacyConfigAdapter` provides a bridge:

```python
from app.config.optimization_config_loader import (
    get_optimization_config,
    LegacyConfigAdapter,
)

config = get_optimization_config()
adapter = LegacyConfigAdapter(config)

# Legacy-style property access
max_fatigue = adapter.or_tools_max_fatigue
timeout = adapter.or_tools_solver_timeout_seconds

# Dot-notation access
timeout = adapter.get("or_tools.timeout_seconds")

# Convert to dict
config_dict = adapter.to_dict()
```

---

## Testing

### Unit Testing with Mock Config

```python
from app.config.optimization_config_loader import OptimizationConfig
from unittest.mock import patch

@patch("app.config.optimization_config_loader.get_optimization_config")
def test_solver_timeout(mock_get_config):
    # Create mock config
    mock_config = OptimizationConfig(
        metadata=Metadata(
            version="1.0.0",
            author="Test",
            description="Test",
        ),
        or_tools=ORToolsConfig(
            enabled=True,
            timeout_seconds=120,  # Custom timeout for test
        ),
        diversity_optimizer=DiversityOptimizerConfig(enabled=False),
        # ... other required fields
    )

    mock_get_config.return_value = mock_config

    # Test uses custom timeout
    config = get_optimization_config()
    assert config.or_tools.timeout_seconds == 120
```

### Testing Validation Errors

```python
import pytest
from app.config.optimization_config_loader import OptimizationConfigValidationError

def test_invalid_config():
    with pytest.raises(OptimizationConfigValidationError):
        OptimizationConfig(
            metadata=Metadata(
                version="invalid",  # Invalid version format
                author="Test",
                description="Test",
            ),
            or_tools=ORToolsConfig(enabled=False),
            diversity_optimizer=DiversityOptimizerConfig(enabled=False),
        )
```

### Testing Hot-Reload

```python
from app.config.optimization_config_loader import (
    get_optimization_config_loader,
    reset_optimization_config_loader,
)

def test_config_reload():
    # Reset to use a test config
    reset_optimization_config_loader()

    loader = get_optimization_config_loader(
        config_path="/path/to/test/config.yaml",
        enable_hot_reload=False,
    )

    # Get initial config
    config1 = loader.get_config()

    # Modify config file...

    # Reload
    config2 = loader.reload_config()

    # Verify reload
    assert config2.metadata.last_updated > config1.metadata.last_updated
```

---

## Troubleshooting

### Issue: Import Error

**Problem:**
```
ImportError: cannot import name 'get_optimization_config'
```

**Solution:**
Ensure pydantic and pydantic-settings are installed:
```bash
pip install pydantic pydantic-settings
```

### Issue: Configuration File Not Found

**Problem:**
```
OptimizationConfigNotFoundError: Configuration file not found
```

**Solution:**
Create the `optimization_config.yaml` file in the `app/config/` directory, or provide a custom path:
```python
from app.config.optimization_config_loader import get_optimization_config_loader

loader = get_optimization_config_loader(
    config_path="/path/to/your/config.yaml"
)
```

### Issue: Validation Error

**Problem:**
```
OptimizationConfigValidationError: Validation failed with X error(s)
```

**Solution:**
Check the error message for details. Common issues:
- Invalid version format (use semantic versioning like "1.0.0")
- Min values greater than max values (e.g., sets_min > sets_max)
- Invalid enum values (check allowed values in Enums)

### Issue: Hot-Reload Not Working

**Problem:**
Configuration changes aren't detected.

**Solution:**
Ensure hot-reload is enabled:
```python
loader = get_optimization_config_loader(enable_hot_reload=True)
```

Check if the file modification time is being updated (some editors have atomic save settings).

### Issue: Thread Safety Concerns

**Problem:**
Potential race conditions when accessing config from multiple threads.

**Solution:**
Use the context manager for thread-safe access:
```python
with loader.get_config_context() as config:
    # Safe access within this block
    timeout = config.or_tools.timeout_seconds
```

---

## Best Practices

### 1. Use Type Hints

```python
from app.config.optimization_config_loader import OptimizationConfig

def solve_optimization(config: OptimizationConfig) -> Solution:
    timeout = config.or_tools.timeout_seconds
    # ...
```

### 2. Cache Configuration Access

```python
from functools import lru_cache
from app.config.optimization_config_loader import get_optimization_config

@lru_cache(maxsize=1)
def get_cached_config() -> OptimizationConfig:
    return get_optimization_config()
```

### 3. Handle Errors Gracefully

```python
from app.config.optimization_config_loader import (
    get_optimization_config,
    OptimizationConfigLoadError,
)

try:
    config = get_optimization_config()
except OptimizationConfigLoadError as e:
    logger.error(f"Failed to load config: {e}")
    # Use fallback or defaults
    config = get_default_config()
```

### 4. Use Environment-Specific Configs

```yaml
# optimization_config.yaml
metadata:
  environment: "production"  # or "development", "staging"
```

### 5. Document Configuration Changes

When modifying the YAML, update the `metadata.last_updated` field:
```yaml
metadata:
  version: "1.1.0"
  last_updated: "2026-02-10T14:30:00Z"
  description: "Increased default timeout to 90s"
```

---

## Summary

| Aspect | Old System | New System |
|--------|-----------|-----------|
| Type Safety | No | Yes (Pydantic) |
| Validation | Runtime | Load-time + Runtime |
| Hot-Reload | No | Yes |
| Error Messages | Generic | Detailed |
| Thread Safety | No | Yes |
| File Location | Multiple constants | Single YAML file |
| Backward Compatible | N/A | Yes (migration period) |

---

## Additional Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Configuration Examples](optimization_config_examples.py)
- [API Reference](optimization_config_loader.py)

For questions or issues, refer to the examples in `optimization_config_examples.py` or the detailed docstrings in `optimization_config_loader.py`.
