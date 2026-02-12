"""Movement variety KPIs for microcycle-level validation.

This module provides comprehensive validation for movement variety across training
sessions within a microcycle, ensuring optimal pattern rotation and movement diversity.

The MovementVarietyKPI class validates:
- Pattern rotation: No pattern repeats within 2 sessions of SAME TYPE (CARDIO/CONDITIONING/REGULAR)
- Unique movements: Percentage of unique movements within a microcycle
- Overall variety score: Composite score based on multiple variety metrics

Variety Rules:
- REGULAR sessions (strength/hypertrophy/full_body/push/pull/legs/upper/lower): 
  No pattern repeats within 2 sessions of same type
- CARDIO sessions: No pattern repeats within 2 cardio sessions
- CONDITIONING sessions: No pattern repeats within 2 conditioning sessions
- Cross-type pattern repetition is allowed (e.g., squat pattern in regular session
  and cardio session within 2 sessions)
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.enums import SessionType

from app.ml.scoring.base import BaseValidationResult
from app.ml.scoring.constants import (
    PatternRotation,
    ScoringThresholds,
    SessionTypes,
    VarietyWeights,
)
from app.ml.scoring.exceptions import (
    MovementDiversityError,
    PatternRotationError,
    ValidationException,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PatternRotationResult(BaseValidationResult):
    """Result of validating pattern rotation across sessions.

    Attributes:
        passed: Whether pattern rotation validation passed
        current_session_id: ID of the current session being validated
        current_session_type: Type of the current session
        current_pattern: Primary pattern in current session
        previous_same_type_sessions: List of previous sessions of same type
        repeated_patterns: List of patterns that violated rotation rule
        message: Detailed feedback message
    """

    passed: bool
    current_session_id: int
    current_session_type: str
    current_pattern: str
    previous_same_type_sessions: tuple[dict[str, Any], ...]
    repeated_patterns: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "current_session_id": self.current_session_id,
            "current_session_type": self.current_session_type,
            "current_pattern": self.current_pattern,
            "previous_same_type_sessions": list(self.previous_same_type_sessions),
            "repeated_patterns": list(self.repeated_patterns),
            "message": self.message,
        }


@dataclass(frozen=True)
class MovementDiversityResult(BaseValidationResult):
    """Result of calculating movement diversity in a microcycle.

    Attributes:
        passed: Whether diversity threshold was met
        microcycle_id: ID of the microcycle
        total_movements: Total movement instances across all sessions
        unique_movements: Count of unique movement IDs
        unique_percentage: Percentage of unique movements (0-100)
        threshold: Minimum required percentage for passing
        most_common_movements: Top repeated movements with counts
        message: Detailed feedback message
    """

    passed: bool
    microcycle_id: int
    total_movements: int
    unique_movements: int
    unique_percentage: float
    threshold: float
    most_common_movements: tuple[tuple[int, int], ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "microcycle_id": self.microcycle_id,
            "total_movements": self.total_movements,
            "unique_movements": self.unique_movements,
            "unique_percentage": self.unique_percentage,
            "threshold": self.threshold,
            "most_common_movements": list(self.most_common_movements),
            "message": self.message,
        }


@dataclass(frozen=True)
class VarietyScoreResult(BaseValidationResult):
    """Result of calculating overall variety score for a microcycle.

    Attributes:
        passed: Whether overall variety score met threshold
        microcycle_id: ID of the microcycle
        pattern_rotation_score: Score for pattern rotation (0-100)
        movement_diversity_score: Score for movement diversity (0-100)
        pattern_type_diversity_score: Score for session type diversity (0-100)
        overall_score: Weighted overall variety score (0-100)
        threshold: Minimum required overall score for passing
        message: Detailed feedback message
        component_results: Detailed results for each component
    """

    passed: bool
    microcycle_id: int
    pattern_rotation_score: float
    movement_diversity_score: float
    pattern_type_diversity_score: float
    overall_score: float
    threshold: float
    message: str
    component_results: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "microcycle_id": self.microcycle_id,
            "pattern_rotation_score": self.pattern_rotation_score,
            "movement_diversity_score": self.movement_diversity_score,
            "pattern_type_diversity_score": self.pattern_type_diversity_score,
            "overall_score": self.overall_score,
            "threshold": self.threshold,
            "message": self.message,
            "component_results": self.component_results,
        }


@dataclass(frozen=True)
class SessionMovements:
    """Movement data for a single session.

    Attributes:
        session_id: ID of the session
        session_type: Type of the session
        movement_ids: List of movement IDs in the session
        patterns: List of movement patterns in the session
        primary_pattern: Most frequent or primary pattern (main block)
    """

    session_id: int
    session_type: str
    movement_ids: tuple[int, ...]
    patterns: tuple[str, ...]
    primary_pattern: str


class MovementVarietyKPI:
    """Validator for movement variety KPIs across microcycles.

    This class provides comprehensive validation of movement variety metrics,
    including pattern rotation, movement diversity, and overall variety scoring.

    Session Type Classification:
    - REGULAR: strength, hypertrophy, full_body, push, pull, legs, upper, lower, skill
    - CARDIO: cardio
    - CONDITIONING: conditioning, endurance

    Example:
        >>> validator = MovementVarietyKPI()
        >>> 
        >>> # Check pattern rotation
        >>> current = SessionMovements(
        ...     session_id=1,
        ...     session_type="strength",
        ...     movement_ids=(101, 102, 103),
        ...     patterns=("squat", "hinge", "horizontal_push"),
        ...     primary_pattern="squat"
        ... )
        >>> previous = [
        ...     SessionMovements(
        ...         session_id=0,
        ...         session_type="strength",
        ...         movement_ids=(104, 105, 106),
        ...         patterns=("hinge", "horizontal_pull", "core"),
        ...         primary_pattern="hinge"
        ...     ),
        ...     SessionMovements(
        ...         session_id=-1,
        ...         session_type="strength",
        ...         movement_ids=(107, 108, 109),
        ...         patterns=("vertical_push", "horizontal_push", "core"),
        ...         primary_pattern="vertical_push"
        ...     )
        ... ]
        >>> result = validator.check_pattern_rotation(current, previous)
        >>> print(result.passed)
    """

    def __init__(self) -> None:
        """Initialize the movement variety KPI validator."""
        logger.debug("Initialized MovementVarietyKPI validator")

    def _classify_session_type(self, session_type: str | SessionType) -> str:
        """Classify session type into REGULAR, CARDIO, or CONDITIONING.

        Args:
            session_type: The session type to classify.

        Returns:
            One of: 'REGULAR', 'CARDIO', 'CONDITIONING'
        """
        return SessionTypes.classify(session_type)

    def check_pattern_rotation(
        self, current_session: SessionMovements, previous_sessions: list[SessionMovements]
    ) -> PatternRotationResult:
        """Validate that patterns don't repeat within 2 sessions of SAME TYPE.

        This ensures pattern rotation only considers sessions of the same type:
        - REGULAR sessions are checked against previous REGULAR sessions
        - CARDIO sessions are checked against previous CARDIO sessions
        - CONDITIONING sessions are checked against previous CONDITIONING sessions

        Cross-type pattern repetition is allowed (e.g., squat pattern can appear
        in a regular session and a cardio session within 2 sessions).

        Args:
            current_session: Current session to validate.
            previous_sessions: List of previous sessions in chronological order
                (most recent first).

        Returns:
            PatternRotationResult: Validation result with detailed feedback.

        Raises:
            PatternRotationError: If validation process fails.
        """
        try:
            current_type = self._classify_session_type(current_session.session_type)
            current_pattern = current_session.primary_pattern

            # Filter previous sessions to only same type
            same_type_previous = [
                s
                for s in previous_sessions
                if self._classify_session_type(s.session_type) == current_type
            ]

            # Check last 2 sessions of same type
            last_two = same_type_previous[:2]

            repeated_patterns: list[str] = []

            # Check for pattern rotation violations
            if PatternRotation.is_rotation_violated(
                current_pattern, [s.primary_pattern for s in last_two]
            ):
                for prev_session in last_two:
                    if prev_session.primary_pattern == current_pattern:
                        repeated_patterns.append(
                            f"Pattern '{current_pattern}' repeated in session {prev_session.session_id}"
                        )

            passed = len(repeated_patterns) == 0

            # Build message
            if passed:
                message = (
                    f"Pattern rotation passed for session {current_session.session_id}. "
                    f"Primary pattern '{current_pattern}' not repeated in last "
                    f"{len(last_two)} {current_type} session(s)."
                )
            else:
                message = (
                    f"Pattern rotation failed for session {current_session.session_id}. "
                    f"Primary pattern '{current_pattern}' repeated within 2 sessions "
                    f"of type '{current_type}'. Issues: {'; '.join(repeated_patterns)}. "
                    f"Consider using a different pattern or increasing session spacing."
                )

            logger.debug(
                f"Pattern rotation check for session {current_session.session_id}: "
                f"passed={passed}, type={current_type}, pattern={current_pattern}"
            )

            return PatternRotationResult(
                passed=passed,
                current_session_id=current_session.session_id,
                current_session_type=current_type,
                current_pattern=current_pattern,
                previous_same_type_sessions=tuple(
                    {
                        "session_id": s.session_id,
                        "session_type": s.session_type,
                        "primary_pattern": s.primary_pattern,
                    }
                    for s in last_two
                ),
                repeated_patterns=tuple(repeated_patterns),
                message=message,
            )

        except Exception as e:
            raise PatternRotationError(
                f"Failed to validate pattern rotation for session {current_session.session_id}: {e}"
            ) from e

    def calculate_unique_movements_in_microcycle(
        self, microcycle_sessions: list[SessionMovements], microcycle_id: int
    ) -> MovementDiversityResult:
        """Calculate the percentage of unique movements in a microcycle.

        This metric ensures adequate movement variety by measuring how many
        unique movements are used relative to total movement instances.

        Args:
            microcycle_sessions: List of sessions in the microcycle.
            microcycle_id: ID of the microcycle being evaluated.

        Returns:
            MovementDiversityResult: Diversity calculation result with details.

        Raises:
            MovementDiversityError: If calculation fails.
        """
        try:
            if not microcycle_sessions:
                return MovementDiversityResult(
                    passed=True,
                    microcycle_id=microcycle_id,
                    total_movements=0,
                    unique_movements=0,
                    unique_percentage=100.0,
                    threshold=ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD,
                    most_common_movements=(),
                    message="No sessions in microcycle, diversity check skipped.",
                )

            # Collect all movement IDs
            all_movements: list[int] = []
            for session in microcycle_sessions:
                all_movements.extend(session.movement_ids)

            total_movements = len(all_movements)

            if total_movements == 0:
                return MovementDiversityResult(
                    passed=True,
                    microcycle_id=microcycle_id,
                    total_movements=0,
                    unique_movements=0,
                    unique_percentage=100.0,
                    threshold=ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD,
                    most_common_movements=(),
                    message="No movements in microcycle, diversity check skipped.",
                )

            # Calculate uniqueness
            unique_movements = len(set(all_movements))
            unique_percentage = (unique_movements / total_movements) * 100

            # Find most repeated movements
            movement_counts = Counter(all_movements)
            most_common = movement_counts.most_common(5)

            passed = unique_percentage >= ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD

            # Build message
            if passed:
                message = (
                    f"Movement diversity passed for microcycle {microcycle_id}. "
                    f"Unique movements: {unique_movements}/{total_movements} "
                    f"({unique_percentage:.1f}%), meets threshold "
                    f"({ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD}%)."
                )
            else:
                most_repeated = ", ".join(
                    [f"movement {mid} (used {count}x)" for mid, count in most_common[:3]]
                )
                message = (
                    f"Movement diversity failed for microcycle {microcycle_id}. "
                    f"Unique movements: {unique_movements}/{total_movements} "
                    f"({unique_percentage:.1f}%), below threshold "
                    f"({ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD}%). "
                    f"Most repeated: {most_repeated}. "
                    f"Consider adding more variety or substituting repeated movements."
                )

            logger.debug(
                f"Movement diversity for microcycle {microcycle_id}: "
                f"unique={unique_percentage:.1f}%, passed={passed}"
            )

            return MovementDiversityResult(
                passed=passed,
                microcycle_id=microcycle_id,
                total_movements=total_movements,
                unique_movements=unique_movements,
                unique_percentage=unique_percentage,
                threshold=ScoringThresholds.MOVEMENT_DIVERSITY_THRESHOLD,
                most_common_movements=tuple(most_common),
                message=message,
            )

        except Exception as e:
            raise MovementDiversityError(
                f"Failed to calculate movement diversity for microcycle {microcycle_id}: {e}"
            ) from e

    def get_variety_score(
        self, microcycle_sessions: list[SessionMovements], microcycle_id: int
    ) -> VarietyScoreResult:
        """Calculate overall variety score for a microcycle.

        The overall variety score is a weighted composite of:
        1. Pattern rotation score (40%): How well patterns rotate within same-type sessions
        2. Movement diversity score (40%): Percentage of unique movements
        3. Pattern type diversity score (20%): Distribution of movement patterns across sessions

        Args:
            microcycle_sessions: List of sessions in the microcycle in chronological order.
            microcycle_id: ID of the microcycle being evaluated.

        Returns:
            VarietyScoreResult: Overall variety score with component breakdown.

        Raises:
            VarietyValidationError: If score calculation fails.
        """
        try:
            component_results: dict[str, Any] = {}

            # Calculate pattern rotation score
            pattern_rotation_score = self._calculate_pattern_rotation_score(
                microcycle_sessions
            )
            component_results["pattern_rotation_score"] = pattern_rotation_score

            # Calculate movement diversity score
            diversity_result = self.calculate_unique_movements_in_microcycle(
                microcycle_sessions, microcycle_id
            )
            movement_diversity_score = diversity_result.unique_percentage
            component_results["movement_diversity"] = diversity_result.to_dict()

            # Calculate pattern type diversity score
            pattern_type_diversity_score = self._calculate_pattern_type_diversity(
                microcycle_sessions
            )
            component_results["pattern_type_diversity_score"] = pattern_type_diversity_score

            # Calculate weighted overall score
            overall_score = VarietyWeights.calculate_overall_score(
                pattern_rotation_score,
                movement_diversity_score,
                pattern_type_diversity_score,
            )

            passed = overall_score >= ScoringThresholds.OVERALL_VARIETY_THRESHOLD

            # Build message
            if passed:
                message = (
                    f"Overall variety score passed for microcycle {microcycle_id}. "
                    f"Score: {overall_score:.1f}/100 (threshold: {ScoringThresholds.OVERALL_VARIETY_THRESHOLD}). "
                    f"Components: Pattern Rotation ({pattern_rotation_score:.1f}), "
                    f"Movement Diversity ({movement_diversity_score:.1f}), "
                    f"Pattern Type Diversity ({pattern_type_diversity_score:.1f})."
                )
            else:
                # Identify weakest component
                components = {
                    "Pattern Rotation": pattern_rotation_score,
                    "Movement Diversity": movement_diversity_score,
                    "Pattern Type Diversity": pattern_type_diversity_score,
                }
                weakest = min(components, key=components.get)
                message = (
                    f"Overall variety score failed for microcycle {microcycle_id}. "
                    f"Score: {overall_score:.1f}/100 (threshold: {ScoringThresholds.OVERALL_VARIETY_THRESHOLD}). "
                    f"Weakest component: {weakest} ({components[weakest]:.1f}). "
                    f"Consider improving {weakest.lower()} to increase variety."
                )

            logger.debug(
                f"Overall variety score for microcycle {microcycle_id}: "
                f"{overall_score:.1f}, passed={passed}"
            )

            return VarietyScoreResult(
                passed=passed,
                microcycle_id=microcycle_id,
                pattern_rotation_score=pattern_rotation_score,
                movement_diversity_score=movement_diversity_score,
                pattern_type_diversity_score=pattern_type_diversity_score,
                overall_score=overall_score,
                threshold=ScoringThresholds.OVERALL_VARIETY_THRESHOLD,
                message=message,
                component_results=component_results,
            )

        except Exception as e:
            raise VarietyValidationError(
                f"Failed to calculate variety score for microcycle {microcycle_id}: {e}"
            ) from e

    def _calculate_pattern_rotation_score(
        self, microcycle_sessions: list[SessionMovements]
    ) -> float:
        """Calculate pattern rotation score based on violations across microcycle.

        Args:
            microcycle_sessions: List of sessions in chronological order.

        Returns:
            Pattern rotation score (0-100).
        """
        if len(microcycle_sessions) < 2:
            return 100.0

        violations = 0
        total_checks = 0

        # Check each session against previous same-type sessions
        for i in range(1, len(microcycle_sessions)):
            current = microcycle_sessions[i]
            previous = microcycle_sessions[:i][::-1]  # Reverse to get most recent first

            try:
                result = self.check_pattern_rotation(current, previous)
                total_checks += 1
                if not result.passed:
                    violations += 1
            except Exception as e:
                logger.warning(f"Pattern rotation check failed for session {current.session_id}: {e}")
                continue

        if total_checks == 0:
            return 100.0

        # Score decreases with each violation
        score = max(0.0, 100.0 - (violations / total_checks) * 100)
        return score

    def _calculate_pattern_type_diversity(
        self, microcycle_sessions: list[SessionMovements]
    ) -> float:
        """Calculate pattern type diversity score across all sessions.

        Measures how evenly different movement patterns are distributed across
        the microcycle. Higher scores indicate better pattern variety.

        Args:
            microcycle_sessions: List of sessions in the microcycle.

        Returns:
            Pattern type diversity score (0-100).
        """
        if not microcycle_sessions:
            return 100.0

        # Collect all patterns across all sessions
        all_patterns: list[str] = []
        for session in microcycle_sessions:
            all_patterns.extend(session.patterns)

        if not all_patterns:
            return 100.0

        # Count pattern occurrences
        pattern_counts = Counter(all_patterns)
        unique_patterns = len(pattern_counts)
        total_patterns = len(all_patterns)

        # Calculate distribution evenness using Shannon entropy-like approach
        # Perfect distribution: each pattern appears equally
        expected_count = total_patterns / unique_patterns if unique_patterns > 0 else 0

        if expected_count == 0:
            return 100.0

        # Calculate deviation from ideal distribution
        deviation = sum(abs(count - expected_count) for count in pattern_counts.values())
        max_deviation = sum(
            abs((i + 1) * total_patterns - expected_count)
            for i in range(unique_patterns)
            if i + 1 <= total_patterns
        )

        if max_deviation == 0:
            return 100.0

        # Score based on how close distribution is to ideal
        score = max(0.0, 100.0 - (deviation / max_deviation) * 100)

        # Bonus for having more unique patterns (up to 8 patterns)
        pattern_bonus = min(20.0, (unique_patterns / 8.0) * 20.0)

        return min(100.0, score + pattern_bonus)
