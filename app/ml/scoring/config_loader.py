"""YAML configuration loader with schema validation and hot-reload support.

This module provides a robust configuration loader that loads YAML configs,
validates them against defined schemas, and supports hot-reloading of configuration
changes without application restart.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import threading
import time
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import yaml

# Global constants for configuration paths
# These can be modified by changing the module-level variables
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent.parent
CONFIG_DIR: Final[Path] = PROJECT_ROOT / "app" / "config"
DEFAULT_CONFIG_PATH: Final[Path] = CONFIG_DIR / "movement_scoring.yaml"

# Default global variables referenced in the YAML
DEFAULT_NORMALIZATION_ENABLED: bool = True
DEFAULT_TIEBREAKER_ENABLED: bool = True
DEFAULT_RELAXATION_ENABLED: bool = True
DEFAULT_DEBUG_ENABLED: bool = False


logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base exception for configuration errors."""

    def __init__(self, message: str, path: str | None = None) -> None:
        self.message = message
        self.path = path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.path:
            return f"Config error in '{self.path}': {self.message}"
        return f"Config error: {self.message}"


class ConfigValidationError(ConfigError):
    """Raised when configuration fails schema validation."""

    pass


class ConfigLoadError(ConfigError):
    """Raised when configuration fails to load."""

    pass


class ConfigNotFoundError(ConfigError):
    """Raised when configuration file is not found."""

    pass


@dataclass(frozen=True)
class ScoringDimension:
    """Represents a single scoring dimension configuration.

    Attributes:
        priority_level: The priority level (1-7) for this dimension
        weight: The weight multiplier for this dimension
        description: Human-readable description of the dimension
        penalty_mismatch: Penalty score for mismatched patterns
        bonus_exact_match: Bonus score for exact matches
    """

    priority_level: int
    weight: float
    description: str
    penalty_mismatch: float | None = None
    bonus_exact_match: float | None = None
    bonus_unique_primary: float | None = None
    penalty_repeated_primary: float | None = None
    bonus_matched_discipline: float | None = None
    penalty_discipline_mismatch: float | None = None
    neutral_default: float | None = None
    bonus_compound: float | None = None
    neutral_hybrid: float | None = None
    penalty_isolation: float | None = None
    bonus_target_muscle: float | None = None
    neutral_non_target: float | None = None
    specialization_threshold: float | None = None
    bonus_goal_match: float | None = None
    neutral_goal_agnostic: float | None = None
    penalty_goal_conflict: float | None = None
    bonus_efficient: float | None = None
    neutral_average: float | None = None
    penalty_inefficient: float | None = None
    max_primary_repeats_per_session: int | None = None
    max_primary_repeats_per_microcycle: int | None = None


@dataclass(frozen=True)
class SubstitutionGroup:
    """Represents a pattern substitution group configuration.

    Attributes:
        name: Name of the substitution group
        patterns: List of pattern names in this group
        compatibility_matrix: Dict mapping patterns to their compatibility scores
    """

    name: str
    patterns: tuple[str, ...]
    compatibility_matrix: dict[str, dict[str, float]]


@dataclass(frozen=True)
class PatternCompatibilityMatrix:
    """Configuration for pattern compatibility and substitution rules.

    Attributes:
        substitution_groups: List of substitution group configurations
        cross_substitution_allowed: Whether cross-group substitution is allowed
        min_substitution_score: Minimum score threshold for substitutions
        exact_match_bonus: Bonus multiplier for exact pattern matches
    """

    substitution_groups: tuple[SubstitutionGroup, ...]
    cross_substitution_allowed: bool
    min_substitution_score: float
    exact_match_bonus: float


@dataclass(frozen=True)
class MuscleRelationship:
    """Represents relationships between muscle groups.

    Attributes:
        name: Name of the primary muscle group
        primary: Whether this is a primary muscle group
        synergists: List of synergist muscle groups
        related: List of related muscle groups
    """

    name: str
    primary: bool
    synergists: tuple[str, ...]
    related: tuple[str, ...]


@dataclass(frozen=True)
class WeightModifiers:
    """Weight modifiers for scoring dimensions.

    Attributes:
        compound_bonus: Modifier for compound bonus dimension
        pattern_alignment: Modifier for pattern alignment dimension
        muscle_coverage: Modifier for muscle coverage dimension
        discipline_preference: Modifier for discipline preference dimension
        goal_alignment: Modifier for goal alignment dimension
        time_utilization: Modifier for time utilization dimension
        specialization: Modifier for specialization dimension
    """

    compound_bonus: float
    pattern_alignment: float
    muscle_coverage: float
    discipline_preference: float
    goal_alignment: float
    time_utilization: float
    specialization: float


@dataclass(frozen=True)
class MovementPreferences:
    """Preferences for movement types.

    Attributes:
        compound: Preference multiplier for compound movements
        isolation: Preference multiplier for isolation movements
        olympic: Preference multiplier for olympic movements
        plyometric: Preference multiplier for plyometric movements
    """

    compound: float
    isolation: float
    olympic: float
    plyometric: float


@dataclass(frozen=True)
class GoalProfile:
    """Configuration for a specific training goal.

    Attributes:
        name: Name of the goal (e.g., 'strength', 'hypertrophy')
        primary_dimensions: Primary scoring dimensions for this goal
        weight_modifiers: Weight modifiers for each dimension
        preferred_patterns: List of preferred movement patterns
        preferred_rep_range: Min and max rep range
        movement_preferences: Preferences for movement types
    """

    name: str
    primary_dimensions: tuple[str, ...]
    weight_modifiers: WeightModifiers
    preferred_patterns: tuple[str, ...]
    preferred_rep_range: tuple[int, int]
    movement_preferences: MovementPreferences


@dataclass(frozen=True)
class DisciplineModifier:
    """Configuration for discipline-specific scoring modifications.

    Attributes:
        name: Name of the discipline (e.g., 'olympic', 'plyometric')
        primary_dimensions: Primary scoring dimensions for this discipline
        weight_modifiers: Weight modifiers for each dimension
        preferred_patterns: List of preferred movement patterns
        movement_bonus: Dict mapping movement names to bonus multipliers
        movement_penalty: Dict mapping movement types to penalty multipliers
        technical_requirement: Technical difficulty requirement level
        recommended_experience_level: Recommended experience level
    """

    name: str
    primary_dimensions: tuple[str, ...]
    weight_modifiers: WeightModifiers
    preferred_patterns: tuple[str, ...]
    movement_bonus: dict[str, float]
    movement_penalty: dict[str, float]
    technical_requirement: str
    recommended_experience_level: str


@dataclass(frozen=True)
class RepSetRange:
    """Configuration for rep and set ranges for a block type.

    Attributes:
        block_type: Type of block (e.g., 'warmup', 'main_strength')
        sets_min: Minimum number of sets
        sets_max: Maximum number of sets
        sets_default: Default number of sets
        reps_min: Minimum number of reps
        reps_max: Maximum number of reps
        reps_default: Default number of reps
        intensity_pct: Intensity percentage range [min, max]
        rest_seconds: Rest time range in seconds [min, max]
        rpe_target: RPE target range [min, max]
        tempo: Tempo string (e.g., '3-0-2')
    """

    block_type: str
    sets_min: int
    sets_max: int
    sets_default: int
    reps_min: int
    reps_max: int
    reps_default: int
    intensity_pct: tuple[int, int]
    rest_seconds: tuple[int, int]
    rpe_target: tuple[int, int]
    tempo: str


@dataclass(frozen=True)
class CircuitConfig:
    """Configuration for circuit-specific settings.

    Attributes:
        exempt_from_ranges: Whether circuits are exempt from standard rep/set ranges
        sets_min: Minimum number of circuit sets
        sets_max: Maximum number of circuit sets
        sets_default: Default number of circuit sets
        reps_min: Minimum number of reps per station
        reps_max: Maximum number of reps per station
        reps_default: Default number of reps per station
        intensity_pct: Intensity percentage range
        rest_seconds: Rest time range
        rpe_target: RPE target range
        tempo: Tempo string
        circuit_types: List of circuit type options
    """

    exempt_from_ranges: bool
    sets_min: int
    sets_max: int
    sets_default: int
    reps_min: int
    reps_max: int
    reps_default: int
    intensity_pct: tuple[int, int]
    rest_seconds: tuple[int, int]
    rpe_target: tuple[int, int]
    tempo: str
    circuit_types: tuple[str, ...]


@dataclass(frozen=True)
class HardConstraints:
    """Hard constraint configurations for movement selection.

    Attributes:
        equipment_enforce: Whether equipment constraints are enforced
        variety_enforce: Whether variety constraints are enforced
        time_enforce: Whether time constraints are enforced
        user_rules_enforce: Whether user rule constraints are enforced
        safety_enforce: Whether safety constraints are enforced
        min_unique_movements_per_session: Minimum unique movements per session
        min_unique_movements_per_microcycle: Minimum unique movements per microcycle
        max_same_movement_per_microcycle: Max times same movement can appear in microcycle
        min_pattern_variety_per_session: Minimum pattern variety per session
        max_pattern_repeats_per_session: Maximum pattern repeats per session
        max_time_per_block_minutes: Maximum time per block
        max_time_per_session_minutes: Maximum time per session
        min_time_per_movement_minutes: Minimum time per movement
        recommended_time_per_movement_minutes: Recommended time per movement
    """

    equipment_enforce: bool
    variety_enforce: bool
    time_enforce: bool
    user_rules_enforce: bool
    safety_enforce: bool
    min_unique_movements_per_session: int
    min_unique_movements_per_microcycle: int
    max_same_movement_per_microcycle: int
    min_pattern_variety_per_session: int
    max_pattern_repeats_per_session: int
    max_time_per_block_minutes: int
    max_time_per_session_minutes: int
    min_time_per_movement_minutes: int
    recommended_time_per_movement_minutes: int


@dataclass(frozen=True)
class GlobalConfig:
    """Global configuration settings.

    Attributes:
        normalization_enabled: Whether score normalization is enabled
        normalization_method: Method for normalization
        tie_breaker_enabled: Whether tie-breaking is enabled
        tie_breaker_strategy: Strategy for tie-breaking
        relaxation_enabled: Whether constraint relaxation is enabled
        relaxation_strategy: Strategy for constraint relaxation
        debug_enabled: Whether debug logging is enabled
        cache_scores: Whether to cache scoring results
        validate_on_load: Whether to validate on config load
        strict_mode: Whether to throw exceptions on validation errors
    """

    normalization_enabled: bool
    normalization_method: str
    tie_breaker_enabled: bool
    tie_breaker_strategy: str
    relaxation_enabled: bool
    relaxation_strategy: str
    debug_enabled: bool
    cache_scores: bool
    validate_on_load: bool
    strict_mode: bool


@dataclass(frozen=True)
class ConfigMetadata:
    """Metadata about the configuration file.

    Attributes:
        version: Configuration version string
        last_updated: Date of last update
        author: Author of the configuration
        description: Description of the configuration
        schema_version: Schema version
    """

    version: str
    last_updated: str
    author: str
    description: str
    schema_version: str


@dataclass(frozen=True)
class MovementScoringConfig:
    """Complete movement scoring configuration.

    This is the main dataclass that contains all configuration data
    loaded from the YAML file.

    Attributes:
        scoring_dimensions: Dictionary of scoring dimension configurations
        pattern_compatibility_matrix: Pattern compatibility configuration
        goal_profiles: Dictionary of goal profile configurations
        discipline_modifiers: Dictionary of discipline modifier configurations
        hard_constraints: Hard constraint configuration
        rep_set_ranges: Dictionary of rep/set range configurations
        circuit_config: Circuit-specific configuration
        global_config: Global configuration settings
        metadata: Configuration metadata
    """

    scoring_dimensions: dict[str, ScoringDimension]
    pattern_compatibility_matrix: PatternCompatibilityMatrix
    goal_profiles: dict[str, GoalProfile]
    discipline_modifiers: dict[str, DisciplineModifier]
    hard_constraints: HardConstraints
    rep_set_ranges: dict[str, RepSetRange]
    circuit_config: CircuitConfig
    global_config: GlobalConfig
    metadata: ConfigMetadata


class YAMLConfigLoader:
    """Loads and validates YAML configuration files with hot-reload support.

    This class provides:
    - Loading of YAML configuration from file
    - Schema validation using dataclasses
    - Hot-reload support for configuration changes
    - Thread-safe configuration access
    - Type-safe configuration access through dataclasses

    Example:
        >>> loader = YAMLConfigLoader()
        >>> config = loader.load_config()
        >>> config.global_config.debug_enabled
        True
        >>> # Reload config when file changes
        >>> config = loader.reload_config()
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        enable_hot_reload: bool = True,
        hot_reload_interval_seconds: float = 5.0,
    ) -> None:
        """Initialize the YAML config loader.

        Args:
            config_path: Path to the YAML config file. Defaults to DEFAULT_CONFIG_PATH.
            enable_hot_reload: Whether to enable hot-reload functionality.
            hot_reload_interval_seconds: Interval in seconds to check for file changes.

        Raises:
            ConfigNotFoundError: If the config file doesn't exist.
        """
        self._config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._enable_hot_reload = enable_hot_reload
        self._hot_reload_interval = hot_reload_interval_seconds
        self._config: MovementScoringConfig | None = None
        self._last_modified: float = 0.0
        self._lock = threading.RLock()
        self._hot_reload_thread: threading.Thread | None = None
        self._hot_reload_stop_event = threading.Event()
        self._callbacks: list[callable[[MovementScoringConfig], None]] = []

        # Validate file exists on initialization
        if not self._config_path.exists():
            raise ConfigNotFoundError(
                f"Configuration file not found: {self._config_path}",
                path=str(self._config_path),
            )

        # Load initial configuration
        self.load_config()

        # Start hot-reload thread if enabled
        if self._enable_hot_reload:
            self._start_hot_reload()

    def load_config(self) -> MovementScoringConfig:
        """Load configuration from YAML file.

        Returns:
            MovementScoringConfig: The loaded and validated configuration.

        Raises:
            ConfigLoadError: If the file cannot be loaded.
            ConfigValidationError: If validation fails.
        """
        with self._lock:
            try:
                logger.info(f"Loading configuration from {self._config_path}")

                # Read YAML file
                raw_config = self._load_yaml_file()

                # Replace global variable references
                raw_config = self._resolve_global_variables(raw_config)

                # Validate and convert to dataclasses
                config = self._convert_to_dataclasses(raw_config)

                # Validate schema
                self.validate_schema(config)

                # Update internal state
                self._config = config
                self._last_modified = self._config_path.stat().st_mtime

                logger.info(
                    f"Configuration loaded successfully (version {config.metadata.version})"
                )

                return config

            except yaml.YAMLError as e:
                raise ConfigLoadError(
                    f"Failed to parse YAML file: {e}", path=str(self._config_path)
                ) from e
            except ConfigError:
                raise
            except Exception as e:
                raise ConfigLoadError(
                    f"Unexpected error loading config: {e}", path=str(self._config_path)
                ) from e

    def reload_config(self) -> MovementScoringConfig:
        """Reload configuration from file.

        This method checks if the file has been modified since the last load
        and reloads if necessary. If hot-reload is enabled, this is typically
        called automatically.

        Returns:
            MovementScoringConfig: The reloaded configuration.

        Raises:
            ConfigLoadError: If the file cannot be loaded.
            ConfigValidationError: If validation fails.
        """
        with self._lock:
            if not self._has_file_changed():
                logger.debug("Configuration file has not changed, skipping reload")
                return self._config  # type: ignore[return-value]

            logger.info("Reloading configuration due to file change")
            config = self.load_config()

            # Notify registered callbacks
            self._notify_callbacks(config)

            return config

    def validate_schema(self, config: MovementScoringConfig | None = None) -> None:
        """Validate the configuration schema.

        Args:
            config: Configuration to validate. If None, uses current config.

        Raises:
            ConfigValidationError: If validation fails.
        """
        config_to_validate = config if config is not None else self._config

        if config_to_validate is None:
            raise ConfigValidationError("No configuration loaded to validate")

        try:
            # Validate scoring dimensions
            self._validate_scoring_dimensions(config_to_validate.scoring_dimensions)

            # Validate pattern compatibility matrix
            self._validate_pattern_compatibility(
                config_to_validate.pattern_compatibility_matrix
            )

            # Validate goal profiles
            self._validate_goal_profiles(config_to_validate.goal_profiles)

            # Validate discipline modifiers
            self._validate_discipline_modifiers(config_to_validate.discipline_modifiers)

            # Validate hard constraints
            self._validate_hard_constraints(config_to_validate.hard_constraints)

            # Validate rep/set ranges
            self._validate_rep_set_ranges(config_to_validate.rep_set_ranges)

            # Validate circuit config
            self._validate_circuit_config(config_to_validate.circuit_config)

            # Validate global config
            self._validate_global_config(config_to_validate.global_config)

            # Validate metadata
            self._validate_metadata(config_to_validate.metadata)

            logger.debug("Configuration schema validation passed")

        except AssertionError as e:
            raise ConfigValidationError(
                f"Schema validation failed: {e}", path=str(self._config_path)
            ) from e

    def get_config(self) -> MovementScoringConfig:
        """Get the current configuration.

        Returns:
            MovementScoringConfig: The current configuration.

        Raises:
            ConfigLoadError: If no configuration has been loaded.
        """
        with self._lock:
            if self._config is None:
                raise ConfigLoadError("No configuration loaded")
            return self._config

    def register_reload_callback(self, callback: callable[[MovementScoringConfig], None]) -> None:
        """Register a callback to be invoked when config is reloaded.

        Args:
            callback: Function to call with new config on reload.
        """
        with self._lock:
            self._callbacks.append(callback)
            logger.debug(f"Registered reload callback: {callback.__name__}")

    def unregister_reload_callback(
        self, callback: callable[[MovementScoringConfig], None]
    ) -> None:
        """Unregister a reload callback.

        Args:
            callback: Callback function to remove.
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.debug(f"Unregistered reload callback: {callback.__name__}")

    def stop_hot_reload(self) -> None:
        """Stop the hot-reload thread.

        This should be called when shutting down the application.
        """
        if self._hot_reload_thread is not None:
            logger.info("Stopping hot-reload thread")
            self._hot_reload_stop_event.set()
            self._hot_reload_thread.join(timeout=5.0)
            self._hot_reload_thread = None

    def _load_yaml_file(self) -> dict[str, Any]:
        """Load and parse the YAML file.

        Returns:
            dict: Parsed YAML content.

        Raises:
            ConfigLoadError: If file cannot be read or parsed.
        """
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError as e:
            raise ConfigNotFoundError(
                f"Configuration file not found: {self._config_path}",
                path=str(self._config_path),
            ) from e
        except yaml.YAMLError as e:
            raise ConfigLoadError(
                f"Failed to parse YAML: {e}", path=str(self._config_path)
            ) from e
        except OSError as e:
            raise ConfigLoadError(
                f"Failed to read file: {e}", path=str(self._config_path)
            ) from e

    def _resolve_global_variables(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        """Replace global variable references with actual values.

        Args:
            raw_config: Raw configuration dict.

        Returns:
            dict: Configuration with resolved variables.
        """
        global_vars = {
            "DEFAULT_NORMALIZATION_ENABLED": DEFAULT_NORMALIZATION_ENABLED,
            "DEFAULT_TIEBREAKER_ENABLED": DEFAULT_TIEBREAKER_ENABLED,
            "DEFAULT_RELAXATION_ENABLED": DEFAULT_RELAXATION_ENABLED,
            "DEFAULT_DEBUG_ENABLED": DEFAULT_DEBUG_ENABLED,
        }

        def resolve_value(value: Any) -> Any:
            """Recursively resolve global variables in a value."""
            if isinstance(value, str):
                return global_vars.get(value, value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(v) for v in value]
            return value

        return resolve_value(raw_config)

    def _convert_to_dataclasses(self, raw_config: dict[str, Any]) -> MovementScoringConfig:
        """Convert raw dict to typed dataclasses.

        Args:
            raw_config: Raw configuration dict.

        Returns:
            MovementScoringConfig: Typed configuration object.
        """
        return MovementScoringConfig(
            scoring_dimensions=self._convert_scoring_dimensions(
                raw_config.get("scoring_dimensions", {})
            ),
            pattern_compatibility_matrix=self._convert_pattern_compatibility(
                raw_config.get("pattern_compatibility_matrix", {})
            ),
            goal_profiles=self._convert_goal_profiles(raw_config.get("goal_profiles", {})),
            discipline_modifiers=self._convert_discipline_modifiers(
                raw_config.get("discipline_modifiers", {})
            ),
            hard_constraints=self._convert_hard_constraints(
                raw_config.get("hard_constraints", {})
            ),
            rep_set_ranges=self._convert_rep_set_ranges(raw_config.get("rep_set_ranges", {})),
            circuit_config=self._convert_circuit_config(raw_config.get("rep_set_ranges", {})),
            global_config=self._convert_global_config(raw_config.get("global_config", {})),
            metadata=self._convert_metadata(raw_config.get("metadata", {})),
        )

    def _convert_scoring_dimensions(
        self, raw: dict[str, Any]
    ) -> dict[str, ScoringDimension]:
        """Convert scoring dimensions section."""
        dimensions = {}
        for name, config in raw.items():
            dimensions[name] = ScoringDimension(
                priority_level=config.get("priority_level", 0),
                weight=config.get("weight", 1.0),
                description=config.get("description", ""),
                penalty_mismatch=config.get("penalty_mismatch"),
                bonus_exact_match=config.get("bonus_exact_match"),
                bonus_unique_primary=config.get("bonus_unique_primary"),
                penalty_repeated_primary=config.get("penalty_repeated_primary"),
                bonus_matched_discipline=config.get("bonus_matched_discipline"),
                penalty_discipline_mismatch=config.get("penalty_discipline_mismatch"),
                neutral_default=config.get("neutral_default"),
                bonus_compound=config.get("bonus_compound"),
                neutral_hybrid=config.get("neutral_hybrid"),
                penalty_isolation=config.get("penalty_isolation"),
                bonus_target_muscle=config.get("bonus_target_muscle"),
                neutral_non_target=config.get("neutral_non_target"),
                specialization_threshold=config.get("specialization_threshold"),
                bonus_goal_match=config.get("bonus_goal_match"),
                neutral_goal_agnostic=config.get("neutral_goal_agnostic"),
                penalty_goal_conflict=config.get("penalty_goal_conflict"),
                bonus_efficient=config.get("bonus_efficient"),
                neutral_average=config.get("neutral_average"),
                penalty_inefficient=config.get("penalty_inefficient"),
                max_primary_repeats_per_session=config.get("max_primary_repeats_per_session"),
                max_primary_repeats_per_microcycle=config.get(
                    "max_primary_repeats_per_microcycle"
                ),
            )
        return dimensions

    def _convert_pattern_compatibility(
        self, raw: dict[str, Any]
    ) -> PatternCompatibilityMatrix:
        """Convert pattern compatibility matrix section."""
        substitution_groups = []
        for name, config in raw.get("substitution_groups", {}).items():
            substitution_groups.append(
                SubstitutionGroup(
                    name=name,
                    patterns=tuple(config.get("patterns", [])),
                    compatibility_matrix=config.get("compatibility_matrix", {}),
                )
            )

        return PatternCompatibilityMatrix(
            substitution_groups=tuple(substitution_groups),
            cross_substitution_allowed=raw.get("cross_substitution_allowed", False),
            min_substitution_score=raw.get("min_substitution_score", 0.6),
            exact_match_bonus=raw.get("exact_match_bonus", 1.0),
        )

    def _convert_weight_modifiers(self, raw: dict[str, float]) -> WeightModifiers:
        """Convert weight modifiers."""
        return WeightModifiers(
            compound_bonus=raw.get("compound_bonus", 1.0),
            pattern_alignment=raw.get("pattern_alignment", 1.0),
            muscle_coverage=raw.get("muscle_coverage", 1.0),
            discipline_preference=raw.get("discipline_preference", 1.0),
            goal_alignment=raw.get("goal_alignment", 1.0),
            time_utilization=raw.get("time_utilization", 1.0),
            specialization=raw.get("specialization", 1.0),
        )

    def _convert_movement_preferences(self, raw: dict[str, float]) -> MovementPreferences:
        """Convert movement preferences."""
        return MovementPreferences(
            compound=raw.get("compound", 1.0),
            isolation=raw.get("isolation", 1.0),
            olympic=raw.get("olympic", 1.0),
            plyometric=raw.get("plyometric", 1.0),
        )

    def _convert_goal_profiles(self, raw: dict[str, Any]) -> dict[str, GoalProfile]:
        """Convert goal profiles section."""
        profiles = {}
        for name, config in raw.items():
            profiles[name] = GoalProfile(
                name=name,
                primary_dimensions=tuple(config.get("primary_dimensions", [])),
                weight_modifiers=self._convert_weight_modifiers(
                    config.get("weight_modifiers", {})
                ),
                preferred_patterns=tuple(config.get("preferred_patterns", [])),
                preferred_rep_range=tuple(config.get("preferred_rep_range", [1, 10])),
                movement_preferences=self._convert_movement_preferences(
                    config.get("movement_preferences", {})
                ),
            )
        return profiles

    def _convert_discipline_modifiers(
        self, raw: dict[str, Any]
    ) -> dict[str, DisciplineModifier]:
        """Convert discipline modifiers section."""
        modifiers = {}
        for name, config in raw.items():
            modifiers[name] = DisciplineModifier(
                name=name,
                primary_dimensions=tuple(config.get("primary_dimensions", [])),
                weight_modifiers=self._convert_weight_modifiers(
                    config.get("weight_modifiers", {})
                ),
                preferred_patterns=tuple(config.get("preferred_patterns", [])),
                movement_bonus=config.get("movement_bonus", {}),
                movement_penalty=config.get("movement_penalty", {}),
                technical_requirement=config.get("technical_requirement", "medium"),
                recommended_experience_level=config.get(
                    "recommended_experience_level", "beginner"
                ),
            )
        return modifiers

    def _convert_hard_constraints(self, raw: dict[str, Any]) -> HardConstraints:
        """Convert hard constraints section."""
        equipment = raw.get("equipment", {})
        variety = raw.get("variety", {})
        time_config = raw.get("time", {})
        user_rules = raw.get("user_rules", {})
        safety = raw.get("safety", {})

        return HardConstraints(
            equipment_enforce=equipment.get("enforce", True),
            variety_enforce=variety.get("enforce", True),
            time_enforce=time_config.get("enforce", True),
            user_rules_enforce=user_rules.get("enforce", True),
            safety_enforce=safety.get("enforce", True),
            min_unique_movements_per_session=variety.get(
                "min_unique_movements_per_session", 4
            ),
            min_unique_movements_per_microcycle=variety.get(
                "min_unique_movements_per_microcycle", 12
            ),
            max_same_movement_per_microcycle=variety.get(
                "max_same_movement_per_microcycle", 3
            ),
            min_pattern_variety_per_session=variety.get(
                "min_pattern_variety_per_session", 2
            ),
            max_pattern_repeats_per_session=variety.get(
                "max_pattern_repeats_per_session", 3
            ),
            max_time_per_block_minutes=time_config.get("max_time_per_block_minutes", 45),
            max_time_per_session_minutes=time_config.get("max_time_per_session_minutes", 120),
            min_time_per_movement_minutes=time_config.get("min_time_per_movement_minutes", 2),
            recommended_time_per_movement_minutes=time_config.get(
                "recommended_time_per_movement_minutes", 5
            ),
        )

    def _convert_rep_set_ranges(self, raw: dict[str, Any]) -> dict[str, RepSetRange]:
        """Convert rep/set ranges section."""
        ranges = {}
        for block_type, config in raw.items():
            if block_type == "circuit":
                continue  # Skip circuit, handled separately

            sets_config = config.get("sets", {})
            reps_config = config.get("reps", {})

            ranges[block_type] = RepSetRange(
                block_type=block_type,
                sets_min=sets_config.get("min", 1),
                sets_max=sets_config.get("max", 4),
                sets_default=sets_config.get("default", 3),
                reps_min=reps_config.get("min", 5),
                reps_max=reps_config.get("max", 15),
                reps_default=reps_config.get("default", 10),
                intensity_pct=tuple(config.get("intensity_pct", [60, 80])),
                rest_seconds=tuple(config.get("rest_seconds", [60, 120])),
                rpe_target=tuple(config.get("rpe_target", [5, 8])),
                tempo=config.get("tempo", "3-0-2"),
            )
        return ranges

    def _convert_circuit_config(self, raw: dict[str, Any]) -> CircuitConfig:
        """Convert circuit-specific configuration."""
        circuit_config = raw.get("circuit", {})
        sets_config = circuit_config.get("sets", {})
        reps_config = circuit_config.get("reps", {})

        return CircuitConfig(
            exempt_from_ranges=circuit_config.get("exempt_from_ranges", True),
            sets_min=sets_config.get("min", 1),
            sets_max=sets_config.get("max", 6),
            sets_default=sets_config.get("default", 3),
            reps_min=reps_config.get("min", 5),
            reps_max=reps_config.get("max", 20),
            reps_default=reps_config.get("default", 10),
            intensity_pct=tuple(circuit_config.get("intensity_pct", [40, 70])),
            rest_seconds=tuple(circuit_config.get("rest_seconds", [0, 60])),
            rpe_target=tuple(circuit_config.get("rpe_target", [5, 8])),
            tempo=circuit_config.get("tempo", "2-0-2"),
            circuit_types=tuple(circuit_config.get("circuit_types", [])),
        )

    def _convert_global_config(self, raw: dict[str, Any]) -> GlobalConfig:
        """Convert global configuration section."""
        normalization = raw.get("normalization", {})
        tie_breaker = raw.get("tie_breaker", {})
        relaxation = raw.get("relaxation", {})
        debug = raw.get("debug", {})
        performance = raw.get("performance", {})
        validation = raw.get("validation", {})

        return GlobalConfig(
            normalization_enabled=normalization.get("enabled", True),
            normalization_method=normalization.get("method", "min_max"),
            tie_breaker_enabled=tie_breaker.get("enabled", True),
            tie_breaker_strategy=tie_breaker.get("strategy", "priority_hierarchy"),
            relaxation_enabled=relaxation.get("enabled", True),
            relaxation_strategy=relaxation.get("strategy", "soft_constraints"),
            debug_enabled=debug.get("enabled", False),
            cache_scores=performance.get("cache_scores", True),
            validate_on_load=validation.get("validate_on_load", True),
            strict_mode=validation.get("strict_mode", False),
        )

    def _convert_metadata(self, raw: dict[str, Any]) -> ConfigMetadata:
        """Convert metadata section."""
        return ConfigMetadata(
            version=raw.get("version", "1.0.0"),
            last_updated=raw.get("last_updated", ""),
            author=raw.get("author", ""),
            description=raw.get("description", ""),
            schema_version=raw.get("schema_version", "1.0"),
        )

    # Validation methods

    def _validate_scoring_dimensions(
        self, dimensions: dict[str, ScoringDimension]
    ) -> None:
        """Validate scoring dimensions configuration."""
        assert len(dimensions) > 0, "At least one scoring dimension must be defined"

        for name, dimension in dimensions.items():
            assert (
                1 <= dimension.priority_level <= 7
            ), f"Invalid priority_level for {name}: {dimension.priority_level}"
            assert (
                0.0 <= dimension.weight <= 2.0
            ), f"Invalid weight for {name}: {dimension.weight}"
            assert len(dimension.description) > 0, f"Description required for {name}"

    def _validate_pattern_compatibility(
        self, matrix: PatternCompatibilityMatrix
    ) -> None:
        """Validate pattern compatibility matrix configuration."""
        assert (
            len(matrix.substitution_groups) > 0
        ), "At least one substitution group must be defined"
        assert (
            0.0 <= matrix.min_substitution_score <= 1.0
        ), f"Invalid min_substitution_score: {matrix.min_substitution_score}"
        assert (
            0.0 <= matrix.exact_match_bonus <= 2.0
        ), f"Invalid exact_match_bonus: {matrix.exact_match_bonus}"

    def _validate_goal_profiles(self, profiles: dict[str, GoalProfile]) -> None:
        """Validate goal profiles configuration."""
        assert len(profiles) > 0, "At least one goal profile must be defined"

        valid_goals = {
            "strength",
            "hypertrophy",
            "endurance",
            "fat_loss",
            "explosiveness",
            "speed",
            "calisthenics",
        }
        for name in profiles:
            assert name in valid_goals, f"Invalid goal profile name: {name}"

        for profile in profiles.values():
            assert len(profile.primary_dimensions) > 0, f"Primary dimensions required for {profile.name}"
            assert (
                len(profile.preferred_patterns) > 0
            ), f"Preferred patterns required for {profile.name}"
            assert (
                profile.preferred_rep_range[0] < profile.preferred_rep_range[1]
            ), f"Invalid rep range for {profile.name}"

    def _validate_discipline_modifiers(
        self, modifiers: dict[str, DisciplineModifier]
    ) -> None:
        """Validate discipline modifiers configuration."""
        valid_disciplines = {"olympic", "plyometric", "calisthenics"}
        for name in modifiers:
            assert name in valid_disciplines, f"Invalid discipline modifier name: {name}"

    def _validate_hard_constraints(self, constraints: HardConstraints) -> None:
        """Validate hard constraints configuration."""
        assert (
            constraints.min_unique_movements_per_session >= 1
        ), "min_unique_movements_per_session must be >= 1"
        assert (
            constraints.min_unique_movements_per_microcycle >= 1
        ), "min_unique_movements_per_microcycle must be >= 1"
        assert (
            constraints.max_time_per_session_minutes > constraints.max_time_per_block_minutes
        ), "max_time_per_session must be > max_time_per_block"

    def _validate_rep_set_ranges(self, ranges: dict[str, RepSetRange]) -> None:
        """Validate rep/set ranges configuration."""
        assert len(ranges) > 0, "At least one rep/set range must be defined"

        for range_config in ranges.values():
            assert (
                range_config.sets_min <= range_config.sets_max
            ), f"Invalid set range for {range_config.block_type}"
            assert (
                range_config.sets_min <= range_config.sets_default <= range_config.sets_max
            ), f"Default sets out of range for {range_config.block_type}"
            assert (
                range_config.reps_min <= range_config.reps_max
            ), f"Invalid rep range for {range_config.block_type}"
            assert (
                range_config.reps_min <= range_config.reps_default <= range_config.reps_max
            ), f"Default reps out of range for {range_config.block_type}"
            assert (
                range_config.intensity_pct[0] < range_config.intensity_pct[1]
            ), f"Invalid intensity range for {range_config.block_type}"

    def _validate_circuit_config(self, config: CircuitConfig) -> None:
        """Validate circuit configuration."""
        assert (
            config.sets_min <= config.sets_max
        ), f"Invalid circuit set range: {config.sets_min}-{config.sets_max}"
        assert (
            config.reps_min <= config.reps_max
        ), f"Invalid circuit rep range: {config.reps_min}-{config.reps_max}"
        assert len(config.circuit_types) > 0, "At least one circuit type must be defined"

    def _validate_global_config(self, config: GlobalConfig) -> None:
        """Validate global configuration."""
        valid_normalization_methods = {"min_max", "z_score", "rank"}
        assert (
            config.normalization_method in valid_normalization_methods
        ), f"Invalid normalization method: {config.normalization_method}"

        valid_tie_breaker_strategies = {
            "priority_hierarchy",
            "random",
            "lexicographic",
        }
        assert (
            config.tie_breaker_strategy in valid_tie_breaker_strategies
        ), f"Invalid tie_breaker strategy: {config.tie_breaker_strategy}"

        valid_relaxation_strategies = {"soft_constraints", "penalty_based", "iterative"}
        assert (
            config.relaxation_strategy in valid_relaxation_strategies
        ), f"Invalid relaxation strategy: {config.relaxation_strategy}"

    def _validate_metadata(self, metadata: ConfigMetadata) -> None:
        """Validate metadata configuration."""
        assert len(metadata.version) > 0, "Version must be specified"
        assert len(metadata.author) > 0, "Author must be specified"

    # Hot-reload methods

    def _has_file_changed(self) -> bool:
        """Check if the configuration file has been modified."""
        try:
            current_mtime = self._config_path.stat().st_mtime
            return current_mtime > self._last_modified
        except OSError:
            logger.warning(f"Failed to check file modification time for {self._config_path}")
            return False

    def _start_hot_reload(self) -> None:
        """Start the hot-reload thread."""
        if self._hot_reload_thread is not None:
            return

        logger.info("Starting hot-reload thread")

        def hot_reload_worker() -> None:
            """Worker function for hot-reload thread."""
            while not self._hot_reload_stop_event.is_set():
                try:
                    if self._has_file_changed():
                        logger.info("Detected configuration file change, reloading...")
                        self.reload_config()
                except Exception as e:
                    logger.error(f"Error during hot-reload: {e}", exc_info=True)

                self._hot_reload_stop_event.wait(self._hot_reload_interval)

        self._hot_reload_thread = threading.Thread(
            target=hot_reload_worker, name="ConfigHotReload", daemon=True
        )
        self._hot_reload_thread.start()

    def _notify_callbacks(self, config: MovementScoringConfig) -> None:
        """Notify all registered callbacks of config reload."""
        for callback in self._callbacks:
            try:
                callback(config)
            except Exception as e:
                logger.error(
                    f"Error in reload callback {callback.__name__}: {e}", exc_info=True
                )


# Singleton instance for easy access
_default_loader: YAMLConfigLoader | None = None


def get_config_loader(
    config_path: Path | str | None = None,
    enable_hot_reload: bool = True,
) -> YAMLConfigLoader:
    """Get or create the default config loader singleton.

    Args:
        config_path: Path to config file. Only used on first call.
        enable_hot_reload: Whether to enable hot-reload. Only used on first call.

    Returns:
        YAMLConfigLoader: The config loader instance.
    """
    global _default_loader
    if _default_loader is None:
        _default_loader = YAMLConfigLoader(
            config_path=config_path, enable_hot_reload=enable_hot_reload
        )
    return _default_loader


def get_config() -> MovementScoringConfig:
    """Get the current configuration from the default loader.

    Returns:
        MovementScoringConfig: The current configuration.

    Raises:
        ConfigLoadError: If no configuration has been loaded.
    """
    return get_config_loader().get_config()
