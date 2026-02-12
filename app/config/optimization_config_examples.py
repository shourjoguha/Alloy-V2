"""
Examples demonstrating the usage of the optimization_config_loader module.

This file provides comprehensive examples of how to use the unified optimization
configuration system with Pydantic validation and hot-reload support.
"""

from app.config.optimization_config_loader import (
    # Enums
    CircuitType,
    FatigueLevel,
    NormalizationMethod,
    RelaxationStrategy,
    ScoringMethod,
    SolverStrategy,
    TiebreakerStrategy,
    # Models
    CircuitConfig,
    DiversityOptimizerConfig,
    GlobalConfig,
    HardConstraints,
    Metadata,
    OptimizationConfig,
    ORToolsConfig,
    RepSetRange,
    RepSetRanges,
    RelaxationConfig,
    SafetyConstraints,
    TiebreakerConfig,
    TimeConstraints,
    UserRules,
    VarietyConstraints,
    NormalizationConfig,
    # Exceptions
    OptimizationConfigError,
    OptimizationConfigLoadError,
    OptimizationConfigNotFoundError,
    OptimizationConfigValidationError,
    # Loader and convenience functions
    get_optimization_config,
    get_optimization_config_loader,
    reload_optimization_config,
    reset_optimization_config_loader,
    OptimizationConfigLoader,
    ReloadStatistics,
    # Backward compatibility
    LegacyConfigAdapter,
    get_legacy_config_adapter,
)


# ============================================================================
# Basic Usage Examples
# ============================================================================


def example_1_basic_config_access() -> None:
    """Example 1: Basic configuration access using convenience function."""
    print("Example 1: Basic Configuration Access")
    print("-" * 50)

    # Get the current configuration
    config = get_optimization_config()

    # Access configuration values with full type safety
    print(f"Config version: {config.metadata.version}")
    print(f"OR-Tools timeout: {config.or_tools.timeout_seconds}s")
    print(f"Max fatigue: {config.or_tools.max_fatigue}")
    print(f"Normalization enabled: {config.global_config.normalization.enabled}")
    print(f"Normalization method: {config.global_config.normalization.method}")

    # Access nested values
    print(f"Warmup sets range: {config.rep_set_ranges.warmup.sets_min} - {config.rep_set_ranges.warmup.sets_max}")
    print(f"Circuit allowed types: {[t.value for t in config.circuit_config.allowed_circuit_types]}")
    print()


def example_2_solver_configuration() -> None:
    """Example 2: Accessing solver configuration."""
    print("Example 2: Solver Configuration")
    print("-" * 50)

    config = get_optimization_config()

    # OR-Tools solver settings
    or_tools = config.or_tools
    print(f"OR-Tools enabled: {or_tools.enabled}")
    print(f"Strategy: {or_tools.strategy}")
    print(f"Timeout: {or_tools.timeout_seconds}s")
    print(f"Max solutions: {or_tools.max_solutions}")
    print(f"Feasibility check first: {or_tools.feasibility_check_first}")

    # Diversity optimizer settings
    diversity = config.diversity_optimizer
    print(f"\nDiversity optimizer enabled: {diversity.enabled}")
    print(f"Scoring method: {diversity.scoring_method}")
    print(f"ML scoring: {diversity.enable_ml_scoring}")
    print(f"Cache enabled: {diversity.cache_scores}")
    print(f"Max candidates: {diversity.max_candidates}")
    print()


def example_3_constraints_configuration() -> None:
    """Example 3: Accessing constraints configuration."""
    print("Example 3: Constraints Configuration")
    print("-" * 50)

    config = get_optimization_config()

    # Time constraints
    time = config.hard_constraints.time
    print("Time constraints:")
    print(f"  Enforced: {time.enforce}")
    print(f"  Max per block: {time.max_time_per_block_minutes}min")
    print(f"  Max per session: {time.max_time_per_session_minutes}min")
    print(f"  Min per movement: {time.min_time_per_movement_minutes}min")

    # Variety constraints
    variety = config.hard_constraints.variety
    print("\nVariety constraints:")
    print(f"  Enforced: {variety.enforce}")
    print(f"  Min pattern variety: {variety.min_pattern_variety_per_session}")
    print(f"  Max pattern repeats: {variety.max_pattern_repeats_per_session}")

    # Safety constraints
    safety = config.hard_constraints.safety
    print("\nSafety constraints:")
    print(f"  Enforced: {safety.enforce}")
    print(f"  Check contraindications: {safety.check_contraindications}")
    print(f"  Block risky combinations: {safety.block_risky_combinations}")
    print()


def example_4_rep_set_ranges() -> None:
    """Example 4: Accessing rep/set ranges."""
    print("Example 4: Rep/Set Ranges")
    print("-" * 50)

    config = get_optimization_config()

    # Warmup range
    warmup = config.rep_set_ranges.warmup
    print("Warmup range:")
    print(f"  Sets: {warmup.sets_min}-{warmup.sets_max} (default: {warmup.sets_default})")
    print(f"  Reps: {warmup.reps_min}-{warmup.reps_max} (default: {warmup.reps_default})")
    print(f"  Intensity: {warmup.intensity_pct_range[0]}%-{warmup.intensity_pct_range[1]}%")
    print(f"  Rest: {warmup.rest_seconds_range[0]}-{warmup.rest_seconds_range[1]}s")
    print(f"  RPE: {warmup.rpe_target_range[0]}-{warmup.rpe_target_range[1]}")
    print(f"  Tempo: {warmup.tempo}")

    # Circuit range
    circuit = config.rep_set_ranges.circuit
    print("\nCircuit range:")
    print(f"  Sets: {circuit.sets_min}-{circuit.sets_max} (default: {circuit.sets_default})")
    print(f"  Reps: {circuit.reps_min}-{circuit.reps_max} (default: {circuit.reps_default})")
    print(f"  Intensity: {circuit.intensity_pct_range[0]}%-{circuit.intensity_pct_range[1]}%")
    print(f"  Rest: {circuit.rest_seconds_range[0]}-{circuit.rest_seconds_range[1]}s")
    print()


def example_5_advanced_configuration() -> None:
    """Example 5: Advanced configuration access."""
    print("Example 5: Advanced Configuration")
    print("-" * 50)

    config = get_optimization_config()

    # Global configuration
    global_config = config.global_config
    print("Global config:")
    print(f"  Debug enabled: {global_config.debug_enabled}")
    print(f"  Cache enabled: {global_config.cache_enabled}")
    print(f"  Strict mode: {global_config.strict_mode}")
    print(f"  Validate on load: {global_config.validate_on_load}")

    # Tiebreaker configuration
    tiebreaker = global_config.tiebreaker
    print("\nTiebreaker:")
    print(f"  Enabled: {tiebreaker.enabled}")
    print(f"  Strategy: {tiebreaker.strategy}")
    print(f"  Priority order: {tiebreaker.priority_order}")

    # Relaxation configuration
    relaxation = global_config.relaxation
    print("\nRelaxation:")
    print(f"  Enabled: {relaxation.enabled}")
    print(f"  Strategy: {relaxation.strategy}")
    print(f"  Penalty weight: {relaxation.penalty_weight}")
    print(f"  Max relaxations: {relaxation.max_relaxations}")
    print(f"  Relaxable constraints: {relaxation.relaxable_constraints}")
    print()


# ============================================================================
# Hot-Reload Examples
# ============================================================================


def example_6_register_reload_callback() -> None:
    """Example 6: Registering reload callbacks."""
    print("Example 6: Reload Callbacks")
    print("-" * 50)

    loader = get_optimization_config_loader()

    # Define a callback function
    def on_config_reloaded(new_config: OptimizationConfig) -> None:
        print(f"Configuration reloaded! New version: {new_config.metadata.version}")
        print(f"Reloaded at: {new_config.metadata.last_updated}")

    # Register the callback
    loader.register_reload_callback(on_config_reloaded)

    print("Reload callback registered. Callback will be triggered on:")
    print("  - Manual reload via reload_optimization_config()")
    print("  - File changes (if hot-reload is enabled)")
    print()


def example_7_manual_reload() -> None:
    """Example 7: Manually reloading configuration."""
    print("Example 7: Manual Reload")
    print("-" * 50)

    # Get current version
    config = get_optimization_config()
    print(f"Current config version: {config.metadata.version}")

    # Reload configuration
    new_config = reload_optimization_config()
    print(f"Reloaded config version: {new_config.metadata.version}")

    # Get reload statistics
    loader = get_optimization_config_loader()
    stats = loader.get_reload_statistics()
    print(f"Total reloads: {stats.total_reloads}")
    print(f"Successful reloads: {stats.successful_reloads}")
    print(f"Failed reloads: {stats.failed_reloads}")
    print(f"Last reload success: {stats.last_reload_success}")
    print()


def example_8_custom_loader_instance() -> None:
    """Example 8: Creating a custom loader instance."""
    print("Example 8: Custom Loader Instance")
    print("-" * 50)

    # Reset the default loader (useful for testing)
    reset_optimization_config_loader()

    # Create a new loader with custom settings
    custom_loader = OptimizationConfigLoader(
        config_path="/path/to/custom/config.yaml",  # Use your custom path
        enable_hot_reload=True,
        hot_reload_interval_seconds=10.0,
        validate_on_load=True,
    )

    # Get configuration from custom loader
    config = custom_loader.get_config()
    print(f"Config version: {config.metadata.version}")

    # Register callback for this specific loader
    custom_loader.register_reload_callback(
        lambda cfg: print(f"Custom loader reloaded: {cfg.metadata.version}")
    )
    print()


# ============================================================================
# Error Handling Examples
# ============================================================================


def example_9_error_handling() -> None:
    """Example 9: Handling configuration errors."""
    print("Example 9: Error Handling")
    print("-" * 50)

    try:
        # Try to load from a non-existent file
        reset_optimization_config_loader()
        loader = OptimizationConfigLoader(
            config_path="/non/existent/path.yaml",
            enable_hot_reload=False,
        )
    except OptimizationConfigNotFoundError as e:
        print(f"Config not found: {e.message}")
        print(f"Path: {e.path}")

    try:
        # Try to create an invalid config
        invalid_config = OptimizationConfig(
            metadata=Metadata(
                version="invalid",  # Invalid version format
                author="Test",
                description="Test config",
            ),
            or_tools=ORToolsConfig(enabled=False),
            diversity_optimizer=DiversityOptimizerConfig(enabled=False),
        )
    except OptimizationConfigValidationError as e:
        print(f"Validation error: {e.message}")

    print()


# ============================================================================
# Backward Compatibility Examples
# ============================================================================


def example_10_legacy_adapter() -> None:
    """Example 10: Using the legacy adapter for backward compatibility."""
    print("Example 10: Legacy Adapter (Backward Compatibility)")
    print("-" * 50)

    config = get_optimization_config()

    # Create a legacy adapter
    adapter = LegacyConfigAdapter(config)

    # Use legacy-style access
    print(f"Max fatigue (legacy property): {adapter.or_tools_max_fatigue}")
    print(f"Timeout (legacy property): {adapter.or_tools_solver_timeout_seconds}")
    print(f"Min sets (legacy property): {adapter.or_tools_min_sets_per_movement}")
    print(f"Max sets (legacy property): {adapter.or_tools_max_sets_per_movement}")
    print(f"Volume reduction (legacy property): {adapter.or_tools_volume_target_reduction_pct}")

    # Use dot-notation access
    print(f"Timeout (dot notation): {adapter.get('or_tools.timeout_seconds')}")
    print(f"Debug mode (dot notation): {adapter.get('global_config.debug_enabled')}")

    # Convert to dictionary
    config_dict = adapter.to_dict()
    print(f"Config as dict keys: {list(config_dict.keys())}")
    print()


# ============================================================================
# Model Creation Examples
# ============================================================================


def example_11_creating_custom_models() -> None:
    """Example 11: Creating custom configuration models."""
    print("Example 11: Creating Custom Models")
    print("-" * 50)

    # Create a custom rep/set range
    custom_warmup = RepSetRange(
        sets_min=1,
        sets_max=4,
        sets_default=2,
        reps_min=5,
        reps_max=20,
        reps_default=10,
        intensity_pct_range=(40.0, 60.0),
        rest_seconds_range=(30, 60),
        rpe_target_range=(1, 3),
        tempo="3-0-2",
    )
    print(f"Custom warmup sets: {custom_warmup.sets_min}-{custom_warmup.sets_max}")

    # Create custom circuit config
    custom_circuit = CircuitConfig(
        exempt_from_rep_set_ranges=True,
        allowed_circuit_types=[CircuitType.AMRAP, CircuitType.EMOM],
        default_rounds=4,
        max_rounds=12,
        work_seconds_range=(15, 45),
        rest_seconds_range=(15, 45),
        total_time_limit_seconds=720,
    )
    print(f"Custom circuit max rounds: {custom_circuit.max_rounds}")

    # Create custom metadata
    custom_metadata = Metadata(
        version="2.0.0",
        author="Custom Author",
        description="Custom configuration",
        tags=["custom", "test"],
        environment="development",
    )
    print(f"Custom metadata version: {custom_metadata.version}")
    print()


# ============================================================================
# Thread-Safe Access Example
# ============================================================================


def example_12_thread_safe_access() -> None:
    """Example 12: Thread-safe configuration access."""
    print("Example 12: Thread-Safe Access")
    print("-" * 50)

    loader = get_optimization_config_loader()

    # Use context manager for thread-safe access
    with loader.get_config_context() as config:
        timeout = config.or_tools.timeout_seconds
        max_fatigue = config.or_tools.max_fatigue
        print(f"Timeout: {timeout}s, Max fatigue: {max_fatigue}")

    # Multiple accesses are thread-safe
    with loader.get_config_context() as config:
        version = config.metadata.version
        author = config.metadata.author
        print(f"Version: {version}, Author: {author}")

    print()


# ============================================================================
# Running Examples
# ============================================================================


def run_all_examples() -> None:
    """Run all examples."""
    examples = [
        example_1_basic_config_access,
        example_2_solver_configuration,
        example_3_constraints_configuration,
        example_4_rep_set_ranges,
        example_5_advanced_configuration,
        example_6_register_reload_callback,
        example_7_manual_reload,
        example_8_custom_loader_instance,
        example_9_error_handling,
        example_10_legacy_adapter,
        example_11_creating_custom_models,
        example_12_thread_safe_access,
    ]

    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"Error in example {i}: {e}")
            print()
            continue

        # Separator between examples
        if i < len(examples):
            print("=" * 50)
            print()


if __name__ == "__main__":
    run_all_examples()
