"""
Simple tests for the optimization config loader.

Run with: python -m pytest app/config/test_optimization_config_loader.py -v
"""

import pytest
from pathlib import Path
from datetime import datetime

from app.config.optimization_config_loader import (
    # Models
    Metadata,
    ORToolsConfig,
    DiversityOptimizerConfig,
    OptimizationConfig,
    RepSetRange,
    CircuitConfig,
    GlobalConfig,
    HardConstraints,
    RepSetRanges,
    NormalizationConfig,
    TiebreakerConfig,
    RelaxationConfig,
    TimeConstraints,
    VarietyConstraints,
    UserRules,
    SafetyConstraints,
    # Enums
    SolverStrategy,
    ScoringMethod,
    NormalizationMethod,
    TiebreakerStrategy,
    RelaxationStrategy,
    CircuitType,
    # Exceptions
    OptimizationConfigError,
    OptimizationConfigValidationError,
    OptimizationConfigLoadError,
    OptimizationConfigNotFoundError,
    # Loader
    OptimizationConfigLoader,
    # Backward compatibility
    LegacyConfigAdapter,
    # Constants
    DEFAULT_OPTIMIZATION_CONFIG_PATH,
)


# ============================================================================
# Model Tests
# ============================================================================


def test_metadata_validation():
    """Test metadata validation."""
    # Valid metadata
    metadata = Metadata(
        version="1.0.0",
        author="Test Author",
        description="Test config",
        last_updated=datetime.now(),
    )
    assert metadata.version == "1.0.0"

    # Invalid version format
    with pytest.raises(OptimizationConfigValidationError):
        Metadata(
            version="invalid",
            author="Test",
            description="Test",
        )


def test_or_tools_config():
    """Test OR-Tools configuration model."""
    config = ORToolsConfig(
        enabled=True,
        timeout_seconds=60,
        max_fatigue=8.0,
        min_sets_per_movement=2,
        max_sets_per_movement=5,
    )
    assert config.enabled is True
    assert config.timeout_seconds == 60

    # Invalid: min_sets > max_sets
    with pytest.raises(OptimizationConfigValidationError):
        ORToolsConfig(
            enabled=True,
            min_sets_per_movement=5,
            max_sets_per_movement=2,
        )


def test_rep_set_range():
    """Test rep/set range model."""
    range_config = RepSetRange(
        sets_min=1,
        sets_max=3,
        sets_default=2,
        reps_min=5,
        reps_max=15,
        reps_default=10,
    )
    assert range_config.sets_min == 1
    assert range_config.sets_max == 3
    assert range_config.sets_default == 2

    # Invalid: default out of range
    with pytest.raises(OptimizationConfigValidationError):
        RepSetRange(
            sets_min=1,
            sets_max=3,
            sets_default=5,  # Out of range
            reps_min=5,
            reps_max=15,
            reps_default=10,
        )


def test_circuit_config():
    """Test circuit configuration model."""
    config = CircuitConfig(
        allowed_circuit_types=[CircuitType.AMRAP, CircuitType.EMOM],
        default_rounds=3,
        max_rounds=10,
    )
    assert len(config.allowed_circuit_types) == 2
    assert config.default_rounds == 3


def test_global_config():
    """Test global configuration model."""
    config = GlobalConfig(
        normalization=NormalizationConfig(enabled=True, method=NormalizationMethod.MIN_MAX),
        tiebreaker=TiebreakerConfig(enabled=True, strategy=TiebreakerStrategy.PRIORITY_HIERARCHY),
        relaxation=RelaxationConfig(enabled=True, strategy=RelaxationStrategy.SOFT_CONSTRAINTS),
    )
    assert config.normalization.enabled is True
    assert config.tiebreaker.strategy == TiebreakerStrategy.PRIORITY_HIERARCHY


def test_complete_config():
    """Test creating a complete optimization configuration."""
    config = OptimizationConfig(
        metadata=Metadata(
            version="1.0.0",
            author="Test",
            description="Test config",
        ),
        or_tools=ORToolsConfig(enabled=True),
        diversity_optimizer=DiversityOptimizerConfig(enabled=False),
        hard_constraints=HardConstraints(
            time=TimeConstraints(enforce=True),
            variety=VarietyConstraints(enforce=True),
            user_rules=UserRules(enforce=True),
            safety=SafetyConstraints(enforce=True),
        ),
        rep_set_ranges=RepSetRanges(),
        circuit_config=CircuitConfig(),
        global_config=GlobalConfig(),
    )
    assert config.metadata.version == "1.0.0"
    assert config.or_tools.enabled is True
    assert config.diversity_optimizer.enabled is False

    # Invalid: both solvers disabled
    with pytest.raises(OptimizationConfigValidationError):
        OptimizationConfig(
            metadata=Metadata(
                version="1.0.0",
                author="Test",
                description="Test config",
            ),
            or_tools=ORToolsConfig(enabled=False),
            diversity_optimizer=DiversityOptimizerConfig(enabled=False),
            hard_constraints=HardConstraints(),
            rep_set_ranges=RepSetRanges(),
            circuit_config=CircuitConfig(),
            global_config=GlobalConfig(),
        )


# ============================================================================
# Loader Tests
# ============================================================================


def test_loader_with_default_config():
    """Test loading configuration from default file."""
    if not DEFAULT_OPTIMIZATION_CONFIG_PATH.exists():
        pytest.skip(f"Default config file not found: {DEFAULT_OPTIMIZATION_CONFIG_PATH}")

    loader = OptimizationConfigLoader(
        config_path=DEFAULT_OPTIMIZATION_CONFIG_PATH,
        enable_hot_reload=False,
    )

    config = loader.get_config()
    assert isinstance(config, OptimizationConfig)
    assert isinstance(config.metadata, Metadata)
    assert isinstance(config.or_tools, ORToolsConfig)
    assert isinstance(config.diversity_optimizer, DiversityOptimizerConfig)


def test_loader_with_nonexistent_file():
    """Test loader with non-existent configuration file."""
    with pytest.raises(OptimizationConfigNotFoundError):
        OptimizationConfigLoader(
            config_path="/non/existent/path.yaml",
            enable_hot_reload=False,
        )


def test_reload_config():
    """Test reloading configuration."""
    if not DEFAULT_OPTIMIZATION_CONFIG_PATH.exists():
        pytest.skip(f"Default config file not found: {DEFAULT_OPTIMIZATION_CONFIG_PATH}")

    loader = OptimizationConfigLoader(
        config_path=DEFAULT_OPTIMIZATION_CONFIG_PATH,
        enable_hot_reload=False,
    )

    config1 = loader.get_config()
    config2 = loader.reload_config()

    assert isinstance(config2, OptimizationConfig)
    assert config1.metadata.version == config2.metadata.version


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


def test_legacy_adapter():
    """Test the legacy configuration adapter."""
    if not DEFAULT_OPTIMIZATION_CONFIG_PATH.exists():
        pytest.skip(f"Default config file not found: {DEFAULT_OPTIMIZATION_CONFIG_PATH}")

    from app.config.optimization_config_loader import get_optimization_config

    config = get_optimization_config()
    adapter = LegacyConfigAdapter(config)

    # Test legacy properties
    assert isinstance(adapter.or_tools_max_fatigue, float)
    assert isinstance(adapter.or_tools_solver_timeout_seconds, int)
    assert isinstance(adapter.or_tools_min_sets_per_movement, int)
    assert isinstance(adapter.or_tools_max_sets_per_movement, int)
    assert isinstance(adapter.or_tools_volume_target_reduction_pct, float)

    # Test dot-notation access
    timeout = adapter.get("or_tools.timeout_seconds")
    assert isinstance(timeout, int)

    # Test dict conversion
    config_dict = adapter.to_dict()
    assert isinstance(config_dict, dict)
    assert "or_tools" in config_dict
    assert "metadata" in config_dict


# ============================================================================
# Activity Distribution Backward Compatibility Tests
# ============================================================================


def test_activity_distribution_backward_compatibility():
    """Test backward compatibility functions in activity_distribution."""
    if not DEFAULT_OPTIMIZATION_CONFIG_PATH.exists():
        pytest.skip(f"Default config file not found: {DEFAULT_OPTIMIZATION_CONFIG_PATH}")

    from app.config.activity_distribution import (
        get_or_tools_max_fatigue,
        get_or_tools_solver_timeout_seconds,
        get_or_tools_min_sets_per_movement,
        get_or_tools_max_sets_per_movement,
        get_or_tools_volume_target_reduction_pct,
    )

    # All getter functions should work
    max_fatigue = get_or_tools_max_fatigue()
    timeout = get_or_tools_solver_timeout_seconds()
    min_sets = get_or_tools_min_sets_per_movement()
    max_sets = get_or_tools_max_sets_per_movement()
    reduction = get_or_tools_volume_target_reduction_pct()

    assert isinstance(max_fatigue, float)
    assert isinstance(timeout, int)
    assert isinstance(min_sets, int)
    assert isinstance(max_sets, int)
    assert isinstance(reduction, float)

    # Verify consistency with new loader
    from app.config.optimization_config_loader import get_optimization_config

    config = get_optimization_config()
    assert max_fatigue == config.or_tools.max_fatigue
    assert timeout == config.or_tools.timeout_seconds
    assert min_sets == config.or_tools.min_sets_per_movement
    assert max_sets == config.or_tools.max_sets_per_movement
    assert reduction == config.or_tools.volume_target_reduction_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
