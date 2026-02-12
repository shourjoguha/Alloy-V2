"""
Tests for feature flags configuration and rollout management.

This module tests the comprehensive feature flag system including:
- Feature flag creation and management
- Gradual rollout strategy
- Emergency rollback functionality
- Database integration stubs
"""

import pytest
from datetime import datetime, timedelta
from app.config.features import (
    FeatureFlag,
    RolloutConfig,
    RolloutPhase,
    DEFAULT_FEATURE_FLAGS,
    FEATURE_DESCRIPTIONS,
    FEATURE_CATEGORIES,
    get_feature_flags,
    create_feature_flag,
    get_feature_flag,
    is_feature_enabled,
    set_feature_flag,
    setup_diversity_rollout,
    advance_rollout_phase,
    get_rollout_status,
    emergency_rollback,
    get_rollback_steps,
    DatabaseFeatureFlagStorage,
    load_flags_from_database,
    save_flags_to_database,
    FeatureFlags,
)


class TestFeatureFlag:
    """Tests for FeatureFlag dataclass."""
    
    def test_create_feature_flag(self):
        """Test creating a feature flag with default values."""
        flag = FeatureFlag(
            name="test_feature",
            enabled=True,
            description="Test feature description",
        )
        
        assert flag.name == "test_feature"
        assert flag.enabled is True
        assert flag.description == "Test feature description"
        assert flag.category == "general"
        assert flag.requires_database is False
    
    def test_feature_flag_enable(self):
        """Test enabling a feature flag."""
        flag = FeatureFlag(
            name="test_feature",
            enabled=False,
            description="Test feature",
        )
        
        flag.enable()
        assert flag.enabled is True
    
    def test_feature_flag_disable(self):
        """Test disabling a feature flag."""
        flag = FeatureFlag(
            name="test_feature",
            enabled=True,
            description="Test feature",
        )
        
        flag.disable()
        assert flag.enabled is False
    
    def test_should_enable_for_user_no_rollout(self):
        """Test user-specific enablement without rollout config."""
        flag = FeatureFlag(
            name="test_feature",
            enabled=True,
            description="Test feature",
        )
        
        assert flag.should_enable_for_user(user_id=123) is True
        assert flag.should_enable_for_user(user_id=None) is True
    
    def test_should_enable_for_user_disabled(self):
        """Test user-specific enablement when feature is disabled."""
        flag = FeatureFlag(
            name="test_feature",
            enabled=False,
            description="Test feature",
        )
        
        assert flag.should_enable_for_user(user_id=123) is False


class TestRolloutConfig:
    """Tests for RolloutConfig dataclass."""
    
    def test_rollout_config_creation(self):
        """Test creating a rollout configuration."""
        start_date = datetime.now()
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.BASELINE_COLLECTION,
            start_date=start_date,
            week_1_end=start_date + timedelta(days=7),
            week_2_end=start_date + timedelta(days=14),
            week_3_end=start_date + timedelta(days=21),
            test_user_ids={1, 2, 3},
        )
        
        assert config.feature_name == "test_feature"
        assert config.current_phase == RolloutPhase.BASELINE_COLLECTION
        assert config.test_user_ids == {1, 2, 3}
        assert config.success_threshold == 0.95
        assert config.rollback_threshold == 0.90
    
    def test_is_in_phase(self):
        """Test checking if rollout is in a specific phase."""
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.TEST_USERS,
            start_date=datetime.now(),
            week_1_end=datetime.now(),
            week_2_end=datetime.now(),
            week_3_end=datetime.now(),
        )
        
        assert config.is_in_phase(RolloutPhase.TEST_USERS) is True
        assert config.is_in_phase(RolloutPhase.BASELINE_COLLECTION) is False
    
    def test_should_enable_for_user_baseline(self):
        """Test user enablement during baseline collection phase."""
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.BASELINE_COLLECTION,
            start_date=datetime.now(),
            week_1_end=datetime.now(),
            week_2_end=datetime.now(),
            week_3_end=datetime.now(),
            test_user_ids={1, 2, 3},
        )
        
        assert config.should_enable_for_user(user_id=1) is False
        assert config.should_enable_for_user(user_id=999) is False
    
    def test_should_enable_for_user_test_phase(self):
        """Test user enablement during test users phase."""
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.TEST_USERS,
            start_date=datetime.now(),
            week_1_end=datetime.now(),
            week_2_end=datetime.now(),
            week_3_end=datetime.now(),
            test_user_ids={1, 2, 3},
        )
        
        assert config.should_enable_for_user(user_id=1) is True
        assert config.should_enable_for_user(user_id=999) is False
    
    def test_should_enable_for_user_full_rollout(self):
        """Test user enablement during full rollout phase."""
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.FULL_ROLLOUT,
            start_date=datetime.now(),
            week_1_end=datetime.now(),
            week_2_end=datetime.now(),
            week_3_end=datetime.now(),
            test_user_ids={1, 2, 3},
        )
        
        assert config.should_enable_for_user(user_id=1) is True
        assert config.should_enable_for_user(user_id=999) is True
    
    def test_get_phase_description(self):
        """Test getting human-readable phase descriptions."""
        config = RolloutConfig(
            feature_name="test_feature",
            current_phase=RolloutPhase.BASELINE_COLLECTION,
            start_date=datetime.now(),
            week_1_end=datetime.now(),
            week_2_end=datetime.now(),
            week_3_end=datetime.now(),
        )
        
        description = config.get_phase_description()
        assert "Week 1" in description
        assert "baseline" in description.lower()


class TestFeatureFlagManagement:
    """Tests for feature flag management functions."""
    
    def test_get_feature_flags(self):
        """Test getting current feature flags."""
        flags = get_feature_flags()
        
        assert isinstance(flags, dict)
        assert "use_diversity_scoring" in flags
        assert "enable_metrics_logging" in flags
        assert "use_diversity_optimizer" in flags
    
    def test_create_feature_flag_from_name(self):
        """Test creating feature flag from name."""
        flag = create_feature_flag("use_diversity_scoring", True)
        
        assert flag.name == "use_diversity_scoring"
        assert flag.enabled is True
        assert flag.description == FEATURE_DESCRIPTIONS["use_diversity_scoring"]
        assert flag.category == FEATURE_CATEGORIES["use_diversity_scoring"]
    
    def test_get_feature_flag(self):
        """Test getting feature flag instance."""
        flag = get_feature_flag("use_diversity_optimizer")
        
        assert flag.name == "use_diversity_optimizer"
        assert isinstance(flag, FeatureFlag)
    
    def test_is_feature_enabled_basic(self):
        """Test basic feature enablement check."""
        # Metrics logging should be enabled by default
        assert is_feature_enabled("enable_metrics_logging") is True
        
        # Diversity features should be disabled by default
        assert is_feature_enabled("use_diversity_scoring") is False
    
    def test_is_feature_enabled_with_user(self):
        """Test feature enablement check with user ID."""
        # This tests the signature but actual user-specific behavior
        # requires rollout configuration
        result = is_feature_enabled("enable_metrics_logging", user_id=123)
        assert result is True
    
    def test_set_feature_flag(self):
        """Test setting a feature flag value."""
        # Store original value
        original = DEFAULT_FEATURE_FLAGS.get("use_diversity_scoring", False)
        
        try:
            set_feature_flag("use_diversity_scoring", True)
            assert DEFAULT_FEATURE_FLAGS["use_diversity_scoring"] is True
            
            set_feature_flag("use_diversity_scoring", False)
            assert DEFAULT_FEATURE_FLAGS["use_diversity_scoring"] is False
        finally:
            # Restore original value
            DEFAULT_FEATURE_FLAGS["use_diversity_scoring"] = original


class TestRolloutStrategy:
    """Tests for gradual rollout strategy."""
    
    def test_setup_diversity_rollout(self):
        """Test setting up diversity feature rollout."""
        test_users = {1, 2, 3}
        config = setup_diversity_rollout(test_user_ids=test_users)
        
        assert config.feature_name == "use_diversity_scoring"
        assert config.current_phase == RolloutPhase.BASELINE_COLLECTION
        assert config.test_user_ids == test_users
    
    def test_advance_rollout_phase(self):
        """Test advancing rollout phase."""
        setup_diversity_rollout(test_user_ids={1, 2, 3})
        
        # Advance from baseline to test users
        success = advance_rollout_phase("use_diversity_scoring")
        assert success is True
        
        status = get_rollout_status("use_diversity_scoring")
        assert status is not None
        assert status["phase"] == "test_users"
    
    def test_advance_nonexistent_feature(self):
        """Test advancing phase for non-existent feature."""
        success = advance_rollout_phase("nonexistent_feature")
        assert success is False
    
    def test_get_rollout_status(self):
        """Test getting rollout status."""
        setup_diversity_rollout(test_user_ids={1, 2, 3})
        
        status = get_rollout_status("use_diversity_scoring")
        
        assert status is not None
        assert status["feature_name"] == "use_diversity_scoring"
        assert status["phase"] == "baseline_collection"
        assert "description" in status
        assert "start_date" in status
        assert status["test_user_count"] == 3
    
    def test_get_rollout_status_nonexistent(self):
        """Test getting status for non-existent feature."""
        status = get_rollout_status("nonexistent_feature")
        assert status is None


class TestEmergencyRollback:
    """Tests for emergency rollback functionality."""
    
    def test_emergency_rollback(self):
        """Test emergency rollback of diversity features."""
        # Enable features first
        set_feature_flag("use_diversity_scoring", True)
        set_feature_flag("use_diversity_optimizer", True)
        
        # Execute rollback
        previous_states = emergency_rollback()
        
        # Check that features were disabled
        assert DEFAULT_FEATURE_FLAGS["use_diversity_scoring"] is False
        assert DEFAULT_FEATURE_FLAGS["use_diversity_optimizer"] is False
        
        # Check that previous states were captured
        assert "use_diversity_scoring" in previous_states
        assert "use_diversity_optimizer" in previous_states
        assert previous_states["use_diversity_scoring"] == "True"
        assert previous_states["use_diversity_optimizer"] == "True"
    
    def test_get_rollback_steps(self):
        """Test getting rollback instructions."""
        steps = get_rollback_steps()
        
        assert isinstance(steps, list)
        assert len(steps) > 0
        
        # Check structure of first step (critical)
        critical_step = steps[0]
        assert "step" in critical_step
        assert "priority" in critical_step
        assert "description" in critical_step
        assert "action" in critical_step
        assert "code" in critical_step
        assert "estimated_time" in critical_step
        
        assert critical_step["priority"] == "CRITICAL"
        assert "emergency" in critical_step["description"].lower()


class TestDatabaseIntegration:
    """Tests for database integration stubs."""
    
    @pytest.mark.asyncio
    async def test_load_flags_from_database_no_storage(self):
        """Test loading flags when database storage is not initialized."""
        # Should not raise an error, just log a warning
        await load_flags_from_database()
        
        # Flags should still be available from defaults
        assert len(DEFAULT_FEATURE_FLAGS) > 0
    
    @pytest.mark.asyncio
    async def test_save_flags_to_database_no_storage(self):
        """Test saving flags when database storage is not initialized."""
        # Should not raise an error, just log a warning
        await save_flags_to_database()
    
    def test_database_feature_flag_storage_protocol(self):
        """Test that DatabaseFeatureFlagStorage is a proper protocol."""
        # This is a compile-time check that the protocol is properly defined
        assert hasattr(DatabaseFeatureFlagStorage, "__protocol_attrs__")


class TestFeatureFlagsConstants:
    """Tests for FeatureFlags constant class."""
    
    def test_feature_flags_constants_exist(self):
        """Test that all feature flag constants are defined."""
        assert hasattr(FeatureFlags, "USE_DIVERSITY_SCORING")
        assert hasattr(FeatureFlags, "ENABLE_METRICS_LOGGING")
        assert hasattr(FeatureFlags, "USE_DIVERSITY_OPTIMIZER")
        assert hasattr(FeatureFlags, "ENABLE_ML_SCORING")
        assert hasattr(FeatureFlags, "ENABLE_NEW_WORKOUT_UI")
        assert hasattr(FeatureFlags, "ENABLE_OPTIMIZATION_CACHE")
        assert hasattr(FeatureFlags, "ENABLE_BETA_FEATURES")
    
    def test_feature_flags_constants_values(self):
        """Test that feature flag constants have correct values."""
        assert FeatureFlags.USE_DIVERSITY_SCORING == "use_diversity_scoring"
        assert FeatureFlags.ENABLE_METRICS_LOGGING == "enable_metrics_logging"
        assert FeatureFlags.USE_DIVERSITY_OPTIMIZER == "use_diversity_optimizer"


class TestFeatureFlagMetadata:
    """Tests for feature flag metadata."""
    
    def test_feature_descriptions(self):
        """Test that all feature flags have descriptions."""
        for flag_name in DEFAULT_FEATURE_FLAGS:
            assert flag_name in FEATURE_DESCRIPTIONS
            assert isinstance(FEATURE_DESCRIPTIONS[flag_name], str)
            assert len(FEATURE_DESCRIPTIONS[flag_name]) > 0
    
    def test_feature_categories(self):
        """Test that all feature flags have categories."""
        for flag_name in DEFAULT_FEATURE_FLAGS:
            assert flag_name in FEATURE_CATEGORIES
            assert isinstance(FEATURE_CATEGORIES[flag_name], str)
            assert len(FEATURE_CATEGORIES[flag_name]) > 0
    
    def test_valid_categories(self):
        """Test that all categories are valid."""
        valid_categories = {
            "optimization",
            "monitoring",
            "ml",
            "ui",
            "performance",
            "experimental",
            "general",
        }
        
        for category in FEATURE_CATEGORIES.values():
            assert category in valid_categories


class TestRolloutProgression:
    """Tests for complete rollout progression."""
    
    def test_complete_rollout_progression(self):
        """Test progressing through all rollout phases."""
        setup_diversity_rollout(test_user_ids={1, 2, 3})
        
        # Start at baseline
        status = get_rollout_status("use_diversity_scoring")
        assert status["phase"] == "baseline_collection"
        
        # Advance to test users
        advance_rollout_phase("use_diversity_scoring")
        status = get_rollout_status("use_diversity_scoring")
        assert status["phase"] == "test_users"
        
        # Advance to full rollout
        advance_rollout_phase("use_diversity_scoring")
        status = get_rollout_status("use_diversity_scoring")
        assert status["phase"] == "full_rollloout"
        
        # Complete rollout
        advance_rollout_phase("use_diversity_scoring")
        status = get_rollout_status("use_diversity_scoring")
        assert status["phase"] == "completed"
        
        # Try to advance beyond completed
        result = advance_rollout_phase("use_diversity_scoring")
        assert result is False
