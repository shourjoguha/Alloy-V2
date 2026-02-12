"""
Unified Optimization Configuration Loader

This module provides a centralized, type-safe configuration loader for optimization
settings, consolidating data from multiple sources into a single system.

Configuration is loaded from optimization_config.yaml and validated with Pydantic.
Supports hot-reloading for production updates without restart.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable

import yaml

if TYPE_CHECKING:
    pass


class OptimizationConfigLoadError(Exception):
    """Raised when configuration cannot be loaded or is invalid."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class OptimizationConfigValidationError(OptimizationConfigLoadError):
    """Raised when configuration fails validation."""


@dataclass(frozen=True)
class ORToolsConfig:
    """OR-Tools CP-SAT solver configuration."""

    min_sets_per_movement: int = 2
    max_sets_per_movement: int = 5
    volume_target_reduction_pct: float = 0.2
    timeout_seconds: int = 60

    def __post_init__(self):
        if not 0 < self.min_sets_per_movement <= self.max_sets_per_movement:
            raise OptimizationConfigValidationError(
                f"min_sets_per_movement ({self.min_sets_per_movement}) must be <= max_sets_per_movement ({self.max_sets_per_movement})"
            )
        if not 0 <= self.volume_target_reduction_pct <= 1:
            raise OptimizationConfigValidationError(
                f"volume_target_reduction_pct ({self.volume_target_reduction_pct}) must be between 0 and 1"
            )


@dataclass(frozen=True)
class OptimizationConstants:
    """Core optimization constants."""

    seconds_per_minute: int = 60
    seconds_per_set: int = 4
    synergist_set_multiplier: float = 0.5

    base_score_multiplier: int = 1000
    circuit_stimulus_multiplier: int = 100
    cardio_score_multiplier: int = 10

    neutral_base_score: float = 0.5
    discipline_preference_bonus: float = 0.2
    compound_bonus: float = 0.1

    dimension_score_weight: float = 0.2

    min_qualified_score: float = 0.5
    score_min_bound: float = 0.0
    score_max_bound: float = 1.0

    discipline_weight_relaxation_multiplier: float = 0.7

    def __post_init__(self):
        if not 0 <= self.min_qualified_score <= 1:
            raise OptimizationConfigValidationError(
                f"min_qualified_score ({self.min_qualified_score}) must be between 0 and 1"
            )


@dataclass(frozen=True)
class EmergencyModeConfig:
    """Emergency mode configuration."""

    volume_multiplier: float = 0.5
    fatigue_multiplier: float = 1.5
    duration_multiplier: float = 1.25

    def __post_init__(self):
        if not 0 < self.volume_multiplier <= 1:
            raise OptimizationConfigValidationError(
                f"volume_multiplier ({self.volume_multiplier}) must be between 0 and 1"
            )
        if self.fatigue_multiplier < 1:
            raise OptimizationConfigValidationError(
                f"fatigue_multiplier ({self.fatigue_multiplier}) must be >= 1"
            )
        if self.duration_multiplier < 1:
            raise OptimizationConfigValidationError(
                f"duration_multiplier ({self.duration_multiplier}) must be >= 1"
            )


@dataclass(frozen=True)
class RelaxationStepConfig:
    """Configuration for a single relaxation step."""

    step: int
    name: str
    description: str
    pattern_compatibility_expansion: bool = False
    include_synergist_muscles: bool = False
    discipline_weight_multiplier: float = 1.0
    allow_isolation_movements: bool = False
    allow_generic_movements: bool = False
    emergency_mode: bool = False


@dataclass(frozen=True)
class ProgressiveRelaxationConfig:
    """Progressive relaxation strategy configuration."""

    enabled: bool = True
    max_relaxation_steps: int = 6
    steps: list[RelaxationStepConfig] | None = None

    def __post_init__(self):
        if self.max_relaxation_steps < 0:
            raise OptimizationConfigValidationError(
                f"max_relaxation_steps ({self.max_relaxation_steps}) must be >= 0"
            )
        if self.steps is not None:
            for step in self.steps:
                if step.step > self.max_relaxation_steps:
                    raise OptimizationConfigValidationError(
                        f"Relaxation step {step.step} exceeds max_relaxation_steps {self.max_relaxation_steps}"
                    )


@dataclass(frozen=True)
class MicrocycleProgressionConfig:
    """Microcycle phase-specific RPE configuration."""

    accumulation: list[float] | None = None
    intensification: list[float] | None = None
    peaking: list[float] | None = None
    deload: list[float] | None = None
    volume_phase: list[float] | None = None
    intensity_phase: list[float] | None = None
    fatigue_mgmt: list[float] | None = None
    daily_undulating: bool = False
    wave_loading: bool = False


@dataclass(frozen=True)
class ProgramTypeRPEProfile:
    """RPE profile for a specific program type."""

    primary_compound_rpe: list[float]
    accessory_rpe: list[float]
    weekly_high_rpe_sets_max: int
    microcycle_progression: MicrocycleProgressionConfig

    def __post_init__(self):
        if len(self.primary_compound_rpe) != 2:
            raise OptimizationConfigValidationError(
                f"primary_compound_rpe must be [min, max], got {self.primary_compound_rpe}"
            )
        if len(self.accessory_rpe) != 2:
            raise OptimizationConfigValidationError(
                f"accessory_rpe must be [min, max], got {self.accessory_rpe}"
            )
        if not 0 < self.weekly_high_rpe_sets_max:
            raise OptimizationConfigValidationError(
                f"weekly_high_rpe_sets_max must be > 0, got {self.weekly_high_rpe_sets_max}"
            )


@dataclass(frozen=True)
class CNSDisciplineAdjustmentsConfig:
    """RPE adjustments for CNS-intensive movements."""

    rpe_cap: float
    weekly_limit: int

    def __post_init__(self):
        if not 1 <= self.rpe_cap <= 10:
            raise OptimizationConfigValidationError(
                f"rpe_cap must be between 1 and 10, got {self.rpe_cap}"
            )
        if self.weekly_limit < 0:
            raise OptimizationConfigValidationError(
                f"weekly_limit must be >= 0, got {self.weekly_limit}"
            )


@dataclass(frozen=True)
class FatigueAdjustmentsConfig:
    """RPE reductions based on fatigue signals."""

    sleep_under_6h: float
    sleep_under_5h: float
    hrv_below_baseline_20pct: float
    soreness_above_7: float
    consecutive_high_rpe_days: float

    def __post_init__(self):
        for field_name, value in [
            ("sleep_under_6h", self.sleep_under_6h),
            ("sleep_under_5h", self.sleep_under_5h),
            ("hrv_below_baseline_20pct", self.hrv_below_baseline_20pct),
            ("soreness_above_7", self.soreness_above_7),
            ("consecutive_high_rpe_days", self.consecutive_high_rpe_days),
        ]:
            if value > 0:
                raise OptimizationConfigValidationError(
                    f"{field_name} must be <= 0 (reduction), got {value}"
                )


@dataclass(frozen=True)
class RecoveryHoursByRPEConfig:
    """Recovery hours required for different RPE levels."""

    rpe_6_7: int
    rpe_8: int
    rpe_9: int
    rpe_10: int

    def __post_init__(self):
        if self.rpe_6_7 <= 0 or self.rpe_8 <= 0 or self.rpe_9 <= 0 or self.rpe_10 <= 0:
            raise OptimizationConfigValidationError(
                "All recovery hours must be > 0"
            )


@dataclass(frozen=True)
class RPESuggestionConfig:
    """RPE suggestion configuration."""

    warmup_rpe: list[float]
    main_strength_rpe: list[float]
    main_hypertrophy_rpe: list[float]
    accessory_rpe: list[float]
    cooldown_rpe: list[float]
    circuit_rpe: list[float]
    program_type_profiles: dict[str, ProgramTypeRPEProfile]
    cns_discipline_adjustments: dict[str, CNSDisciplineAdjustmentsConfig]
    fatigue_adjustments: FatigueAdjustmentsConfig
    recovery_hours_by_rpe: RecoveryHoursByRPEConfig

    def __post_init__(self):
        for field_name, value in [
            ("warmup_rpe", self.warmup_rpe),
            ("main_strength_rpe", self.main_strength_rpe),
            ("main_hypertrophy_rpe", self.main_hypertrophy_rpe),
            ("accessory_rpe", self.accessory_rpe),
            ("cooldown_rpe", self.cooldown_rpe),
            ("circuit_rpe", self.circuit_rpe),
        ]:
            if len(value) != 2:
                raise OptimizationConfigValidationError(
                    f"{field_name} must be [min, max], got {value}"
                )


@dataclass(frozen=True)
class OptimizationConfig:
    """Unified optimization configuration."""

    version: str
    last_updated: str
    or_tools: ORToolsConfig
    constants: OptimizationConstants
    emergency_mode: EmergencyModeConfig
    progressive_relaxation: ProgressiveRelaxationConfig
    rpe_suggestion: RPESuggestionConfig

    def get_relaxation_step(self, step: int) -> RelaxationStepConfig:
        """Get configuration for a specific relaxation step.

        Args:
            step: Relaxation step number (0 to max_relaxation_steps)

        Returns:
            RelaxationStepConfig for the requested step.

        Raises:
            ValueError: If step is out of range.
        """
        if self.progressive_relaxation.steps is None:
            raise ValueError("No relaxation steps defined")

        for s in self.progressive_relaxation.steps:
            if s.step == step:
                return s

        raise ValueError(f"Relaxation step {step} not found")


class OptimizationConfigLoader:
    """Loader for unified optimization configuration with hot-reload support."""

    _instance: OptimizationConfigLoader | None = None
    _lock = RLock()

    def __new__(cls, config_path: Path | None = None, enable_hot_reload: bool = False):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(
        self,
        config_path: Path | None = None,
        enable_hot_reload: bool = False,
    ):
        if hasattr(self, "_initialized"):
            return

        self._lock = RLock()
        self._config: OptimizationConfig | None = None
        self._config_path = config_path or self._default_config_path()
        self._enable_hot_reload = enable_hot_reload
        self._reload_callbacks: list[Callable[[OptimizationConfig], None]] = []
        self._reload_count = 0
        self._initialized = True

        self._load_config()

    @staticmethod
    def _default_config_path() -> Path:
        """Get default configuration file path."""
        return Path(__file__).parent / "optimization_config.yaml"

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self._config_path, "r") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            raise OptimizationConfigLoadError(
                f"Configuration file not found: {self._config_path}"
            )
        except yaml.YAMLError as e:
            raise OptimizationConfigLoadError(
                f"Failed to parse YAML configuration: {e}",
                details={"file_path": str(self._config_path)},
            )

        try:
            self._config = self._parse_config(data)
            self._reload_count += 1
            self._notify_callbacks()
        except OptimizationConfigValidationError:
            raise
        except Exception as e:
            raise OptimizationConfigLoadError(
                f"Failed to parse configuration: {e}",
                details={"file_path": str(self._config_path)},
            )

    def _parse_config(self, data: dict[str, Any]) -> OptimizationConfig:
        """Parse raw YAML data into OptimizationConfig.

        Args:
            data: Raw YAML data as dictionary.

        Returns:
            Parsed OptimizationConfig.

        Raises:
            OptimizationConfigValidationError: If validation fails.
        """
        or_tools_data = data.get("or_tools", {})
        or_tools_config = ORToolsConfig(**or_tools_data)

        constants_data = data.get("constants", {})
        constants_config = OptimizationConstants(**constants_data)

        emergency_data = data.get("emergency_mode", {})
        emergency_config = EmergencyModeConfig(**emergency_data)

        relaxation_data = data.get("progressive_relaxation", {})
        steps_data = relaxation_data.get("steps", [])
        steps = [RelaxationStepConfig(**step_data) for step_data in steps_data]
        relaxation_config = ProgressiveRelaxationConfig(
            enabled=relaxation_data.get("enabled", True),
            max_relaxation_steps=relaxation_data.get("max_relaxation_steps", 6),
            steps=steps if steps else None,
        )

        rpe_suggestion_data = data.get("rpe_suggestion", {})
        rpe_suggestion_config = self._parse_rpe_suggestion_config(rpe_suggestion_data)

        return OptimizationConfig(
            version=data.get("version", "1.0.0"),
            last_updated=data.get("last_updated", ""),
            or_tools=or_tools_config,
            constants=constants_config,
            emergency_mode=emergency_config,
            progressive_relaxation=relaxation_config,
            rpe_suggestion=rpe_suggestion_config,
        )

    def _parse_rpe_suggestion_config(
        self, data: dict[str, Any]
    ) -> RPESuggestionConfig:
        """Parse RPE suggestion configuration section.

        Args:
            data: RPE suggestion data from YAML.

        Returns:
            Parsed RPESuggestionConfig.
        """
        warmup_rpe = data.get("warmup_rpe", [1, 3])
        main_strength_rpe = data.get("main_strength_rpe", [7, 9])
        main_hypertrophy_rpe = data.get("main_hypertrophy_rpe", [6, 8])
        accessory_rpe = data.get("accessory_rpe", [5, 7])
        cooldown_rpe = data.get("cooldown_rpe", [1, 3])
        circuit_rpe = data.get("circuit_rpe", [5, 8])

        program_profiles_data = data.get("program_type_profiles", {})
        program_type_profiles = {}
        for profile_name, profile_data in program_profiles_data.items():
            progression_data = profile_data.get("microcycle_progression", {})
            microcycle_progression = MicrocycleProgressionConfig(
                accumulation=progression_data.get("accumulation"),
                intensification=progression_data.get("intensification"),
                peaking=progression_data.get("peaking"),
                deload=progression_data.get("deload"),
                volume_phase=progression_data.get("volume_phase"),
                intensity_phase=progression_data.get("intensity_phase"),
                fatigue_mgmt=progression_data.get("fatigue_mgmt"),
                daily_undulating=progression_data.get("daily_undulating", False),
                wave_loading=progression_data.get("wave_loading", False),
            )
            program_type_profiles[profile_name] = ProgramTypeRPEProfile(
                primary_compound_rpe=profile_data.get("primary_compound_rpe", [6.5, 8.5]),
                accessory_rpe=profile_data.get("accessory_rpe", [6, 7.5]),
                weekly_high_rpe_sets_max=profile_data.get("weekly_high_rpe_sets_max", 12),
                microcycle_progression=microcycle_progression,
            )

        cns_data = data.get("cns_discipline_adjustments", {})
        cns_discipline_adjustments = {}
        for adj_name, adj_data in cns_data.items():
            cns_discipline_adjustments[adj_name] = CNSDisciplineAdjustmentsConfig(**adj_data)

        fatigue_data = data.get("fatigue_adjustments", {})
        fatigue_adjustments = FatigueAdjustmentsConfig(
            sleep_under_6h=fatigue_data.get("sleep_under_6h", -0.5),
            sleep_under_5h=fatigue_data.get("sleep_under_5h", -1.0),
            hrv_below_baseline_20pct=fatigue_data.get("hrv_below_baseline_20pct", -1.0),
            soreness_above_7=fatigue_data.get("soreness_above_7", -1.0),
            consecutive_high_rpe_days=fatigue_data.get("consecutive_high_rpe_days", -0.5),
        )

        recovery_data = data.get("recovery_hours_by_rpe", {})
        recovery_hours_by_rpe = RecoveryHoursByRPEConfig(
            rpe_6_7=recovery_data.get("rpe_6_7", 24),
            rpe_8=recovery_data.get("rpe_8", 48),
            rpe_9=recovery_data.get("rpe_9", 72),
            rpe_10=recovery_data.get("rpe_10", 96),
        )

        return RPESuggestionConfig(
            warmup_rpe=warmup_rpe,
            main_strength_rpe=main_strength_rpe,
            main_hypertrophy_rpe=main_hypertrophy_rpe,
            accessory_rpe=accessory_rpe,
            cooldown_rpe=cooldown_rpe,
            circuit_rpe=circuit_rpe,
            program_type_profiles=program_type_profiles,
            cns_discipline_adjustments=cns_discipline_adjustments,
            fatigue_adjustments=fatigue_adjustments,
            recovery_hours_by_rpe=recovery_hours_by_rpe,
        )

    @property
    def config(self) -> OptimizationConfig:
        """Get current configuration (thread-safe).

        Returns:
            Current OptimizationConfig instance.
        """
        with self._lock:
            if self._config is None:
                self._load_config()
            return self._config

    def reload(self) -> None:
        """Force reload configuration from file."""
        with self._lock:
            self._load_config()

    def register_reload_callback(
        self, callback: Callable[[OptimizationConfig], None]
    ) -> None:
        """Register a callback to be called on configuration reload.

        Args:
            callback: Function to call with new configuration on reload.
        """
        self._reload_callbacks.append(callback)

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks of configuration reload."""
        if self._config is None:
            return
        for callback in self._reload_callbacks:
            try:
                callback(self._config)
            except Exception:
                pass

    @property
    def reload_count(self) -> int:
        """Get number of times configuration has been reloaded."""
        return self._reload_count


_loader_instance: OptimizationConfigLoader | None = None


def get_optimization_config_loader(
    config_path: Path | None = None,
    enable_hot_reload: bool = False,
) -> OptimizationConfigLoader:
    """Get or create the singleton OptimizationConfigLoader instance.

    Args:
        config_path: Optional custom path to configuration file.
        enable_hot_reload: Enable hot-reload support.

    Returns:
        OptimizationConfigLoader singleton instance.

    Example:
        >>> loader = get_optimization_config_loader()
        >>> config = loader.config
        >>> timeout = config.or_tools.timeout_seconds
    """
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = OptimizationConfigLoader(config_path, enable_hot_reload)
    return _loader_instance


def get_optimization_config() -> OptimizationConfig:
    """Get current optimization configuration.

    Returns:
        Current OptimizationConfig instance.

    Example:
        >>> from app.config.optimization_config_loader import get_optimization_config
        >>> config = get_optimization_config()
        >>> timeout = config.or_tools.timeout_seconds
    """
    return get_optimization_config_loader().config


def reload_optimization_config() -> None:
    """Force reload optimization configuration from file.

    Example:
        >>> from app.config.optimization_config_loader import reload_optimization_config
        >>> reload_optimization_config()
    """
    get_optimization_config_loader().reload()
