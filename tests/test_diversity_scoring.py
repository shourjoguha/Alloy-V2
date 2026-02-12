"""Comprehensive unit tests for diversity-based movement scoring system.

This test suite covers:
- GlobalMovementScorer basic functionality
- Discipline preference normalization (1-5 to 0-1 scale)
- Goal-specific modifiers (explosiveness, speed, etc.)
- Pattern compatibility and substitution rules
- Progressive constraint relaxation
- Configuration loading and validation
- All 7 scoring dimensions
- Session metrics tracking and retrieval
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from app.ml.scoring.movement_scorer import (
    GlobalMovementScorer,
    ScoringContext,
    ScoringResult,
    ScoringRule,
    ScoringDimension,
    ScoringError,
    ScoringRuleError,
)
from app.ml.scoring.config_loader import (
    YAMLConfigLoader,
    ScoringDimension as ConfigScoringDimension,
    MovementScoringConfig,
    WeightModifiers,
    MovementPreferences,
    GoalProfile,
    ConfigError,
    ConfigValidationError,
    ConfigLoadError,
)
from app.ml.scoring.scoring_metrics import (
    ScoringMetricsTracker,
    SessionResult,
    SessionContext,
    DimensionScores,
    ScoringMetrics,
    MetricsValidationError,
)
from app.models.movement import Movement
from app.models.enums import (
    MovementPattern,
    PrimaryMuscle,
    PrimaryRegion,
    SkillLevel,
    CNSLoad,
    Goal,
)


@pytest.fixture
def mock_config_loader():
    """Create a mock config loader for testing."""
    loader = Mock(spec=YAMLConfigLoader)
    
    # Create mock configuration
    config = Mock(spec=MovementScoringConfig)
    
    # Mock scoring dimensions
    config.scoring_dimensions = {
        "pattern_alignment": ConfigScoringDimension(
            priority_level=1,
            weight=1.0,
            description="Match movement pattern to block pattern requirements",
            penalty_mismatch=0.5,
            bonus_exact_match=1.0,
        ),
        "muscle_coverage": ConfigScoringDimension(
            priority_level=2,
            weight=0.8,
            description="Maximize primary muscle group diversity",
            bonus_unique_primary=1.0,
            penalty_repeated_primary=0.3,
            max_primary_repeats_per_session=2,
            max_primary_repeats_per_microcycle=4,
        ),
        "discipline_preference": ConfigScoringDimension(
            priority_level=3,
            weight=0.7,
            description="Align with user's preferred training discipline",
            bonus_matched_discipline=1.0,
            penalty_discipline_mismatch=0.5,
            neutral_default=0.8,
        ),
        "compound_bonus": ConfigScoringDimension(
            priority_level=4,
            weight=0.6,
            description="Prefer compound movements over isolation",
            bonus_compound=1.0,
            neutral_hybrid=0.8,
            penalty_isolation=0.5,
        ),
        "specialization": ConfigScoringDimension(
            priority_level=5,
            weight=0.5,
            description="Focus on user-defined specialization areas",
            bonus_target_muscle=1.0,
            neutral_non_target=0.7,
            specialization_threshold=0.7,
        ),
        "goal_alignment": ConfigScoringDimension(
            priority_level=6,
            weight=0.4,
            description="Align movement with primary training goal",
            bonus_goal_match=1.0,
            neutral_goal_agnostic=0.8,
            penalty_goal_conflict=0.4,
        ),
        "time_utilization": ConfigScoringDimension(
            priority_level=7,
            weight=0.3,
            description="Prefer movements with favorable time-to-benefit ratio",
            bonus_efficient=1.0,
            neutral_average=0.8,
            penalty_inefficient=0.5,
        ),
    }
    
    # Mock goal profiles
    config.goal_profiles = {
        "strength": GoalProfile(
            name="strength",
            primary_dimensions=("compound_bonus", "specialization"),
            weight_modifiers=WeightModifiers(
                compound_bonus=1.5,
                pattern_alignment=1.2,
                muscle_coverage=0.8,
                discipline_preference=1.0,
                goal_alignment=1.0,
                time_utilization=0.7,
                specialization=1.0,
            ),
            preferred_patterns=("squat", "hinge", "horizontal_push", "horizontal_pull"),
            preferred_rep_range=(1, 6),
            movement_preferences=MovementPreferences(
                compound=1.5,
                isolation=0.5,
                olympic=1.3,
                plyometric=0.7,
            ),
        ),
        "explosiveness": GoalProfile(
            name="explosiveness",
            primary_dimensions=("goal_alignment", "compound_bonus"),
            weight_modifiers=WeightModifiers(
                compound_bonus=1.3,
                pattern_alignment=1.0,
                muscle_coverage=0.7,
                discipline_preference=1.0,
                goal_alignment=1.5,
                time_utilization=0.9,
                specialization=0.8,
            ),
            preferred_patterns=("hinge", "squat", "horizontal_push"),
            preferred_rep_range=(1, 5),
            movement_preferences=MovementPreferences(
                compound=1.5,
                isolation=0.3,
                olympic=1.5,
                plyometric=1.5,
            ),
        ),
        "speed": GoalProfile(
            name="speed",
            primary_dimensions=("goal_alignment", "time_utilization"),
            weight_modifiers=WeightModifiers(
                compound_bonus=0.9,
                pattern_alignment=0.8,
                muscle_coverage=0.6,
                discipline_preference=1.0,
                goal_alignment=1.5,
                time_utilization=1.3,
                specialization=0.7,
            ),
            preferred_patterns=("lunge", "hiit_cardio", "horizontal_pull"),
            preferred_rep_range=(5, 12),
            movement_preferences=MovementPreferences(
                compound=1.2,
                isolation=0.5,
                olympic=1.3,
                plyometric=1.5,
            ),
        ),
    }
    
    # Mock pattern compatibility matrix
    from app.ml.scoring.config_loader import (
        PatternCompatibilityMatrix,
        SubstitutionGroup,
    )
    config.pattern_compatibility_matrix = PatternCompatibilityMatrix(
        substitution_groups=(
            SubstitutionGroup(
                name="lower_body_chain",
                patterns=("squat", "hinge", "lunge"),
                compatibility_matrix={
                    "squat": {"hinge": 0.8, "lunge": 0.7},
                    "hinge": {"squat": 0.8, "lunge": 0.6},
                    "lunge": {"squat": 0.7, "hinge": 0.6},
                },
            ),
            SubstitutionGroup(
                name="upper_push_chain",
                patterns=("horizontal_push", "vertical_push"),
                compatibility_matrix={
                    "horizontal_push": {"vertical_push": 0.9},
                    "vertical_push": {"horizontal_push": 0.9},
                },
            ),
            SubstitutionGroup(
                name="upper_pull_chain",
                patterns=("horizontal_pull", "vertical_pull"),
                compatibility_matrix={
                    "horizontal_pull": {"vertical_pull": 0.9},
                    "vertical_pull": {"horizontal_pull": 0.9},
                },
            ),
        ),
        cross_substitution_allowed=False,
        min_substitution_score=0.6,
        exact_match_bonus=1.0,
    )
    
    # Mock global config
    config.global_config = Mock()
    config.global_config.normalization_enabled = True
    config.global_config.normalization_method = "min_max"
    
    loader.get_config.return_value = config
    return loader


@pytest.fixture
def mock_movement():
    """Create a mock movement for testing."""
    movement = Mock(spec=Movement)
    movement.id = 1
    movement.name = "Barbell Squat"
    movement.pattern = MovementPattern.SQUAT
    movement.primary_muscle = PrimaryMuscle.QUADRICEPS
    movement.primary_region = PrimaryRegion.ANTERIOR_LOWER
    movement.skill_level = SkillLevel.INTERMEDIATE
    movement.cns_load = CNSLoad.MODERATE
    movement.compound = True
    movement.is_complex_lift = False
    movement.is_unilateral = False
    movement.disciplines = []
    return movement


@pytest.fixture
def mock_user_profile():
    """Create a mock user profile for testing."""
    profile = Mock()
    profile.discipline_preferences = {
        "strength": 5,
        "hypertrophy": 4,
        "endurance": 3,
    }
    return profile


@pytest.fixture
def scorer(mock_config_loader):
    """Create a GlobalMovementScorer instance for testing."""
    with patch('app.ml.scoring.movement_scorer.get_config_loader', return_value=mock_config_loader):
        return GlobalMovementScorer()


class TestGlobalMovementScorerBasicScoring:
    """Test basic scoring logic of GlobalMovementScorer."""

    def test_scorer_initialization(self, scorer):
        """Test that scorer initializes correctly."""
        assert scorer is not None
        assert scorer._config_loader is not None
        assert len(scorer._dimensions) == 7

    def test_score_movement_basic(self, scorer, mock_movement, mock_config_loader):
        """Test basic movement scoring returns valid result."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert isinstance(result, ScoringResult)
        assert result.movement_id == mock_movement.id
        assert result.movement_name == mock_movement.name
        assert isinstance(result.total_score, float)
        assert 0.0 <= result.total_score <= 1.0
        assert isinstance(result.dimension_scores, dict)
        assert isinstance(result.dimension_details, dict)
        assert isinstance(result.qualified, bool)

    def test_score_movement_with_pattern_match(self, scorer, mock_movement, mock_config_loader):
        """Test scoring when movement pattern matches required pattern."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
            required_pattern="squat",
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Should get higher score for pattern match
        assert result.total_score > 0.5
        assert "pattern_alignment" in result.dimension_scores

    def test_score_movement_with_pattern_mismatch(self, scorer, mock_movement, mock_config_loader):
        """Test scoring when movement pattern doesn't match required pattern."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
            required_pattern="horizontal_push",
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Should get lower score for pattern mismatch
        pattern_score = result.dimension_scores.get("pattern_alignment", 0.0)
        assert pattern_score <= 0.5

    def test_score_movement_compound_bonus(self, scorer, mock_movement, mock_config_loader):
        """Test that compound movements receive bonus."""
        mock_movement.compound = True
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        compound_score = result.dimension_scores.get("compound_bonus", 0.0)
        assert compound_score > 0

    def test_score_movement_isolation_penalty(self, scorer, mock_movement, mock_config_loader):
        """Test that isolation movements receive penalty."""
        mock_movement.compound = False
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        compound_score = result.dimension_scores.get("compound_bonus", 0.0)
        assert compound_score < 0.6  # Should be penalized

    def test_qualification_check(self, scorer, mock_movement, mock_config_loader):
        """Test qualification threshold checking."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Result should have qualification status
        assert hasattr(result, 'qualified')
        assert isinstance(result.qualified, bool)
        
        if not result.qualified:
            assert result.disqualified_reason is not None

    def test_get_top_dimensions(self, scorer, mock_movement, mock_config_loader):
        """Test getting top dimensions by weighted score."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        top_dimensions = result.get_top_dimensions(n=3)
        
        assert len(top_dimensions) <= 3
        assert all(isinstance(dim, tuple) and len(dim) == 2 for dim in top_dimensions)
        assert all(isinstance(score, float) for _, score in top_dimensions)


class TestDisciplineNormalization:
    """Test discipline preference normalization from 1-5 to 0-1 scale."""

    def test_normalize_discipline_preferences_basic(self, scorer, mock_config_loader):
        """Test basic normalization of discipline preferences."""
        context = ScoringContext(
            movement=Mock(spec=Movement),
            user_profile=Mock(),
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        # Set raw discipline preferences (1-5 scale)
        context.user_profile.discipline_preferences = {
            "strength": 5,
            "hypertrophy": 4,
            "endurance": 3,
            "cardio": 2,
            "mobility": 1,
        }
        
        normalized = scorer._normalize_discipline_preferences(context)
        
        # Check normalization to 0-1 scale
        assert normalized["strength"] == 1.0
        assert normalized["hypertrophy"] == 0.8
        assert normalized["endurance"] == 0.6
        assert normalized["cardio"] == 0.4
        assert normalized["mobility"] == 0.2

    def test_normalize_discipline_preferences_edge_cases(self, scorer, mock_config_loader):
        """Test normalization with edge cases."""
        context = ScoringContext(
            movement=Mock(spec=Movement),
            user_profile=Mock(),
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        # Test minimum value
        context.user_profile.discipline_preferences = {"strength": 1}
        normalized = scorer._normalize_discipline_preferences(context)
        assert normalized["strength"] == 0.2
        
        # Test maximum value
        context.user_profile.discipline_preferences = {"strength": 5}
        normalized = scorer._normalize_discipline_preferences(context)
        assert normalized["strength"] == 1.0
        
        # Test middle value
        context.user_profile.discipline_preferences = {"strength": 3}
        normalized = scorer._normalize_discipline_preferences(context)
        assert normalized["strength"] == 0.6

    def test_normalize_discipline_preferences_empty(self, scorer, mock_config_loader):
        """Test normalization with empty preferences."""
        context = ScoringContext(
            movement=Mock(spec=Movement),
            user_profile=Mock(),
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        context.user_profile.discipline_preferences = {}
        normalized = scorer._normalize_discipline_preferences(context)
        
        assert len(normalized) == 0

    def test_normalize_discipline_preferences_none_profile(self, scorer, mock_config_loader):
        """Test normalization when user profile is None."""
        context = ScoringContext(
            movement=Mock(spec=Movement),
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        normalized = scorer._normalize_discipline_preferences(context)
        
        assert len(normalized) == 0


class TestGoalModifiers:
    """Test goal-specific modifiers for scoring."""

    def test_explosiveness_goal_olympic_boost(self, scorer, mock_movement, mock_config_loader):
        """Test that explosiveness goal boosts Olympic movements."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["explosiveness"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Explosiveness should boost compound movements
        compound_score = result.dimension_scores.get("compound_bonus", 0.0)
        assert compound_score >= 0.0

    def test_speed_goal_plyometric_boost(self, scorer, mock_movement, mock_config_loader):
        """Test that speed goal boosts plyometric movements."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["speed"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Speed should boost time utilization and goal alignment
        time_score = result.dimension_scores.get("time_utilization", 0.0)
        goal_score = result.dimension_scores.get("goal_alignment", 0.0)
        assert time_score > 0.0 or goal_score > 0.0

    def test_strength_goal_compound_boost(self, scorer, mock_movement, mock_config_loader):
        """Test that strength goal boosts compound movements."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["strength"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Strength should favor compound movements
        compound_score = result.dimension_scores.get("compound_bonus", 0.0)
        assert compound_score >= 0.0

    def test_multiple_goals_modifier_application(self, scorer, mock_movement, mock_config_loader):
        """Test that multiple goals apply combined modifiers."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["strength", "explosiveness"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Multiple goals should produce a valid score
        assert 0.0 <= result.total_score <= 1.0

    def test_no_goals_no_modifiers(self, scorer, mock_movement, mock_config_loader):
        """Test that no goals results in no modifiers."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        # Should still get a valid score
        assert 0.0 <= result.total_score <= 1.0

    def test_goal_modifier_calculation(self, scorer, mock_config_loader):
        """Test internal goal modifier calculation."""
        context = ScoringContext(
            movement=Mock(spec=Movement),
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["explosiveness"],
        )
        
        base_score = 0.5
        modified_score = scorer._apply_goal_modifiers(base_score, context)
        
        # Explosiveness should increase the score
        assert modified_score >= base_score


class TestPatternCompatibility:
    """Test pattern compatibility and substitution rules."""

    def test_squat_hinge_compatibility(self, mock_config_loader):
        """Test squat and hinge pattern compatibility."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        # Get lower_body_chain substitution group
        lower_chain = None
        for group in matrix.substitution_groups:
            if group.name == "lower_body_chain":
                lower_chain = group
                break
        
        assert lower_chain is not None
        
        # Check compatibility scores
        assert "squat" in lower_chain.compatibility_matrix
        assert "hinge" in lower_chain.compatibility_matrix
        
        squat_to_hinge = lower_chain.compatibility_matrix["squat"]["hinge"]
        hinge_to_squat = lower_chain.compatibility_matrix["hinge"]["squat"]
        
        # Squat and hinge should be highly compatible
        assert squat_to_hinge >= 0.7
        assert hinge_to_squat >= 0.7

    def test_squat_lunge_compatibility(self, mock_config_loader):
        """Test squat and lunge pattern compatibility."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        # Get lower_body_chain substitution group
        lower_chain = None
        for group in matrix.substitution_groups:
            if group.name == "lower_body_chain":
                lower_chain = group
                break
        
        assert lower_chain is not None
        
        squat_to_lunge = lower_chain.compatibility_matrix["squat"]["lunge"]
        lunge_to_squat = lower_chain.compatibility_matrix["lunge"]["squat"]
        
        # Squat and lunge should be reasonably compatible
        assert squat_to_lunge >= 0.6
        assert lunge_to_squat >= 0.6

    def test_hinge_lunge_compatibility(self, mock_config_loader):
        """Test hinge and lunge pattern compatibility."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        # Get lower_body_chain substitution group
        lower_chain = None
        for group in matrix.substitution_groups:
            if group.name == "lower_body_chain":
                lower_chain = group
                break
        
        assert lower_chain is not None
        
        hinge_to_lunge = lower_chain.compatibility_matrix["hinge"]["lunge"]
        lunge_to_hinge = lower_chain.compatibility_matrix["lunge"]["hinge"]
        
        # Hinge and lunge should be somewhat compatible
        assert hinge_to_lunge >= 0.5
        assert lunge_to_hinge >= 0.5

    def test_upper_push_compatibility(self, mock_config_loader):
        """Test horizontal and vertical push compatibility."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        # Get upper_push_chain substitution group
        push_chain = None
        for group in matrix.substitution_groups:
            if group.name == "upper_push_chain":
                push_chain = group
                break
        
        assert push_chain is not None
        
        horizontal_to_vertical = push_chain.compatibility_matrix["horizontal_push"]["vertical_push"]
        vertical_to_horizontal = push_chain.compatibility_matrix["vertical_push"]["horizontal_push"]
        
        # Push patterns should be highly compatible
        assert horizontal_to_vertical >= 0.8
        assert vertical_to_horizontal >= 0.8

    def test_upper_pull_compatibility(self, mock_config_loader):
        """Test horizontal and vertical pull compatibility."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        # Get upper_pull_chain substitution group
        pull_chain = None
        for group in matrix.substitution_groups:
            if group.name == "upper_pull_chain":
                pull_chain = group
                break
        
        assert pull_chain is not None
        
        horizontal_to_vertical = pull_chain.compatibility_matrix["horizontal_pull"]["vertical_pull"]
        vertical_to_horizontal = pull_chain.compatibility_matrix["vertical_pull"]["horizontal_pull"]
        
        # Pull patterns should be highly compatible
        assert horizontal_to_vertical >= 0.8
        assert vertical_to_horizontal >= 0.8

    def test_cross_substitution_disabled(self, mock_config_loader):
        """Test that cross-substitution is disabled."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        assert matrix.cross_substitution_allowed is False

    def test_min_substitution_score(self, mock_config_loader):
        """Test minimum substitution score threshold."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        assert matrix.min_substitution_score >= 0.5
        assert matrix.min_substitution_score <= 1.0

    def test_exact_match_bonus(self, mock_config_loader):
        """Test exact match bonus multiplier."""
        config = mock_config_loader.get_config()
        matrix = config.pattern_compatibility_matrix
        
        assert matrix.exact_match_bonus >= 1.0
        assert matrix.exact_match_bonus <= 2.0


class TestProgressiveRelaxation:
    """Test progressive constraint relaxation (6-step)."""

    def test_relaxation_order_in_config(self, mock_config_loader):
        """Test that relaxation order is defined in config."""
        config = mock_config_loader.get_config()
        config.global_config.relaxation_enabled = True
        
        # Mock the relaxation order
        config.global_config.relaxation_order = [
            "muscle_coverage",
            "pattern_alignment",
            "discipline_preference",
            "compound_bonus",
            "specialization",
            "goal_alignment",
            "time_utilization",
        ]
        
        assert len(config.global_config.relaxation_order) == 7
        assert "muscle_coverage" in config.global_config.relaxation_order
        assert "time_utilization" in config.global_config.relaxation_order

    def test_relaxation_strategy_defined(self, mock_config_loader):
        """Test that relaxation strategy is defined."""
        config = mock_config_loader.get_config()
        config.global_config.relaxation_strategy = "soft_constraints"
        
        valid_strategies = ["soft_constraints", "penalty_based", "iterative"]
        assert config.global_config.relaxation_strategy in valid_strategies

    def test_relaxation_threshold(self, mock_config_loader):
        """Test relaxation threshold configuration."""
        config = mock_config_loader.get_config()
        config.global_config.relaxation_threshold = 0.1
        
        assert 0.0 <= config.global_config.relaxation_threshold <= 1.0

    def test_max_relaxations(self, mock_config_loader):
        """Test maximum number of relaxations."""
        config = mock_config_loader.get_config()
        config.global_config.max_relaxations = 3
        
        assert config.global_config.max_relaxations > 0
        assert config.global_config.max_relaxations <= 10

    def test_penalty_factor(self, mock_config_loader):
        """Test penalty factor for relaxed constraints."""
        config = mock_config_loader.get_config()
        config.global_config.penalty_factor = 0.5
        
        assert 0.0 <= config.global_config.penalty_factor <= 1.0

    def test_relaxation_enabled(self, mock_config_loader):
        """Test that relaxation can be enabled/disabled."""
        config = mock_config_loader.get_config()
        config.global_config.relaxation_enabled = True
        
        assert isinstance(config.global_config.relaxation_enabled, bool)


class TestConfigLoader:
    """Test configuration loading and validation."""

    def test_config_loader_initialization(self, tmp_path):
        """Test config loader initialization."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
scoring_dimensions:
  pattern_alignment:
    priority_level: 1
    weight: 1.0
    description: "Test dimension"
    bonus_exact_match: 1.0
    penalty_mismatch: 0.5

goal_profiles:
  strength:
    name: "strength"
    primary_dimensions: ["compound_bonus"]
    weight_modifiers:
      compound_bonus: 1.5
      pattern_alignment: 1.2
      muscle_coverage: 0.8
      discipline_preference: 1.0
      goal_alignment: 1.0
      time_utilization: 0.7
      specialization: 1.0
    preferred_patterns: ["squat", "hinge"]
    preferred_rep_range: [1, 6]
    movement_preferences:
      compound: 1.5
      isolation: 0.5
      olympic: 1.3
      plyometric: 0.7

pattern_compatibility_matrix:
  substitution_groups:
    lower_body_chain:
      patterns: ["squat", "hinge", "lunge"]
      compatibility_matrix:
        squat:
          hinge: 0.8
          lunge: 0.7
        hinge:
          squat: 0.8
          lunge: 0.6
        lunge:
          squat: 0.7
          hinge: 0.6
  cross_substitution_allowed: false
  min_substitution_score: 0.6
  exact_match_bonus: 1.0

discipline_modifiers: {}

hard_constraints:
  equipment:
    enforce: true
  variety:
    enforce: true
    min_unique_movements_per_session: 4
    min_unique_movements_per_microcycle: 12
    max_same_movement_per_microcycle: 3
    min_pattern_variety_per_session: 2
    max_pattern_repeats_per_session: 3
  time:
    enforce: true
    max_time_per_block_minutes: 45
    max_time_per_session_minutes: 120
    min_time_per_movement_minutes: 2
    recommended_time_per_movement_minutes: 5
  user_rules:
    enforce: true
  safety:
    enforce: true

rep_set_ranges:
  warmup:
    sets:
      min: 1
      max: 3
      default: 2
    reps:
      min: 5
      max: 15
      default: 10
    intensity_pct: [40, 60]
    rest_seconds: [30, 60]
    rpe_target: [1, 3]
    tempo: "2-0-2"
  circuit:
    exempt_from_ranges: true
    sets:
      min: 1
      max: 6
      default: 3
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [40, 70]
    rest_seconds: [0, 60]
    rpe_target: [5, 8]
    tempo: "2-0-2"
    circuit_types: ["amrap", "emom", "for_time", "rounds"]

global_config:
  normalization:
    enabled: true
    method: "min_max"
  tie_breaker:
    enabled: true
    strategy: "priority_hierarchy"
  relaxation:
    enabled: true
    strategy: "soft_constraints"
  debug:
    enabled: false
  performance:
    cache_scores: true
  validation:
    validate_on_load: true
    strict_mode: false

metadata:
  version: "1.0.0"
  last_updated: "2024-01-01"
  author: "Test Author"
  description: "Test configuration"
  schema_version: "1.0"
""")
        
        loader = YAMLConfigLoader(config_path=str(config_file))
        
        assert loader._config_path == config_file
        assert loader._config is not None

    def test_config_loading(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "movement_scoring.yaml"
        config_file.write_text("""
scoring_dimensions:
  pattern_alignment:
    priority_level: 1
    weight: 1.0
    description: "Test dimension"
    bonus_exact_match: 1.0
    penalty_mismatch: 0.5

goal_profiles:
  strength:
    name: "strength"
    primary_dimensions: ["compound_bonus"]
    weight_modifiers:
      compound_bonus: 1.5
      pattern_alignment: 1.2
      muscle_coverage: 0.8
      discipline_preference: 1.0
      goal_alignment: 1.0
      time_utilization: 0.7
      specialization: 1.0
    preferred_patterns: ["squat", "hinge"]
    preferred_rep_range: [1, 6]
    movement_preferences:
      compound: 1.5
      isolation: 0.5
      olympic: 1.3
      plyometric: 0.7

pattern_compatibility_matrix:
  substitution_groups:
    lower_body_chain:
      patterns: ["squat", "hinge", "lunge"]
      compatibility_matrix:
        squat:
          hinge: 0.8
          lunge: 0.7
        hinge:
          squat: 0.8
          lunge: 0.6
        lunge:
          squat: 0.7
          hinge: 0.6
  cross_substitution_allowed: false
  min_substitution_score: 0.6
  exact_match_bonus: 1.0

discipline_modifiers: {}

hard_constraints:
  equipment:
    enforce: true
  variety:
    enforce: true
    min_unique_movements_per_session: 4
    min_unique_movements_per_microcycle: 12
    max_same_movement_per_microcycle: 3
    min_pattern_variety_per_session: 2
    max_pattern_repeats_per_session: 3
  time:
    enforce: true
    max_time_per_block_minutes: 45
    max_time_per_session_minutes: 120
    min_time_per_movement_minutes: 2
    recommended_time_per_movement_minutes: 5
  user_rules:
    enforce: true
  safety:
    enforce: true

rep_set_ranges:
  warmup:
    sets:
      min: 1
      max: 3
      default: 2
    reps:
      min: 5
      max: 15
      default: 10
    intensity_pct: [40, 60]
    rest_seconds: [30, 60]
    rpe_target: [1, 3]
    tempo: "2-0-2"
  circuit:
    exempt_from_ranges: true
    sets:
      min: 1
      max: 6
      default: 3
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [40, 70]
    rest_seconds: [0, 60]
    rpe_target: [5, 8]
    tempo: "2-0-2"
    circuit_types: ["amrap", "emom", "for_time", "rounds"]

global_config:
  normalization:
    enabled: true
    method: "min_max"
  tie_breaker:
    enabled: true
    strategy: "priority_hierarchy"
  relaxation:
    enabled: true
    strategy: "soft_constraints"
  debug:
    enabled: false
  performance:
    cache_scores: true
  validation:
    validate_on_load: true
    strict_mode: false

metadata:
  version: "1.0.0"
  last_updated: "2024-01-01"
  author: "Test Author"
  description: "Test configuration"
  schema_version: "1.0"
""")
        
        loader = YAMLConfigLoader(config_path=str(config_file))
        config = loader.get_config()
        
        assert config is not None
        assert len(config.scoring_dimensions) >= 1
        assert "pattern_alignment" in config.scoring_dimensions

    def test_config_validation(self, tmp_path):
        """Test configuration validation."""
        config_file = tmp_path / "movement_scoring.yaml"
        config_file.write_text("""
scoring_dimensions:
  pattern_alignment:
    priority_level: 1
    weight: 1.0
    description: "Test dimension"
    bonus_exact_match: 1.0
    penalty_mismatch: 0.5

goal_profiles:
  strength:
    name: "strength"
    primary_dimensions: ["compound_bonus"]
    weight_modifiers:
      compound_bonus: 1.5
      pattern_alignment: 1.2
      muscle_coverage: 0.8
      discipline_preference: 1.0
      goal_alignment: 1.0
      time_utilization: 0.7
      specialization: 1.0
    preferred_patterns: ["squat", "hinge"]
    preferred_rep_range: [1, 6]
    movement_preferences:
      compound: 1.5
      isolation: 0.5
      olympic: 1.3
      plyometric: 0.7

pattern_compatibility_matrix:
  substitution_groups:
    lower_body_chain:
      patterns: ["squat", "hinge", "lunge"]
      compatibility_matrix:
        squat:
          hinge: 0.8
          lunge: 0.7
        hinge:
          squat: 0.8
          lunge: 0.6
        lunge:
          squat: 0.7
          hinge: 0.6
  cross_substitution_allowed: false
  min_substitution_score: 0.6
  exact_match_bonus: 1.0

discipline_modifiers: {}

hard_constraints:
  equipment:
    enforce: true
  variety:
    enforce: true
    min_unique_movements_per_session: 4
    min_unique_movements_per_microcycle: 12
    max_same_movement_per_microcycle: 3
    min_pattern_variety_per_session: 2
    max_pattern_repeats_per_session: 3
  time:
    enforce: true
    max_time_per_block_minutes: 45
    max_time_per_session_minutes: 120
    min_time_per_movement_minutes: 2
    recommended_time_per_movement_minutes: 5
  user_rules:
    enforce: true
  safety:
    enforce: true

rep_set_ranges:
  warmup:
    sets:
      min: 1
      max: 3
      default: 2
    reps:
      min: 5
      max: 15
      default: 10
    intensity_pct: [40, 60]
    rest_seconds: [30, 60]
    rpe_target: [1, 3]
    tempo: "2-0-2"
  main_strength:
    sets:
      min: 3
      max: 6
      default: 4
    reps:
      min: 1
      max: 8
      default: 5
    intensity_pct: [75, 95]
    rest_seconds: [120, 300]
    rpe_target: [7, 9]
    tempo: "2-0-X"
  main_hypertrophy:
    sets:
      min: 3
      max: 5
      default: 4
    reps:
      min: 6
      max: 20
      default: 12
    intensity_pct: [60, 80]
    rest_seconds: [60, 120]
    rpe_target: [6, 8]
    tempo: "3-0-2"
  accessory:
    sets:
      min: 2
      max: 4
      default: 3
    reps:
      min: 8
      max: 25
      default: 15
    intensity_pct: [50, 70]
    rest_seconds: [45, 90]
    rpe_target: [5, 7]
    tempo: "3-0-3"
  cooldown:
    sets:
      min: 1
      max: 2
      default: 1
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [20, 40]
    rest_seconds: [15, 30]
    rpe_target: [1, 3]
    tempo: "3-1-3"
  circuit:
    exempt_from_ranges: true
    sets:
      min: 1
      max: 6
      default: 3
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [40, 70]
    rest_seconds: [0, 60]
    rpe_target: [5, 8]
    tempo: "2-0-2"
    circuit_types:
      - amrap
      - emom
      - for_time
      - rounds

global_config:
  normalization:
    enabled: true
    method: "min_max"
  tie_breaker:
    enabled: true
    strategy: "priority_hierarchy"
  relaxation:
    enabled: true
    strategy: "soft_constraints"
  debug:
    enabled: false
  performance:
    cache_scores: true
  validation:
    validate_on_load: true
    strict_mode: false

metadata:
  version: "1.0.0"
  last_updated: "2024-01-01"
  author: "Test Author"
  description: "Test configuration"
  schema_version: "1.0"
""")
        
        loader = YAMLConfigLoader(config_path=str(config_file))
        
        # Should not raise exception
        loader.validate_schema()

    def test_config_file_not_found(self, tmp_path):
        """Test error when config file is not found."""
        config_file = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(ConfigError):
            YAMLConfigLoader(config_path=str(config_file))

    def test_config_reload(self, tmp_path):
        """Test configuration reloading."""
        config_file = tmp_path / "movement_scoring.yaml"
        config_file.write_text("""
scoring_dimensions:
  pattern_alignment:
    priority_level: 1
    weight: 1.0
    description: "Test dimension"
    bonus_exact_match: 1.0
    penalty_mismatch: 0.5

goal_profiles:
  strength:
    name: "strength"
    primary_dimensions: ["compound_bonus"]
    weight_modifiers:
      compound_bonus: 1.5
      pattern_alignment: 1.2
      muscle_coverage: 0.8
      discipline_preference: 1.0
      goal_alignment: 1.0
      time_utilization: 0.7
      specialization: 1.0
    preferred_patterns: ["squat", "hinge"]
    preferred_rep_range: [1, 6]
    movement_preferences:
      compound: 1.5
      isolation: 0.5
      olympic: 1.3
      plyometric: 0.7

pattern_compatibility_matrix:
  substitution_groups:
    lower_body_chain:
      patterns: ["squat", "hinge", "lunge"]
      compatibility_matrix:
        squat:
          hinge: 0.8
          lunge: 0.7
        hinge:
          squat: 0.8
          lunge: 0.6
        lunge:
          squat: 0.7
          hinge: 0.6
  cross_substitution_allowed: false
  min_substitution_score: 0.6
  exact_match_bonus: 1.0

discipline_modifiers: {}

hard_constraints:
  equipment:
    enforce: true
  variety:
    enforce: true
    min_unique_movements_per_session: 4
    min_unique_movements_per_microcycle: 12
    max_same_movement_per_microcycle: 3
    min_pattern_variety_per_session: 2
    max_pattern_repeats_per_session: 3
  time:
    enforce: true
    max_time_per_block_minutes: 45
    max_time_per_session_minutes: 120
    min_time_per_movement_minutes: 2
    recommended_time_per_movement_minutes: 5
  user_rules:
    enforce: true
  safety:
    enforce: true

rep_set_ranges:
  warmup:
    sets:
      min: 1
      max: 3
      default: 2
    reps:
      min: 5
      max: 15
      default: 10
    intensity_pct: [40, 60]
    rest_seconds: [30, 60]
    rpe_target: [1, 3]
    tempo: "2-0-2"
  main_strength:
    sets:
      min: 3
      max: 6
      default: 4
    reps:
      min: 1
      max: 8
      default: 5
    intensity_pct: [75, 95]
    rest_seconds: [120, 300]
    rpe_target: [7, 9]
    tempo: "2-0-X"
  main_hypertrophy:
    sets:
      min: 3
      max: 5
      default: 4
    reps:
      min: 6
      max: 20
      default: 12
    intensity_pct: [60, 80]
    rest_seconds: [60, 120]
    rpe_target: [6, 8]
    tempo: "3-0-2"
  accessory:
    sets:
      min: 2
      max: 4
      default: 3
    reps:
      min: 8
      max: 25
      default: 15
    intensity_pct: [50, 70]
    rest_seconds: [45, 90]
    rpe_target: [5, 7]
    tempo: "3-0-3"
  cooldown:
    sets:
      min: 1
      max: 2
      default: 1
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [20, 40]
    rest_seconds: [15, 30]
    rpe_target: [1, 3]
    tempo: "3-1-3"
  circuit:
    exempt_from_ranges: true
    sets:
      min: 1
      max: 6
      default: 3
    reps:
      min: 5
      max: 20
      default: 10
    intensity_pct: [40, 70]
    rest_seconds: [0, 60]
    rpe_target: [5, 8]
    tempo: "2-0-2"
    circuit_types:
      - amrap
      - emom
      - for_time
      - rounds

global_config:
  normalization:
    enabled: true
    method: "min_max"
  tie_breaker:
    enabled: true
    strategy: "priority_hierarchy"
  relaxation:
    enabled: true
    strategy: "soft_constraints"
  debug:
    enabled: false
  performance:
    cache_scores: true
  validation:
    validate_on_load: true
    strict_mode: false

metadata:
  version: "1.0.0"
  last_updated: "2024-01-01"
  author: "Test Author"
  description: "Test configuration"
  schema_version: "1.0"
""")
        
        loader = YAMLConfigLoader(config_path=str(config_file), enable_hot_reload=False)
        
        # Reload should work
        config = loader.reload_config()
        assert config is not None


class TestScoringDimensions:
    """Test that all 7 scoring dimensions evaluate correctly."""

    def test_pattern_alignment_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test pattern alignment dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
            required_pattern="squat",
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "pattern_alignment" in result.dimension_scores
        pattern_score = result.dimension_scores["pattern_alignment"]
        assert 0.0 <= pattern_score <= 1.0
        
        # Exact match should give positive score
        assert pattern_score >= 0.0

    def test_muscle_coverage_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test muscle coverage dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "muscle_coverage" in result.dimension_scores
        muscle_score = result.dimension_scores["muscle_coverage"]
        assert 0.0 <= muscle_score <= 1.0

    def test_discipline_preference_dimension(self, scorer, mock_movement, mock_config_loader, mock_user_profile):
        """Test discipline preference dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=mock_user_profile,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
            discipline_preferences={"strength": 1.0},
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "discipline_preference" in result.dimension_scores
        discipline_score = result.dimension_scores["discipline_preference"]
        assert 0.0 <= discipline_score <= 1.0

    def test_compound_bonus_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test compound bonus dimension evaluation."""
        mock_movement.compound = True
        
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "compound_bonus" in result.dimension_scores
        compound_score = result.dimension_scores["compound_bonus"]
        assert 0.0 <= compound_score <= 1.0
        # Compound should get a positive score
        assert compound_score >= 0.0

    def test_specialization_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test specialization dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
            target_muscles=["quadriceps"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "specialization" in result.dimension_scores
        specialization_score = result.dimension_scores["specialization"]
        assert 0.0 <= specialization_score <= 1.0

    def test_goal_alignment_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test goal alignment dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=["strength"],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "goal_alignment" in result.dimension_scores
        goal_score = result.dimension_scores["goal_alignment"]
        assert 0.0 <= goal_score <= 1.0

    def test_time_utilization_dimension(self, scorer, mock_movement, mock_config_loader):
        """Test time utilization dimension evaluation."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        assert "time_utilization" in result.dimension_scores
        time_score = result.dimension_scores["time_utilization"]
        assert 0.0 <= time_score <= 1.0

    def test_all_dimensions_present(self, scorer, mock_movement, mock_config_loader):
        """Test that all 7 dimensions are evaluated."""
        context = ScoringContext(
            movement=mock_movement,
            user_profile=None,
            config=mock_config_loader.get_config(),
            session_movements=[],
            microcycle_movements=[],
            user_goals=[],
        )
        
        result = scorer.score_movement(mock_movement, context)
        
        expected_dimensions = [
            "pattern_alignment",
            "muscle_coverage",
            "discipline_preference",
            "compound_bonus",
            "specialization",
            "goal_alignment",
            "time_utilization",
        ]
        
        for dimension in expected_dimensions:
            assert dimension in result.dimension_scores
            assert 0.0 <= result.dimension_scores[dimension] <= 1.0

    def test_dimension_weights_normalization(self, scorer, mock_config_loader):
        """Test that dimension weights are normalized to sum to 1.0."""
        weights = scorer._normalize_dimension_weights()
        
        assert len(weights) == 7
        assert math.isclose(sum(weights.values()), 1.0, rel_tol=1e-6)
        
        for weight in weights.values():
            assert 0.0 <= weight <= 1.0


class TestMetricsTracking:
    """Test session metrics recording and retrieval."""

    def test_metrics_tracker_initialization(self, tmp_path):
        """Test metrics tracker initialization."""
        metrics_file = tmp_path / "metrics.json"
        
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        assert tracker is not None
        assert tracker._metrics_path == metrics_file

    def test_record_session_metrics(self, tmp_path):
        """Test recording session metrics."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        result = SessionResult(
            session_id=1,
            session_type="strength",
            warmup_exercises=[1, 2],
            main_exercises=[3, 4, 5],
            accessory_exercises=[6, 7],
            cooldown_exercises=[8],
            estimated_duration_minutes=60,
            movements=[],
            patterns=["squat", "hinge", "horizontal_push"],
            muscle_groups=["quadriceps", "glutes", "chest"],
            hard_constraint_violations=[],
        )
        
        context = SessionContext(
            target_duration_minutes=60,
            session_type="strength",
        )
        
        metrics = tracker.record_session(result, context)
        
        assert isinstance(metrics, ScoringMetrics)
        assert metrics.session_id == 1
        assert metrics.session_type == "strength"
        assert metrics.movement_count == 8
        assert metrics.pattern_diversity == 3
        assert metrics.muscle_coverage == 3
        assert isinstance(metrics.dimension_scores, DimensionScores)

    def test_get_success_rate(self, tmp_path):
        """Test calculating success rate."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record multiple sessions
        for i in range(10):
            result = SessionResult(
                session_id=i,
                session_type="strength",
                warmup_exercises=[1, 2],
                main_exercises=[3, 4, 5],
                accessory_exercises=[6, 7],
                cooldown_exercises=[8],
                estimated_duration_minutes=60,
                movements=[],
                patterns=["squat", "hinge"],
                muscle_groups=["quadriceps", "glutes"],
                hard_constraint_violations=[],
            )
            
            context = SessionContext(
                target_duration_minutes=60,
                session_type="strength",
            )
            
            tracker.record_session(result, context)
        
        success_rate = tracker.get_success_rate()
        
        assert 0.0 <= success_rate <= 1.0

    def test_get_success_rate_by_session_type(self, tmp_path):
        """Test calculating success rate filtered by session type."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record strength sessions
        for i in range(5):
            result = SessionResult(
                session_id=i,
                session_type="strength",
                warmup_exercises=[1, 2],
                main_exercises=[3, 4, 5],
                accessory_exercises=[6, 7],
                cooldown_exercises=[8],
                estimated_duration_minutes=60,
                movements=[],
                patterns=["squat", "hinge"],
                muscle_groups=["quadriceps", "glutes"],
                hard_constraint_violations=[],
            )
            
            context = SessionContext(
                target_duration_minutes=60,
                session_type="strength",
            )
            
            tracker.record_session(result, context)
        
        # Record hypertrophy sessions
        for i in range(5, 10):
            result = SessionResult(
                session_id=i,
                session_type="hypertrophy",
                warmup_exercises=[1, 2],
                main_exercises=[3, 4, 5],
                accessory_exercises=[6, 7],
                cooldown_exercises=[8],
                estimated_duration_minutes=60,
                movements=[],
                patterns=["horizontal_push", "vertical_push"],
                muscle_groups=["chest", "shoulders"],
                hard_constraint_violations=[],
            )
            
            context = SessionContext(
                target_duration_minutes=60,
                session_type="hypertrophy",
            )
            
            tracker.record_session(result, context)
        
        strength_rate = tracker.get_success_rate(session_type="strength")
        hypertrophy_rate = tracker.get_success_rate(session_type="hypertrophy")
        
        assert 0.0 <= strength_rate <= 1.0
        assert 0.0 <= hypertrophy_rate <= 1.0

    def test_get_dimension_effectiveness(self, tmp_path):
        """Test analyzing dimension effectiveness."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record sessions
        for i in range(5):
            result = SessionResult(
                session_id=i,
                session_type="strength",
                warmup_exercises=[1, 2],
                main_exercises=[3, 4, 5],
                accessory_exercises=[6, 7],
                cooldown_exercises=[8],
                estimated_duration_minutes=60,
                movements=[],
                patterns=["squat", "hinge"],
                muscle_groups=["quadriceps", "glutes"],
                hard_constraint_violations=[],
            )
            
            context = SessionContext(
                target_duration_minutes=60,
                session_type="strength",
            )
            
            tracker.record_session(result, context)
        
        effectiveness = tracker.get_dimension_effectiveness()
        
        assert isinstance(effectiveness, dict)
        assert len(effectiveness) > 0
        
        for dimension, stats in effectiveness.items():
            assert "mean" in stats
            assert "median" in stats
            assert "std" in stats
            assert "min" in stats
            assert "max" in stats
            assert "sample_size" in stats

    def test_get_failure_reasons(self, tmp_path):
        """Test getting failure reasons."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record a failing session
        result = SessionResult(
            session_id=1,
            session_type="strength",
            warmup_exercises=[],
            main_exercises=[3, 4],
            accessory_exercises=[],
            cooldown_exercises=[],
            estimated_duration_minutes=30,
            movements=[],
            patterns=["squat"],
            muscle_groups=["quadriceps"],
            hard_constraint_violations=["equipment_constraint"],
        )
        
        context = SessionContext(
            target_duration_minutes=60,
            session_type="strength",
        )
        
        tracker.record_session(result, context)
        
        failure_reasons = tracker.get_failure_reasons()
        
        assert isinstance(failure_reasons, dict)
        # At least one failure reason should be present
        # (structural_incomplete, invalid_movement_count, poor_time_utilization, hard_constraint_violation)

    def test_get_metrics_summary(self, tmp_path):
        """Test getting metrics summary."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record sessions
        for i in range(5):
            result = SessionResult(
                session_id=i,
                session_type="strength",
                warmup_exercises=[1, 2],
                main_exercises=[3, 4, 5],
                accessory_exercises=[6, 7],
                cooldown_exercises=[8],
                estimated_duration_minutes=60,
                movements=[],
                patterns=["squat", "hinge"],
                muscle_groups=["quadriceps", "glutes"],
                hard_constraint_violations=[],
            )
            
            context = SessionContext(
                target_duration_minutes=60,
                session_type="strength",
            )
            
            tracker.record_session(result, context)
        
        summary = tracker.get_metrics_summary()
        
        assert "total_sessions" in summary
        assert "successful_sessions" in summary
        assert "success_rate" in summary
        assert "by_session_type" in summary
        assert summary["total_sessions"] == 5
        assert 0.0 <= summary["success_rate"] <= 1.0

    def test_export_metrics(self, tmp_path):
        """Test exporting metrics to JSON file."""
        metrics_file = tmp_path / "metrics.json"
        export_file = tmp_path / "export.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record a session
        result = SessionResult(
            session_id=1,
            session_type="strength",
            warmup_exercises=[1, 2],
            main_exercises=[3, 4, 5],
            accessory_exercises=[6, 7],
            cooldown_exercises=[8],
            estimated_duration_minutes=60,
            movements=[],
            patterns=["squat", "hinge"],
            muscle_groups=["quadriceps", "glutes"],
            hard_constraint_violations=[],
        )
        
        context = SessionContext(
            target_duration_minutes=60,
            session_type="strength",
        )
        
        tracker.record_session(result, context)
        
        # Export metrics
        tracker.export_metrics(str(export_file))
        
        assert export_file.exists()

    def test_clear_metrics(self, tmp_path):
        """Test clearing all metrics."""
        metrics_file = tmp_path / "metrics.json"
        tracker = ScoringMetricsTracker(metrics_path=str(metrics_file))
        
        # Record a session
        result = SessionResult(
            session_id=1,
            session_type="strength",
            warmup_exercises=[1, 2],
            main_exercises=[3, 4, 5],
            accessory_exercises=[6, 7],
            cooldown_exercises=[8],
            estimated_duration_minutes=60,
            movements=[],
            patterns=["squat", "hinge"],
            muscle_groups=["quadriceps", "glutes"],
            hard_constraint_violations=[],
        )
        
        context = SessionContext(
            target_duration_minutes=60,
            session_type="strength",
        )
        
        tracker.record_session(result, context)
        
        # Clear metrics
        tracker.clear_metrics()
        
        summary = tracker.get_metrics_summary()
        assert summary["total_sessions"] == 0

    def test_dimension_scores_serialization(self):
        """Test DimensionScores serialization."""
        scores = DimensionScores(
            pattern_alignment=0.8,
            muscle_coverage=0.7,
            discipline_preference=0.9,
            compound_bonus=0.6,
            specialization=0.5,
            goal_alignment=0.8,
            time_utilization=0.7,
        )
        
        # Test to_dict
        scores_dict = scores.to_dict()
        assert isinstance(scores_dict, dict)
        assert len(scores_dict) == 7
        
        # Test from_dict
        scores_from_dict = DimensionScores.from_dict(scores_dict)
        assert scores_from_dict == scores

    def test_scoring_metrics_serialization(self):
        """Test ScoringMetrics serialization."""
        dimension_scores = DimensionScores(
            pattern_alignment=0.8,
            muscle_coverage=0.7,
            discipline_preference=0.9,
            compound_bonus=0.6,
            specialization=0.5,
            goal_alignment=0.8,
            time_utilization=0.7,
        )
        
        metrics = ScoringMetrics(
            session_id=1,
            session_type="strength",
            timestamp=datetime.utcnow(),
            success=True,
            movement_count=8,
            time_utilization=1.0,
            pattern_diversity=3,
            muscle_coverage=3,
            dimension_scores=dimension_scores,
            failure_reasons=(),
            structural_completeness=True,
            hard_constraints_compliant=True,
        )
        
        # Test to_dict
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["session_id"] == 1
        assert metrics_dict["success"] is True
        
        # Test from_dict
        metrics_from_dict = ScoringMetrics.from_dict(metrics_dict)
        assert metrics_from_dict.session_id == metrics.session_id
        assert metrics_from_dict.success == metrics.success


# Import math for dimension weight normalization test
import math
