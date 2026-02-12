"""Constants for scoring KPI validation.

This module centralizes all magic numbers, thresholds, and configuration
constants used across KPI validation modules. It provides a single source
of truth for scoring-related constants to improve maintainability and
reduce duplication.

Constants are organized by functional area:
- Time utilization: Tolerances and thresholds for session duration
- Movement counts: Min/max values for blocks and sessions
- Scoring thresholds: Quality and qualification thresholds
- Session types: Categories and classifications
- Scoring dimensions: Names and weights
- Coverage thresholds: Minimum percentages for various metrics
"""

from __future__ import annotations

# =============================================================================
# Time Utilization Constants
# =============================================================================

class TimeUtilization:
    """Time utilization validation constants.

    These constants define acceptable ranges for session duration
    relative to target duration.
    """

    TOLERANCE_PERCENT = 0.05  # 5% tolerance for time utilization
    TOLERANCE_PERCENT_DECIMAL = 0.05  # Same as above, for clarity

    @staticmethod
    def is_within_tolerance(actual: float, target: float) -> bool:
        """Check if actual time is within tolerance of target.

        Args:
            actual: Actual duration in minutes
            target: Target duration in minutes

        Returns:
            True if within 5% tolerance, False otherwise
        """
        if target == 0:
            return True
        pct_diff = abs(actual - target) / target
        return pct_diff <= TimeUtilization.TOLERANCE_PERCENT


# =============================================================================
# Movement Count Constants
# =============================================================================

class MovementCounts:
    """Movement count validation constants for blocks and sessions.

    These constants define minimum and maximum movement counts for
    different session blocks and overall session requirements.
    """

    # Overall session movement counts
    MIN_SESSION_MOVEMENTS = 8  # Minimum movements for regular sessions
    MAX_SESSION_MOVEMENTS = 15  # Maximum movements for finisher sessions

    # Block-specific movement counts
    WARMUP_MIN = 2
    WARMUP_MAX = 5

    COOLDOWN_MIN = 2
    COOLDOWN_MAX = 5

    MAIN_MIN_REGULAR = 2  # For strength/hypertrophy/cardio sessions
    MAIN_MAX_REGULAR = 5
    MAIN_MIN_ENDURANCE = 6  # For endurance sessions
    MAIN_MAX_ENDURANCE = 10

    ACCESSORY_MIN = 2
    ACCESSORY_MAX = 4

    FINISHER_COUNT = 1  # Finisher counted as 1 unit (circuit or single movement)

    @staticmethod
    def get_main_block_range(session_type: str) -> tuple[int, int]:
        """Get appropriate main block movement count range for session type.

        Args:
            session_type: Type of session (e.g., 'strength', 'endurance')

        Returns:
            Tuple of (min, max) movement count for main block
        """
        session_type_lower = session_type.lower()

        if session_type_lower in SessionTypes.ENDURANCE_TYPES:
            return (MovementCounts.MAIN_MIN_ENDURANCE, MovementCounts.MAIN_MAX_ENDURANCE)
        else:
            return (MovementCounts.MAIN_MIN_REGULAR, MovementCounts.MAIN_MAX_REGULAR)


# =============================================================================
# Scoring Threshold Constants
# =============================================================================

class ScoringThresholds:
    """Threshold constants for scoring and qualification.

    These constants define minimum scores and thresholds for
    various scoring metrics and qualification criteria.
    """

    # Qualification thresholds
    QUALIFICATION_THRESHOLD = 0.5  # Minimum score to qualify (50%)

    # Quality thresholds
    MIN_QUALITY_SCORE = 0.5  # Minimum acceptable quality score

    # Diversity and coverage thresholds
    MOVEMENT_DIVERSITY_THRESHOLD = 70.0  # Minimum 70% unique movements
    OVERALL_VARIETY_THRESHOLD = 75.0  # Minimum 75% overall variety score
    MUSCLE_COVERAGE_THRESHOLD = 100.0  # 100% of major muscles must be covered

    # Success rate thresholds
    MIN_SUCCESS_RATE = 0.5  # 50% minimum success rate for acceptance


# =============================================================================
# Session Type Categories
# =============================================================================

class SessionTypes:
    """Session type classification and categorization constants.

    These constants group session types into functional categories
    for validation and scoring purposes.
    """

    # Regular session types (standard resistance training)
    REGULAR_TYPES = frozenset({
        "strength",
        "hypertrophy",
        "full_body",
        "push",
        "pull",
        "legs",
        "upper",
        "lower",
        "skill",
        "mobility",
        "recovery",
    })

    # Cardio session types
    CARDIO_TYPES = frozenset({"cardio"})

    # Conditioning/Endurance session types
    CONDITIONING_TYPES = frozenset({"conditioning", "endurance"})
    ENDURANCE_TYPES = CONDITIONING_TYPES  # Alias for backward compatibility

    # Finisher session types
    FINISHER_TYPES = frozenset({"finisher", "metcon_finisher"})

    @staticmethod
    def classify(session_type: str) -> str:
        """Classify session type into category.

        Args:
            session_type: The session type to classify

        Returns:
            One of: 'REGULAR', 'CARDIO', 'CONDITIONING', 'FINISHER'
        """
        session_type_lower = session_type.lower()

        if session_type_lower in SessionTypes.FINISHER_TYPES:
            return "FINISHER"
        elif session_type_lower in SessionTypes.CARDIO_TYPES:
            return "CARDIO"
        elif session_type_lower in SessionTypes.CONDITIONING_TYPES:
            return "CONDITIONING"
        else:
            return "REGULAR"

    @staticmethod
    def is_endurance_type(session_type: str) -> bool:
        """Check if session type is an endurance session.

        Args:
            session_type: The session type to check

        Returns:
            True if endurance type, False otherwise
        """
        return session_type.lower() in SessionTypes.ENDURANCE_TYPES


# =============================================================================
# Scoring Dimension Names
# =============================================================================

class ScoringDimensions:
    """Names and identifiers for scoring dimensions.

    These constants define the names of all scoring dimensions
    used in the movement scoring system.
    """

    PATTERN_ALIGNMENT = "pattern_alignment"
    MUSCLE_COVERAGE = "muscle_coverage"
    DISCIPLINE_PREFERENCE = "discipline_preference"
    COMPOUND_BONUS = "compound_bonus"
    SPECIALIZATION = "specialization"
    GOAL_ALIGNMENT = "goal_alignment"
    TIME_UTILIZATION = "time_utilization"

    # All dimensions as a set for iteration
    ALL_DIMENSIONS = frozenset({
        PATTERN_ALIGNMENT,
        MUSCLE_COVERAGE,
        DISCIPLINE_PREFERENCE,
        COMPOUND_BONUS,
        SPECIALIZATION,
        GOAL_ALIGNMENT,
        TIME_UTILIZATION,
    })

    @staticmethod
    def get_display_name(dimension: str) -> str:
        """Get human-readable display name for a dimension.

        Args:
            dimension: Internal dimension identifier

        Returns:
            Human-readable display name
        """
        display_names = {
            ScoringDimensions.PATTERN_ALIGNMENT: "Pattern Alignment",
            ScoringDimensions.MUSCLE_COVERAGE: "Muscle Coverage",
            ScoringDimensions.DISCIPLINE_PREFERENCE: "Discipline Preference",
            ScoringDimensions.COMPOUND_BONUS: "Compound Bonus",
            ScoringDimensions.SPECIALIZATION: "Specialization",
            ScoringDimensions.GOAL_ALIGNMENT: "Goal Alignment",
            ScoringDimensions.TIME_UTILIZATION: "Time Utilization",
        }
        return display_names.get(dimension, dimension.replace("_", " ").title())


# =============================================================================
# Variety Score Weights
# =============================================================================

class VarietyWeights:
    """Weights for calculating overall variety scores.

    These constants define the relative importance of different
    components in the overall variety score calculation.
    """

    PATTERN_ROTATION_WEIGHT = 0.40  # 40% weight for pattern rotation
    MOVEMENT_DIVERSITY_WEIGHT = 0.40  # 40% weight for movement diversity
    PATTERN_TYPE_DIVERSITY_WEIGHT = 0.20  # 20% weight for pattern type diversity

    @staticmethod
    def calculate_overall_score(
        pattern_rotation_score: float,
        movement_diversity_score: float,
        pattern_type_diversity_score: float,
    ) -> float:
        """Calculate weighted overall variety score.

        Args:
            pattern_rotation_score: Score for pattern rotation (0-100)
            movement_diversity_score: Score for movement diversity (0-100)
            pattern_type_diversity_score: Score for pattern type diversity (0-100)

        Returns:
            Weighted overall variety score (0-100)
        """
        return (
            pattern_rotation_score * VarietyWeights.PATTERN_ROTATION_WEIGHT
            + movement_diversity_score * VarietyWeights.MOVEMENT_DIVERSITY_WEIGHT
            + pattern_type_diversity_score * VarietyWeights.PATTERN_TYPE_DIVERSITY_WEIGHT
        )


# =============================================================================
# Muscle Group Constants
# =============================================================================

class MuscleGroups:
    """Constants for muscle group tracking and validation.

    These constants define the major muscle groups tracked for
    coverage validation and aggregation rules.
    """

    # Major muscle groups (7 groups)
    MAJOR_MUSCLES = frozenset({
        "quadriceps",
        "hamstrings",
        "glutes",
        "chest",
        "lats",
        "upper_back",
        "shoulders",
    })

    # Shoulder muscles that aggregate to "shoulders"
    SHOULDER_MUSCLES = frozenset({"front_delts", "side_delts", "rear_delts"})

    @staticmethod
    def normalize_muscle(muscle: str) -> str:
        """Normalize muscle name to match major muscle groups.

        This method handles:
        - Case normalization
        - Aggregating shoulder muscles to "shoulders"

        Args:
            muscle: Muscle name to normalize

        Returns:
            Normalized muscle name
        """
        muscle_lower = muscle.lower()

        # Aggregate shoulder muscles
        if muscle_lower in MuscleGroups.SHOULDER_MUSCLES:
            return "shoulders"

        return muscle_lower

    @staticmethod
    def is_major_muscle(muscle: str) -> bool:
        """Check if muscle is a major muscle group.

        Args:
            muscle: Muscle name to check

        Returns:
            True if major muscle group, False otherwise
        """
        return MuscleGroups.normalize_muscle(muscle) in MuscleGroups.MAJOR_MUSCLES


# =============================================================================
# Pattern Rotation Constants
# =============================================================================

class PatternRotation:
    """Constants for pattern rotation validation.

    These constants define the rules for ensuring pattern variety
    across sessions of the same type.
    """

    MIN_SESSIONS_BETWEEN_REPEATS = 2  # Minimum sessions between pattern repeats

    @staticmethod
    def is_rotation_violated(
        current_pattern: str,
        previous_patterns: list[str],
    ) -> bool:
        """Check if pattern rotation rule is violated.

        Args:
            current_pattern: Pattern in current session
            previous_patterns: Patterns from previous sessions (most recent first)

        Returns:
            True if rotation violated, False otherwise
        """
        recent_patterns = previous_patterns[:PatternRotation.MIN_SESSIONS_BETWEEN_REPEATS]
        return current_pattern in recent_patterns


# =============================================================================
# Validation Message Templates
# =============================================================================

class MessageTemplates:
    """Templates for building validation messages.

    These constants provide reusable message templates for consistent
    validation feedback across KPI modules.
    """

    # Pass message templates
    PASS_TEMPLATE = "{validation_type} passed for {entity_id}."
    PASS_WITH_DETAILS = "{validation_type} passed for {entity_id}. {details}."

    # Fail message templates
    FAIL_TEMPLATE = "{validation_type} failed for {entity_id}."
    FAIL_WITH_REASONS = "{validation_type} failed for {entity_id}. Reasons: {reasons}."
    FAIL_WITH_RECOMMENDATIONS = "{validation_type} failed for {entity_id}. Reasons: {reasons}. Recommendations: {recommendations}."

    # Range validation templates
    RANGE_ACCEPTABLE = "{block} has {actual} movement(s) (acceptable range: {min}-{max})"
    RANGE_BELOW_MIN = "{block} has {actual} movement(s), which is below minimum {min}. Add {to_add} more movement(s)."
    RANGE_ABOVE_MAX = "{block} has {actual} movement(s), which exceeds maximum {max}. Remove {to_remove} movement(s)."


# =============================================================================
# Convenience Exports
# =============================================================================

# For backward compatibility and convenience
TIME_UTILIZATION_TOLERANCE = TimeUtilization.TOLERANCE_PERCENT
MIN_MOVEMENT_COUNT = MovementCounts.MIN_SESSION_MOVEMENTS
MAX_MOVEMENT_COUNT = MovementCounts.MAX_SESSION_MOVEMENTS
QUALIFICATION_THRESHOLD = ScoringThresholds.QUALIFICATION_THRESHOLD
MOVEMENT_DIVERSITY_THRESHOLD = ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD
OVERALL_VARIETY_THRESHOLD = ScoringThresholds.OVERALL_VARIETY_THRESHOLD
MUSCLE_COVERAGE_THRESHOLD = ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD


# =============================================================================
# Optimization Constants (moved from app/services/optimization_constants.py)
# =============================================================================

class OptimizationConstants:
    """Constants for the optimization service.
    
    These constants are used by DiversityOptimizationService for movement
    selection and constraint satisfaction.
    
    Note: Some constants (COMPOUND_BONUS, score bounds) have similar names
    to KPI constants but different values - this is intentional as they
    serve different purposes (optimization scoring vs validation thresholds).
    """
    
    # Time calculation
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_SET = 4  # Average seconds per set
    
    # Synergist muscle weighting
    SYNERGIST_SET_MULTIPLIER = 0.5  # Synergist movements count at 50%
    
    # Emergency mode multipliers (progressive relaxation step 6)
    EMERGENCY_VOLUME_MULTIPLIER = 0.5
    EMERGENCY_FATIGUE_MULTIPLIER = 1.5
    EMERGENCY_DURATION_MULTIPLIER = 1.25
    
    # Scoring multipliers (for integer conversion in solver)
    BASE_SCORE_MULTIPLIER = 1000
    CIRCUIT_STIMULUS_MULTIPLIER = 100
    CARDIO_SCORE_MULTIPLIER = 10
    
    # Base scoring values
    NEUTRAL_BASE_SCORE = 0.5
    DISCIPLINE_PREFERENCE_BONUS = 0.2
    COMPOUND_BONUS = 0.1  # Note: Different from ScoringDimensions.COMPOUND_BONUS
    
    # Dimension weights
    DIMENSION_SCORE_WEIGHT = 0.2  # Each of 5 dimensions = 20%
    
    # Thresholds
    MIN_QUALIFIED_SCORE = 0.5
    SCORE_MIN_BOUND = 0.0
    SCORE_MAX_BOUND = 1.0
    
    # Relaxation
    DISCIPLINE_WEIGHT_RELAXATION_MULTIPLIER = 0.7
