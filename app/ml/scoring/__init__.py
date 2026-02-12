"""Movement scoring configuration package.

This package provides configuration loading and validation for the
diversity-based movement scoring system.

Main exports:
    - YAMLConfigLoader: Main configuration loader class
    - MovementScoringConfig: Complete configuration dataclass
    - get_config_loader: Get singleton loader instance
    - get_config: Get current configuration
    - GlobalMovementScorer: Main scorer class for movement evaluation
    - ScoringRule: Single scoring rule with condition and score
    - ScoringDimension: Complete scoring dimension with rules and weight
    - ScoringResult: Score breakdown with dimension scores and qualification status
    - ScoringContext: Context object for movement scoring
    - ScoringMetricsTracker: Session metrics tracking and analysis
    - ScoringMetrics: Single session metrics dataclass
    - DimensionScores: Per-dimension scoring breakdown
    - SessionQualityKPI: Session quality validation with block-specific rules
"""
from .config_loader import (
    ConfigError,
    ConfigLoadError,
    ConfigNotFoundError,
    ConfigValidationError,
    CircuitConfig,
    ConfigMetadata,
    DEFAULT_DEBUG_ENABLED,
    DEFAULT_NORMALIZATION_ENABLED,
    DEFAULT_RELAXATION_ENABLED,
    DEFAULT_TIEBREAKER_ENABLED,
    DEFAULT_CONFIG_PATH,
    DisciplineModifier,
    GoalProfile,
    GlobalConfig,
    HardConstraints,
    MovementPreferences,
    MovementScoringConfig,
    PatternCompatibilityMatrix,
    RepSetRange,
    ScoringDimension as ScoringDimensionConfig,
    SubstitutionGroup,
    WeightModifiers,
    YAMLConfigLoader,
    get_config,
    get_config_loader,
)

from .movement_scorer import (
    ScoringError,
    ScoringRuleError,
    ScoringRule,
    ScoringDimension,
    ScoringResult,
    ScoringContext,
    GlobalMovementScorer,
)

from .scoring_metrics import (
    DimensionScores,
    ScoringMetrics,
    SessionContext,
    SessionResult,
    ScoringMetricsTracker,
)

from .exceptions import (
    ScoringException,
    ValidationException,
    SessionValidationError,
    BlockCountValidationError,
    StructureValidationError,
    PatternRotationError,
    MovementDiversityError,
    InsufficientCoverageError,
    MetricsValidationError,
    StorageException,
    MetricsStorageError,
)

from .base import (
    ValidationResult,
    BaseValidationResult,
    BaseValidator,
    ValidationMixin,
)

from .constants import (
    TimeUtilization,
    MovementCounts,
    ScoringThresholds,
    SessionTypes,
    ScoringDimensions,
    VarietyWeights,
    MuscleGroups,
    PatternRotation,
    MessageTemplates,
    OptimizationConstants,
    TIME_UTILIZATION_TOLERANCE,
    MIN_MOVEMENT_COUNT,
    MAX_MOVEMENT_COUNT,
    QUALIFICATION_THRESHOLD,
    MOVEMENT_DIVERSITY_THRESHOLD,
    OVERALL_VARIETY_THRESHOLD,
    MUSCLE_COVERAGE_THRESHOLD,
)

from .session_quality_kpi import (
    BlockValidationResult,
    StructureValidationResult,
    SessionQualityKPI,
    SessionResult as SessionQualityResult,
)

__all__ = [
    # Main loader and config
    "YAMLConfigLoader",
    "MovementScoringConfig",
    "get_config_loader",
    "get_config",
    # Scorer
    "GlobalMovementScorer",
    "ScoringRule",
    "ScoringDimension",
    "ScoringResult",
    "ScoringContext",
    # Metrics tracker
    "ScoringMetricsTracker",
    "ScoringMetrics",
    "DimensionScores",
    "SessionContext",
    "SessionResult",
    # Session quality KPI
    "SessionQualityKPI",
    "SessionQualityResult",
    "BlockValidationResult",
    "StructureValidationResult",
    # Base classes and protocols
    "ValidationResult",
    "BaseValidationResult",
    "BaseValidator",
    "ValidationMixin",
    # Constants
    "TimeUtilization",
    "MovementCounts",
    "ScoringThresholds",
    "SessionTypes",
    "ScoringDimensions",
    "VarietyWeights",
    "MuscleGroups",
    "PatternRotation",
    "MessageTemplates",
    "TIME_UTILIZATION_TOLERANCE",
    "MIN_MOVEMENT_COUNT",
    "MAX_MOVEMENT_COUNT",
    "QUALIFICATION_THRESHOLD",
    "MOVEMENT_DIVERSITY_THRESHOLD",
    "OVERALL_VARIETY_THRESHOLD",
    "MUSCLE_COVERAGE_THRESHOLD",
    "OptimizationConstants",
    # Exceptions
    "ConfigError",
    "ConfigLoadError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "ScoringError",
    "ScoringRuleError",
    "ScoringException",
    "ValidationException",
    "SessionValidationError",
    "BlockCountValidationError",
    "StructureValidationError",
    "PatternRotationError",
    "MovementDiversityError",
    "InsufficientCoverageError",
    "MetricsValidationError",
    "StorageException",
    "MetricsStorageError",
    # Config dataclasses
    "ScoringDimensionConfig",
    "SubstitutionGroup",
    "PatternCompatibilityMatrix",
    "MuscleRelationship",
    "WeightModifiers",
    "MovementPreferences",
    "GoalProfile",
    "DisciplineModifier",
    "RepSetRange",
    "CircuitConfig",
    "HardConstraints",
    "GlobalConfig",
    "ConfigMetadata",
    # Global constants
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_NORMALIZATION_ENABLED",
    "DEFAULT_TIEBREAKER_ENABLED",
    "DEFAULT_RELAXATION_ENABLED",
    "DEFAULT_DEBUG_ENABLED",
]
