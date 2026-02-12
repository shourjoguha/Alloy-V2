"""Application configuration module.

This module organizes configuration into specialized files:

- **settings.py**: Environment-based settings (Pydantic BaseSettings)
  - Database URL, LLM config, JWT secrets, API tokens
  - Loaded from .env file via pydantic-settings

- **activity_distribution.py**: Domain logic constants with rationale
  - Goal weights, finisher presets, session timing
  - Includes BIAS_RATIONALE documentation for transparency
  - OR-Tools solver configuration (migrated to optimization_config.yaml)

- **features.py**: Feature flags system
  - Gradual rollout support, A/B testing capability
  - In-memory flag management with environment overrides

- **movement_scoring.yaml**: ML scoring configuration
  - Hot-reloadable via YAMLConfigLoader
  - Scoring dimensions, weights, thresholds, goal profiles

- **optimization_config.yaml**: Unified optimization configuration
  - Hot-reloadable via OptimizationConfigLoader (Pydantic-based)
  - OR-Tools solver settings, diversity optimizer, constraints, rep/set ranges
  - Normalization, tiebreaker, relaxation strategies
"""
from app.config.settings import Settings, get_settings

# Optimization config loader (lazy import to avoid circular dependencies)
# Use: from app.config.optimization_config_loader import get_optimization_config

__all__ = ["Settings", "get_settings"]
