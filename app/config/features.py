"""
Feature flags configuration for the application.

This module provides a centralized way to enable/disable features
throughout the application. Feature flags allow for:
- Safe rollouts of new features
- A/B testing
- Quick rollback of problematic features
- Gradual feature deployment

Feature flags can be controlled via:
1. Environment variables (APP_FEATURE_<FEATURE_NAME>=true/false)
2. Configuration settings (app.config.settings)
3. Database configuration table
4. External feature flag service (e.g., LaunchDarkly, Unleash)

Phase 6: Full feature flag system with database backing and admin UI.
This is a stub implementation for backward compatibility.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Protocol

# Import for type hints in docstrings (lazy import)
def _get_time_estimation_service():
    from app.services.time_estimation import TimeEstimationService
    return TimeEstimationService()

logger = logging.getLogger(__name__)


class RolloutPhase(Enum):
    """Enumeration of rollout phases for gradual feature deployment."""
    BASELINE_COLLECTION = "baseline_collection"
    TEST_USERS = "test_users"
    FULL_ROLLOUT = "full_rollloout"
    COMPLETED = "completed"


@dataclass
class RolloutConfig:
    """Configuration for gradual feature rollout strategy."""
    feature_name: str
    current_phase: RolloutPhase
    start_date: datetime
    week_1_end: datetime
    week_2_end: datetime
    week_3_end: datetime
    test_user_ids: set[int] = field(default_factory=set)
    success_threshold: float = 0.95  # 95% success rate required
    rollback_threshold: float = 0.90  # Rollback if below 90% success
    
    def is_in_phase(self, phase: RolloutPhase) -> bool:
        """Check if rollout is in a specific phase."""
        return self.current_phase == phase
    
    def should_enable_for_user(self, user_id: Optional[int] = None) -> bool:
        """Determine if feature should be enabled for a specific user."""
        now = datetime.now()
        
        if self.current_phase == RolloutPhase.BASELINE_COLLECTION:
            return False
        
        if self.current_phase == RolloutPhase.TEST_USERS:
            return user_id in self.test_user_ids if user_id else False
        
        if self.current_phase in (RolloutPhase.FULL_ROLLOUT, RolloutPhase.COMPLETED):
            return True
        
        return False
    
    def get_phase_description(self) -> str:
        """Get human-readable description of current phase."""
        descriptions = {
            RolloutPhase.BASELINE_COLLECTION: "Week 1: Collecting baseline metrics with feature disabled",
            RolloutPhase.TEST_USERS: "Week 2: Feature enabled for test users only",
            RolloutPhase.FULL_ROLLOUT: "Week 3: Feature enabled for all users, monitoring success rates",
            RolloutPhase.COMPLETED: "Rollout completed successfully",
        }
        return descriptions.get(self.current_phase, "Unknown phase")


@dataclass
class FeatureFlag:
    """Individual feature flag with metadata and rollout configuration."""
    name: str
    enabled: bool
    description: str
    rollout_config: Optional[RolloutConfig] = None
    category: str = "general"
    requires_database: bool = False
    last_modified: datetime = field(default_factory=datetime.now)
    
    def enable(self) -> None:
        """Enable the feature flag."""
        self.enabled = True
        self.last_modified = datetime.now()
        logger.info(f"Feature flag '{self.name}' enabled")
    
    def disable(self) -> None:
        """Disable the feature flag."""
        self.enabled = False
        self.last_modified = datetime.now()
        logger.info(f"Feature flag '{self.name}' disabled")
    
    def should_enable_for_user(self, user_id: Optional[int] = None) -> bool:
        """Determine if feature should be enabled for a specific user."""
        if not self.enabled:
            return False
        
        if self.rollout_config:
            return self.rollout_config.should_enable_for_user(user_id)
        
        return True


# Default feature flag values
DEFAULT_FEATURE_FLAGS = {
    # Diversity Scoring: Use diversity-based scoring algorithm (disabled initially)
    "use_diversity_scoring": False,
    
    # Metrics Logging: Enable comprehensive metrics logging (enabled immediately)
    "enable_metrics_logging": True,
    
    # Optimization: Use the new diversity optimizer with scoring (disabled initially)
    "use_diversity_optimizer": False,
    
    # ML: Enable machine learning movement scoring
    "enable_ml_scoring": False,
    
    # UI: Enable new workout generation UI
    "enable_new_workout_ui": False,
    
    # Performance: Enable caching for optimization results
    "enable_optimization_cache": False,
    
    # Beta: Enable experimental features
    "enable_beta_features": False,
}

# Feature flag descriptions
FEATURE_DESCRIPTIONS = {
    "use_diversity_scoring": "Enable diversity-based scoring algorithm for movement selection",
    "enable_metrics_logging": "Enable comprehensive metrics logging for all operations",
    "use_diversity_optimizer": "Use the new diversity optimizer with scoring for workout generation",
    "enable_ml_scoring": "Enable machine learning movement scoring",
    "enable_new_workout_ui": "Enable new workout generation UI",
    "enable_optimization_cache": "Enable caching for optimization results",
    "enable_beta_features": "Enable experimental beta features",
}

# Feature flag categories
FEATURE_CATEGORIES = {
    "use_diversity_scoring": "optimization",
    "enable_metrics_logging": "monitoring",
    "use_diversity_optimizer": "optimization",
    "enable_ml_scoring": "ml",
    "enable_new_workout_ui": "ui",
    "enable_optimization_cache": "performance",
    "enable_beta_features": "experimental",
}


def get_feature_flags() -> dict[str, Any]:
    """
    Get current feature flags configuration.
    
    Returns:
        Dictionary mapping feature names to their enabled/disabled status.
        
    Example:
        >>> flags = get_feature_flags()
        >>> if flags.get("use_diversity_optimizer"):
        ...     use_new_optimizer()
    """
    flags = dict(DEFAULT_FEATURE_FLAGS)
    
    # Override with environment variables
    for key in flags:
        env_var = f"APP_FEATURE_{key.upper()}"
        env_value = os.getenv(env_var)
        if env_value is not None:
            flags[key] = env_value.lower() in ("true", "1", "yes", "on")
    
    # In Phase 6, this would also check:
    # 1. Database feature_flags table
    # 2. External feature flag service
    # 3. User-specific feature overrides
    
    return flags


def create_feature_flag(name: str, enabled: bool = False) -> FeatureFlag:
    """
    Create a FeatureFlag instance from a name and enabled state.
    
    Args:
        name: Name of the feature flag.
        enabled: Whether the feature is enabled.
        
    Returns:
        A FeatureFlag instance with description and category.
        
    Example:
        >>> flag = create_feature_flag("use_diversity_scoring", True)
        >>> flag.description
        'Enable diversity-based scoring algorithm for movement selection'
    """
    description = FEATURE_DESCRIPTIONS.get(name, f"Feature flag: {name}")
    category = FEATURE_CATEGORIES.get(name, "general")
    
    return FeatureFlag(
        name=name,
        enabled=enabled,
        description=description,
        category=category,
    )


def get_feature_flag(name: str) -> FeatureFlag:
    """
    Get a FeatureFlag instance with current state.
    
    Args:
        name: Name of the feature flag.
        
    Returns:
        A FeatureFlag instance representing the current state.
        
    Example:
        >>> flag = get_feature_flag("use_diversity_optimizer")
        >>> if flag.enabled:
        ...     print("Diversity optimizer is enabled")
    """
    flags = get_feature_flags()
    enabled = flags.get(name, False)
    
    return create_feature_flag(name, enabled)


def is_feature_enabled(feature_name: str, user_id: Optional[int] = None) -> bool:
    """
    Check if a specific feature is enabled for a user.
    
    Args:
        feature_name: Name of the feature flag to check.
        user_id: Optional user ID for user-specific feature checks.
        
    Returns:
        True if feature is enabled for the user, False otherwise.
        
    Example:
        >>> if is_feature_enabled("use_greedy_optimizer", user_id=123):
        ...     from app.services.time_estimation import TimeEstimationService
        ...     return GreedyOptimizationService(time_estimation_service=TimeEstimationService())
        >>> else:
        ...     return LegacyOptimizer()
    """
    flags = get_feature_flags()
    enabled = flags.get(feature_name, False)
    
    if enabled and user_id:
        flag = get_feature_flag(feature_name)
        return flag.should_enable_for_user(user_id)
    
    return enabled


def set_feature_flag(feature_name: str, enabled: bool) -> None:
    """
    Set a feature flag value (in-memory only).
    
    In Phase 6, this would persist to the database.
    
    Args:
        feature_name: Name of the feature flag.
        enabled: Whether the feature should be enabled.
        
    Example:
        >>> set_feature_flag("use_diversity_optimizer", True)
    """
    # In-memory update only for now
    DEFAULT_FEATURE_FLAGS[feature_name] = enabled
    logger.info(f"Feature flag '{feature_name}' set to {enabled}")


# Rollout configuration storage
_rollout_configs: dict[str, RolloutConfig] = {}


def setup_diversity_rollout(
    test_user_ids: Optional[set[int]] = None,
    start_date: Optional[datetime] = None,
) -> RolloutConfig:
    """
    Setup the gradual rollout strategy for diversity features.
    
    Args:
        test_user_ids: Set of user IDs for test phase. Defaults to empty set.
        start_date: Start date for rollout. Defaults to now.
        
    Returns:
        Configured RolloutConfig instance.
        
    Example:
        >>> config = setup_diversity_rollout(test_user_ids={1, 2, 3})
        >>> config.current_phase
        <RolloutPhase.BASELINE_COLLECTION: 'baseline_collection'>
    """
    if start_date is None:
        start_date = datetime.now()
    
    if test_user_ids is None:
        test_user_ids = set()
    
    # Define rollout timeline (3 weeks)
    week_1_end = start_date + timedelta(days=7)
    week_2_end = start_date + timedelta(days=14)
    week_3_end = start_date + timedelta(days=21)
    
    # Create rollout config for diversity scoring
    config = RolloutConfig(
        feature_name="use_diversity_scoring",
        current_phase=RolloutPhase.BASELINE_COLLECTION,
        start_date=start_date,
        week_1_end=week_1_end,
        week_2_end=week_2_end,
        week_3_end=week_3_end,
        test_user_ids=test_user_ids,
    )
    
    _rollout_configs["use_diversity_scoring"] = config
    
    # Also setup for diversity optimizer
    optimizer_config = RolloutConfig(
        feature_name="use_diversity_optimizer",
        current_phase=RolloutPhase.BASELINE_COLLECTION,
        start_date=start_date,
        week_1_end=week_1_end,
        week_2_end=week_2_end,
        week_3_end=week_3_end,
        test_user_ids=test_user_ids,
    )
    
    _rollout_configs["use_diversity_optimizer"] = optimizer_config
    
    logger.info(
        f"Rollout strategy configured for diversity features. "
        f"Phase: {config.current_phase.value}, "
        f"Test users: {len(test_user_ids)}"
    )
    
    return config


def advance_rollout_phase(feature_name: str) -> bool:
    """
    Advance the rollout phase for a feature to the next stage.
    
    Args:
        feature_name: Name of the feature to advance.
        
    Returns:
        True if phase was advanced, False if already completed or not found.
        
    Example:
        >>> advance_rollout_phase("use_diversity_scoring")
        True
    """
    if feature_name not in _rollout_configs:
        logger.warning(f"No rollout config found for feature: {feature_name}")
        return False
    
    config = _rollout_configs[feature_name]
    
    phase_progression = {
        RolloutPhase.BASELINE_COLLECTION: RolloutPhase.TEST_USERS,
        RolloutPhase.TEST_USERS: RolloutPhase.FULL_ROLLOUT,
        RolloutPhase.FULL_ROLLOUT: RolloutPhase.COMPLETED,
    }
    
    next_phase = phase_progression.get(config.current_phase)
    
    if next_phase:
        config.current_phase = next_phase
        
        # Update feature flag based on phase
        if next_phase in (RolloutPhase.TEST_USERS, RolloutPhase.FULL_ROLLOUT, RolloutPhase.COMPLETED):
            set_feature_flag(feature_name, True)
        
        logger.info(
            f"Rollout phase advanced for '{feature_name}': "
            f"{config.current_phase.value} - {config.get_phase_description()}"
        )
        return True
    
    logger.info(f"Rollout already completed for feature: {feature_name}")
    return False


def get_rollout_status(feature_name: str) -> Optional[dict[str, Any]]:
    """
    Get the current rollout status for a feature.
    
    Args:
        feature_name: Name of the feature.
        
    Returns:
        Dictionary with rollout status or None if not configured.
        
    Example:
        >>> status = get_rollout_status("use_diversity_scoring")
        >>> status['phase']
        'baseline_collection'
    """
    if feature_name not in _rollout_configs:
        return None
    
    config = _rollout_configs[feature_name]
    
    return {
        "feature_name": config.feature_name,
        "phase": config.current_phase.value,
        "description": config.get_phase_description(),
        "start_date": config.start_date.isoformat(),
        "test_user_count": len(config.test_user_ids),
        "success_threshold": config.success_threshold,
        "rollback_threshold": config.rollback_threshold,
    }


def emergency_rollback() -> dict[str, str]:
    """
    Emergency rollback: Disable all diversity features instantly.
    
    This function should be called if critical issues are detected
    during rollout that require immediate disabling of features.
    
    Returns:
        Dictionary mapping feature names to their previous states.
        
    Example:
        >>> previous_states = emergency_rollback()
        >>> previous_states["use_diversity_scoring"]
        'True'
    """
    diversity_features = [
        "use_diversity_scoring",
        "use_diversity_optimizer",
        "enable_ml_scoring",
    ]
    
    previous_states: dict[str, str] = {}
    
    for feature_name in diversity_features:
        current_state = DEFAULT_FEATURE_FLAGS.get(feature_name, False)
        previous_states[feature_name] = str(current_state)
        
        # Disable the feature
        set_feature_flag(feature_name, False)
        
        # Reset rollout config to baseline if exists
        if feature_name in _rollout_configs:
            _rollout_configs[feature_name].current_phase = RolloutPhase.BASELINE_COLLECTION
    
    logger.critical(
        f"EMERGENCY ROLLBACK EXECUTED. Disabled {len(diversity_features)} features. "
        f"Previous states: {previous_states}"
    )
    
    return previous_states


def get_rollback_steps() -> list[dict[str, str]]:
    """
    Get rollback instructions for diversity features.
    
    Returns:
        List of rollback steps with descriptions and commands.
        
    Example:
        >>> steps = get_rollback_steps()
        >>> for step in steps:
        ...     print(f"{step['step']}: {step['description']}")
    """
    steps = [
        {
            "step": "1",
            "priority": "CRITICAL",
            "description": "Emergency rollback - disable all diversity features",
            "action": "Call emergency_rollback() function",
            "code": "from app.config.features import emergency_rollback; emergency_rollback()",
            "estimated_time": "< 1 second",
        },
        {
            "step": "2",
            "priority": "HIGH",
            "description": "Stop any ongoing optimization processes",
            "action": "Kill running optimization workers",
            "code": "# Kill optimization processes\npkill -f optimization",
            "estimated_time": "< 5 seconds",
        },
        {
            "step": "3",
            "priority": "HIGH",
            "description": "Clear any cached optimization results",
            "action": "Flush optimization cache",
            "code": "# Clear cache (if Redis or similar)\nredis-cli FLUSHDB",
            "estimated_time": "< 1 second",
        },
        {
            "step": "4",
            "priority": "MEDIUM",
            "description": "Review metrics logs to identify the issue",
            "action": "Analyze recent error logs and metrics",
            "code": "# Check recent logs\ntail -n 100 backend.log | grep -i error",
            "estimated_time": "5-10 minutes",
        },
        {
            "step": "5",
            "priority": "MEDIUM",
            "description": "Revert database changes if applicable",
            "action": "Rollback recent migrations",
            "code": "alembic downgrade -1",
            "estimated_time": "1-2 minutes",
        },
        {
            "step": "6",
            "priority": "LOW",
            "description": "Notify stakeholders of the rollback",
            "action": "Send alert to development team",
            "code": "# Send notification via your alerting system",
            "estimated_time": "< 1 minute",
        },
        {
            "step": "7",
            "priority": "LOW",
            "description": "Document the incident and root cause",
            "action": "Create incident report",
            "code": "# Document in incident tracking system",
            "estimated_time": "15-30 minutes",
        },
    ]
    
    return steps


# Database integration stub (Phase 6)
class DatabaseFeatureFlagStorage(Protocol):
    """
    Protocol for database-backed feature flag storage.
    
    This protocol defines the interface for persistent feature flag storage
    that will be implemented in Phase 6.
    """
    
    async def load_feature_flags(self) -> dict[str, bool]:
        """Load feature flags from database."""
        ...
    
    async def save_feature_flag(self, name: str, enabled: bool) -> None:
        """Save feature flag to database."""
        ...
    
    async def load_rollout_config(self, feature_name: str) -> Optional[RolloutConfig]:
        """Load rollout configuration from database."""
        ...
    
    async def save_rollout_config(self, config: RolloutConfig) -> None:
        """Save rollout configuration to database."""
        ...


# Placeholder for future database integration
_db_storage: Optional[DatabaseFeatureFlagStorage] = None


async def load_flags_from_database() -> None:
    """
    Load feature flags from database (Phase 6).
    
    This function will be implemented when database integration is added
    to provide persistent feature flag storage.
    """
    if _db_storage is None:
        logger.warning("Database storage not initialized. Using in-memory flags.")
        return
    
    try:
        flags = await _db_storage.load_feature_flags()
        DEFAULT_FEATURE_FLAGS.update(flags)
        logger.info(f"Loaded {len(flags)} feature flags from database")
    except Exception as e:
        logger.error(f"Failed to load feature flags from database: {e}")


async def save_flags_to_database() -> None:
    """
    Save current feature flags to database (Phase 6).
    
    This function will be implemented when database integration is added
    to provide persistent feature flag storage.
    """
    if _db_storage is None:
        logger.warning("Database storage not initialized. Flags not persisted.")
        return
    
    try:
        for name, enabled in DEFAULT_FEATURE_FLAGS.items():
            await _db_storage.save_feature_flag(name, enabled)
        logger.info(f"Saved {len(DEFAULT_FEATURE_FLAGS)} feature flags to database")
    except Exception as e:
        logger.error(f"Failed to save feature flags to database: {e}")


# Feature flag constants for type safety
class FeatureFlags:
    """Feature flag name constants."""
    
    USE_DIVERSITY_SCORING = "use_diversity_scoring"
    ENABLE_METRICS_LOGGING = "enable_metrics_logging"
    USE_DIVERSITY_OPTIMIZER = "use_diversity_optimizer"
    ENABLE_ML_SCORING = "enable_ml_scoring"
    ENABLE_NEW_WORKOUT_UI = "enable_new_workout_ui"
    ENABLE_OPTIMIZATION_CACHE = "enable_optimization_cache"
    ENABLE_BETA_FEATURES = "enable_beta_features"
