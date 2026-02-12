"""
Centralized program-distribution and goal-bias configuration.

This module intentionally includes plain-text bias rationale so the system's
implicit choices are inspectable (e.g., why fat loss tends to add cardio blocks
or metabolic finishers).

BACKWARD COMPATIBILITY:
This module now provides backward compatibility by reading from optimization_config.yaml
when available, falling back to legacy constants otherwise. During migration, code
that previously accessed OR-Tools constants directly will work transparently.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ============================================================================
# Legacy Constants (for backward compatibility)
# ============================================================================

mobility_max_pct: float = 0.30
cardio_max_pct: float = 0.75

preference_deviation_pct: float = 0.15

default_microcycle_length_days: int = 14

min_conditioning_minutes: int = 30
min_conditioning_unique_movements: int = 5

default_lifting_warmup_minutes: int = 10
default_lifting_cooldown_minutes: int = 5

default_finisher_minutes: int = 8
max_finisher_minutes: int = 15

goal_finisher_thresholds = {
    "fat_loss_min_weight": 5,
    "endurance_min_weight": 6,
}

goal_finisher_presets = {
    "fat_loss": {
        "type": "circuit",
        "circuit_type": "AMRAP",
        "rounds": "Max Rounds",
        "duration_minutes": 8,
        "notes": "Metabolic finisher",
        "exercises": [
            {"movement": "Kettlebell Swing", "reps": 15},
            {"movement": "Burpee", "reps": 10},
            {"movement": "Mountain Climber", "duration_seconds": 40},
        ],
    },
    "endurance": {
        "type": "interval",
        "circuit_type": "EMOM",
        "rounds": "10 Rounds",
        "duration_minutes": 10,
        "notes": "Endurance intervals",
        "exercises": [
            {"movement": "Rowing Machine", "duration_seconds": 60},
            {"movement": "Cardio Intervals", "duration_seconds": 30},
        ],
    },
}

goal_bucket_weights = {
    "strength": {"lifting": 1.0},
    "hypertrophy": {"lifting": 1.0},
    "fat_loss": {"cardio": 0.2, "finisher": 0.5, "lifting": 0.3},
    "endurance": {"cardio": 0.5, "finisher": 0.5},
    "mobility": {"mobility": 1.0},
}

endurance_heavy_dedicated_cardio_day_default: bool = True
endurance_heavy_dedicated_cardio_day_min_weight: int = 6
endurance_heavy_dedicated_cardio_day_min_cycle_length_days: int = 7


# ============================================================================
# Backward Compatibility Functions
# ============================================================================

def get_or_tools_max_fatigue() -> float:
    """Get OR-Tools max fatigue from unified config (backward compatibility).

    Returns:
        Max fatigue value from optimization_config.yaml or legacy default.

    Example:
        >>> from app.config.activity_distribution import get_or_tools_max_fatigue
        >>> max_fatigue = get_or_tools_max_fatigue()
    """
    try:
        from app.config.optimization_config_loader import (
            get_optimization_config,
            OptimizationConfigLoadError,
        )
        config = get_optimization_config()
        return config.or_tools.max_fatigue
    except (ImportError, OptimizationConfigLoadError, Exception):
        # Fall back to legacy constant
        return 8.0


def get_or_tools_solver_timeout_seconds() -> int:
    """Get OR-Tools solver timeout from unified config (backward compatibility).

    Returns:
        Solver timeout in seconds from optimization_config.yaml or legacy default.

    Example:
        >>> from app.config.activity_distribution import get_or_tools_solver_timeout_seconds
        >>> timeout = get_or_tools_solver_timeout_seconds()
    """
    try:
        from app.config.optimization_config_loader import (
            get_optimization_config,
            OptimizationConfigLoadError,
        )
        config = get_optimization_config()
        return config.or_tools.timeout_seconds
    except (ImportError, OptimizationConfigLoadError, Exception):
        # Fall back to legacy constant
        return 60


def get_or_tools_min_sets_per_movement() -> int:
    """Get OR-Tools min sets from unified config (backward compatibility).

    Returns:
        Minimum sets per movement from optimization_config.yaml or legacy default.

    Example:
        >>> from app.config.activity_distribution import get_or_tools_min_sets_per_movement
        >>> min_sets = get_or_tools_min_sets_per_movement()
    """
    try:
        from app.config.optimization_config_loader import (
            get_optimization_config,
            OptimizationConfigLoadError,
        )
        config = get_optimization_config()
        return config.or_tools.min_sets_per_movement
    except (ImportError, OptimizationConfigLoadError, Exception):
        # Fall back to legacy constant
        return 2


def get_or_tools_max_sets_per_movement() -> int:
    """Get OR-Tools max sets from unified config (backward compatibility).

    Returns:
        Maximum sets per movement from optimization_config.yaml or legacy default.

    Example:
        >>> from app.config.activity_distribution import get_or_tools_max_sets_per_movement
        >>> max_sets = get_or_tools_max_sets_per_movement()
    """
    try:
        from app.config.optimization_config_loader import (
            get_optimization_config,
            OptimizationConfigLoadError,
        )
        config = get_optimization_config()
        return config.or_tools.max_sets_per_movement
    except (ImportError, OptimizationConfigLoadError, Exception):
        # Fall back to legacy constant
        return 5


def get_or_tools_volume_target_reduction_pct() -> float:
    """Get OR-Tools volume reduction from unified config (backward compatibility).

    Returns:
        Volume target reduction percentage from optimization_config.yaml or legacy default.

    Example:
        >>> from app.config.activity_distribution import get_or_tools_volume_target_reduction_pct
        >>> reduction = get_or_tools_volume_target_reduction_pct()
    """
    try:
        from app.config.optimization_config_loader import (
            get_optimization_config,
            OptimizationConfigLoadError,
        )
        config = get_optimization_config()
        return config.or_tools.volume_target_reduction_pct
    except (ImportError, OptimizationConfigLoadError, Exception):
        # Fall back to legacy constant
        return 0.2


# Legacy OR-Tools constants (kept for backward compatibility, deprecated)
# These are deprecated and will be removed in a future version.
# Use the getter functions above instead.
or_tools_max_fatigue: float = 8.0  # Deprecated: use get_or_tools_max_fatigue()
or_tools_solver_timeout_seconds: int = 60  # Deprecated: use get_or_tools_solver_timeout_seconds()
or_tools_min_sets_per_movement: int = 2  # Deprecated: use get_or_tools_min_sets_per_movement()
or_tools_max_sets_per_movement: int = 5  # Deprecated: use get_or_tools_max_sets_per_movement()
or_tools_volume_target_reduction_pct: float = 0.2  # Deprecated: use get_or_tools_volume_target_reduction_pct()

BIAS_RATIONALE = {
    "fat_loss": "Bias toward higher weekly energy expenditure via cardio blocks and/or metabolic finishers while keeping lifting exposure for lean mass retention.",
    "endurance": "Bias toward time-under-aerobic-load via cardio blocks or interval-style finishers; lifting stays but is not the sole driver.",
    "strength": "Bias toward main lifts and accessory volume; cardio is minimized unless required for safety or user preference.",
    "hypertrophy": "Bias toward main lifts plus accessories for volume; finishers are deprioritized unless fat loss/endurance is also high.",
    "mobility": "Bias toward mobility sessions and extended warmup/cooldown; mobility time is capped to prevent dominating the week.",
    "conditioning": "Conditioning-only sessions are reserved for explicit allowance or safe scenarios; they require 5+ conditioning movements and 30+ minutes.",
}

HARD_CODED_BIAS_LOCATIONS = [
    "app/services/program.py:create_program split-template selection (days_per_week-based)",
    "app/config/activity_distribution.py:goal_bucket_weights and goal_finisher_thresholds",
]
