"""Muscle coverage KPIs for microcycle-level validation.

This module provides comprehensive validation for muscle group coverage
across training sessions within a microcycle, ensuring balanced training
and no major muscle groups are neglected.

The MuscleCoverageKPI class validates:
- Complete coverage of major muscle groups (no missed major muscles)
- Coverage percentage calculation
- Detailed feedback on missing or undertrained muscles
- Shoulder coverage aggregation (front/side/rear delts)

Major Muscle Groups:
- Lower Body: quadriceps, hamstrings, glutes
- Upper Body: chest, lats, upper_back
- Shoulders: aggregated from front_delts, side_delts, rear_delts
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.enums import PrimaryMuscle

from app.ml.scoring.base import BaseValidationResult
from app.ml.scoring.constants import (
    MuscleGroups,
    ScoringThresholds,
)
from app.ml.scoring.exceptions import (
    InsufficientCoverageError,
    ValidationException,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MuscleCoverageResult:
    """Result of muscle coverage analysis for a single session.

    Attributes:
        session_id: ID of session analyzed
        session_type: Type of the session
        covered_muscles: Tuple of muscle groups targeted in this session
        coverage_count: Number of major muscle groups covered
        message: Detailed feedback message
    """

    session_id: int
    session_type: str
    covered_muscles: tuple[str, ...]
    coverage_count: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "covered_muscles": list(self.covered_muscles),
            "coverage_count": self.coverage_count,
            "message": self.message,
        }


@dataclass(frozen=True)
class MicrocycleCoverageResult(BaseValidationResult):
    """Result of validating muscle coverage across a microcycle.

    Attributes:
        microcycle_id: ID of the microcycle validated
        passed: Whether all major muscle groups are covered
        covered_muscles: Tuple of muscle groups covered in microcycle
        missing_muscles: Tuple of muscle groups not covered
        coverage_score: Percentage of major muscle groups covered (0-100)
        threshold: Minimum coverage percentage required for passing
        session_results: Tuple of per-session muscle coverage results
        muscle_frequency: Frequency count of each muscle across sessions
        message: Detailed feedback message
    """

    microcycle_id: int
    passed: bool
    covered_muscles: tuple[str, ...]
    missing_muscles: tuple[str, ...]
    coverage_score: float
    threshold: float
    session_results: tuple[MuscleCoverageResult, ...]
    muscle_frequency: tuple[tuple[str, int], ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "microcycle_id": self.microcycle_id,
            "passed": self.passed,
            "covered_muscles": list(self.covered_muscles),
            "missing_muscles": list(self.missing_muscles),
            "coverage_score": self.coverage_score,
            "threshold": self.threshold,
            "session_results": [sr.to_dict() for sr in self.session_results],
            "muscle_frequency": list(self.muscle_frequency),
            "message": self.message,
        }


@dataclass(frozen=True)
class SessionMuscleData:
    """Muscle data for a single session.

    Attributes:
        session_id: ID of the session
        session_type: Type of the session
        primary_muscles: Tuple of primary muscle groups targeted
    """

    session_id: int
    session_type: str
    primary_muscles: tuple[str, ...]


class MuscleCoverageKPI:
    """Validator for muscle coverage KPIs across microcycles.

    This class provides comprehensive validation of muscle group coverage,
    ensuring balanced training across major muscle groups and providing
    detailed feedback on coverage gaps.

    Major Muscle Groups:
    - quadriceps: Primary knee extensors (squats, leg press, lunges)
    - hamstrings: Posterior chain (deadlifts, leg curls, RDLs)
    - glutes: Hip extension (hip thrusts, glute bridges)
    - chest: Horizontal pushing (bench press, pushups)
    - lats: Vertical pulling (pullups, pulldowns)
    - upper_back: Horizontal pulling (rows)
    - shoulders: Aggregated from front_delts, side_delts, rear_delts

    Shoulder Coverage Logic:
    - Any of front_delts, side_delts, or rear_delts counts as "shoulders"
    - Multiple shoulder muscles in a session still count as one coverage unit

    Example:
        >>> validator = MuscleCoverageKPI()
        >>> 
        >>> # Define microcycle sessions
        >>> sessions = [
        ...     SessionMuscleData(
        ...         session_id=1,
        ...         session_type="strength",
        ...         primary_muscles=("quadriceps", "glutes", "chest", "front_delts")
        ...     ),
        ...     SessionMuscleData(
        ...         session_id=2,
        ...         session_type="strength",
        ...         primary_muscles=("hamstrings", "lats", "upper_back", "rear_delts")
        ...     )
        ... ]
        >>> 
        >>> # Check microcycle coverage
        >>> result = validator.check_microcycle_coverage(sessions, microcycle_id=1)
        >>> print(result.passed)
        >>> print(result.message)
    """

    def __init__(self) -> None:
        """Initialize the muscle coverage KPI validator."""
        logger.debug("Initialized MuscleCoverageKPI validator")

    def check_microcycle_coverage(
        self, microcycle_sessions: list[SessionMuscleData], microcycle_id: int
    ) -> MicrocycleCoverageResult:
        """Validate that no major muscle group is missed in the microcycle.

        This method analyzes all sessions in a microcycle to ensure complete
        coverage of all major muscle groups. It provides detailed feedback on
        which muscles are covered, which are missing, and the overall coverage
        percentage.

        Args:
            microcycle_sessions: List of sessions in the microcycle.
            microcycle_id: ID of the microcycle being validated.

        Returns:
            MicrocycleCoverageResult: Complete validation result with details.

        Raises:
            InsufficientCoverageError: If coverage validation fails.
        """
        try:
            if not microcycle_sessions:
                logger.warning(f"No sessions provided for microcycle {microcycle_id}")
                return MicrocycleCoverageResult(
                    microcycle_id=microcycle_id,
                    passed=False,
                    covered_muscles=(),
                    missing_muscles=tuple(MuscleGroups.MAJOR_MUSCLES),
                    coverage_score=0.0,
                    threshold=ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD,
                    session_results=(),
                    muscle_frequency=(),
                    message=f"Microcycle {microcycle_id} has no sessions. Cannot validate muscle coverage.",
                )

            # Analyze each session
            session_results: list[MuscleCoverageResult] = []
            all_covered_muscles: set[str] = set()

            for session in microcycle_sessions:
                result = self._analyze_session_muscles(session)
                session_results.append(result)

                # Add covered muscles to the set
                for muscle in result.covered_muscles:
                    all_covered_muscles.add(muscle)

            # Identify missing muscles
            missing_muscles = MuscleGroups.MAJOR_MUSCLES - all_covered_muscles

            # Calculate coverage score
            coverage_score = (len(all_covered_muscles) / len(MuscleGroups.MAJOR_MUSCLES)) * 100

            # Determine pass/fail
            passed = coverage_score >= ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD

            # Calculate muscle frequency across sessions
            muscle_counter: Counter[str] = Counter()
            for session in microcycle_sessions:
                for muscle in session.primary_muscles:
                    normalized = self._normalize_muscle(muscle)
                    if normalized in MuscleGroups.MAJOR_MUSCLES:
                        muscle_counter[normalized] += 1

            muscle_frequency = tuple(muscle_counter.most_common())

            # Build detailed message
            message = self._build_coverage_message(
                microcycle_id=microcycle_id,
                passed=passed,
                covered_muscles=sorted(all_covered_muscles),
                missing_muscles=sorted(missing_muscles),
                coverage_score=coverage_score,
                muscle_frequency=muscle_frequency,
            )

            logger.debug(
                f"Muscle coverage for microcycle {microcycle_id}: "
                f"score={coverage_score:.1f}%, passed={passed}"
            )

            return MicrocycleCoverageResult(
                microcycle_id=microcycle_id,
                passed=passed,
                covered_muscles=tuple(sorted(all_covered_muscles)),
                missing_muscles=tuple(sorted(missing_muscles)),
                coverage_score=coverage_score,
                threshold=ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD,
                session_results=tuple(session_results),
                muscle_frequency=muscle_frequency,
                message=message,
            )

        except Exception as e:
            raise InsufficientCoverageError(
                f"Failed to validate muscle coverage for microcycle {microcycle_id}: {e}"
            ) from e

    def get_coverage_score(
        self, microcycle_sessions: list[SessionMuscleData], microcycle_id: int
    ) -> MicrocycleCoverageResult:
        """Calculate muscle coverage percentage for a microcycle.

        This is a convenience method that returns the same result as
        check_microcycle_coverage but with a clearer semantic name for
        score calculation purposes.

        Args:
            microcycle_sessions: List of sessions in the microcycle.
            microcycle_id: ID of the microcycle being evaluated.

        Returns:
            MicrocycleCoverageResult: Coverage score with full details.
        """
        return self.check_microcycle_coverage(microcycle_sessions, microcycle_id)

    def _analyze_session_muscles(self, session: SessionMuscleData) -> MuscleCoverageResult:
        """Analyze which major muscle groups are covered in a session.

        Args:
            session: Session data containing primary muscles.

        Returns:
            MuscleCoverageResult: Analysis result for the session.
        """
        # Normalize and filter muscles
        covered_muscles: set[str] = set()

        for muscle in session.primary_muscles:
            normalized = self._normalize_muscle(muscle)
            if normalized in MuscleGroups.MAJOR_MUSCLES:
                covered_muscles.add(normalized)

        # Build message
        if covered_muscles:
            muscles_str = ", ".join(sorted(covered_muscles))
            message = (
                f"Session {session.session_id} ({session.session_type}) "
                f"covers: {muscles_str} ({len(covered_muscles)} major muscle(s))"
            )
        else:
            message = (
                f"Session {session.session_id} ({session.session_type}) "
                f"covers no major muscle groups"
            )

        return MuscleCoverageResult(
            session_id=session.session_id,
            session_type=session.session_type,
            covered_muscles=tuple(sorted(covered_muscles)),
            coverage_count=len(covered_muscles),
            message=message,
        )

    def _normalize_muscle(self, muscle: str | PrimaryMuscle) -> str:
        """Normalize muscle name to match major muscle groups.

        This method handles:
        - Converting PrimaryMuscle enum values to strings
        - Aggregating shoulder muscles to "shoulders"
        - Case normalization

        Args:
            muscle: Muscle name or PrimaryMuscle enum.

        Returns:
            Normalized muscle name string.
        """
        return MuscleGroups.normalize_muscle(muscle)

    def _build_coverage_message(
        self,
        microcycle_id: int,
        passed: bool,
        covered_muscles: list[str],
        missing_muscles: list[str],
        coverage_score: float,
        muscle_frequency: tuple[tuple[str, int], ...],
    ) -> str:
        """Build detailed coverage validation message.

        Args:
            microcycle_id: ID of the microcycle.
            passed: Whether validation passed.
            covered_muscles: List of covered muscle groups.
            missing_muscles: List of missing muscle groups.
            coverage_score: Coverage percentage.
            muscle_frequency: Frequency count of each muscle.

        Returns:
            Detailed validation message.
        """
        if passed:
            message = (
                f"Microcycle {microcycle_id} passed muscle coverage check. "
                f"All {len(MuscleGroups.MAJOR_MUSCLES)} major muscle groups covered: "
                f"{', '.join(covered_muscles)}. "
                f"Coverage: {coverage_score:.1f}%."
            )
        else:
            # Build failure message with recommendations
            missing_str = ", ".join(missing_muscles) if missing_muscles else "none"
            covered_str = ", ".join(covered_muscles) if covered_muscles else "none"

            message = (
                f"Microcycle {microcycle_id} failed muscle coverage check. "
                f"Coverage: {coverage_score:.1f}% (threshold: {ScoringThresholds.MUSCLE_COVERAGE_THRESHOLD}%). "
                f"Covered: {covered_str}. Missing: {missing_str}. "
            )

            # Add recommendations for missing muscles
            if missing_muscles:
                recommendations = self._get_muscle_recommendations(missing_muscles)
                message += f"Recommendations: {recommendations}."

        # Add frequency breakdown
        if muscle_frequency:
            freq_str = ", ".join([f"{muscle} ({count}x)" for muscle, count in muscle_frequency])
            message += f" Muscle frequency: {freq_str}."

        return message

    def _get_muscle_recommendations(self, missing_muscles: list[str]) -> str:
        """Get movement pattern recommendations for missing muscle groups.

        Args:
            missing_muscles: List of missing muscle groups.

        Returns:
            Recommendation string.
        """
        recommendations: list[str] = []

        muscle_to_pattern = {
            "quadriceps": "squat or lunge patterns",
            "hamstrings": "hinge patterns (RDLs, leg curls)",
            "glutes": "hip extension patterns (hip thrusts, glute bridges)",
            "chest": "horizontal push patterns (bench press, pushups)",
            "lats": "vertical pull patterns (pullups, pulldowns)",
            "upper_back": "horizontal pull patterns (rows)",
            "shoulders": "vertical push patterns (overhead press) and isolation work",
        }

        for muscle in missing_muscles:
            if muscle in muscle_to_pattern:
                recommendations.append(f"{muscle}: {muscle_to_pattern[muscle]}")

        return "; ".join(recommendations)
