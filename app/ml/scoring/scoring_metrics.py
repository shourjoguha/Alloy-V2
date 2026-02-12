"""Scoring metrics tracker for session evaluation and analysis.

This module provides comprehensive tracking and analysis of session scoring metrics,
including success rate calculation, dimension effectiveness analysis, and structured
metric storage for machine learning and optimization purposes.

The tracker evaluates sessions against multiple criteria:
- Structural completeness (warmup, main, accessory/finisher, cooldown)
- Movement count requirements
- Time utilization within target range
- Pattern diversity (session-type dependent)
- Muscle coverage across microcycle
- Hard constraint compliance
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, final

if TYPE_CHECKING:
    from app.models import Session, SessionExercise, Movement
    from app.models.enums import SessionType

from app.ml.scoring.constants import (
    MovementCounts,
    SessionTypes,
    TimeUtilization,
)
from app.ml.scoring.exceptions import (
    MetricsStorageError,
    MetricsValidationError,
    ScoringException,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DimensionScores:
    """Scores for each scoring dimension.

    Attributes:
        pattern_alignment: Score for pattern alignment dimension
        muscle_coverage: Score for muscle coverage dimension
        discipline_preference: Score for discipline preference dimension
        compound_bonus: Score for compound bonus dimension
        specialization: Score for specialization dimension
        goal_alignment: Score for goal alignment dimension
        time_utilization: Score for time utilization dimension
    """

    pattern_alignment: float
    muscle_coverage: float
    discipline_preference: float
    compound_bonus: float
    specialization: float
    goal_alignment: float
    time_utilization: float

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> DimensionScores:
        """Create from dictionary."""
        return cls(**data)


@dataclass(frozen=True)
class ScoringMetrics:
    """Single session scoring metrics.

    Contains all metrics for a single session evaluation, including
    success determination and per-dimension scores.

    Attributes:
        session_id: ID of the evaluated session
        session_type: Type of the session (e.g., 'strength', 'cardio')
        timestamp: When the metrics were recorded
        success: Whether session met all success criteria
        movement_count: Number of unique movements in session
        time_utilization: Ratio of actual to target duration (0-1)
        pattern_diversity: Number of unique patterns used
        muscle_coverage: Number of unique muscle groups targeted
        dimension_scores: Per-dimension scoring breakdown
        failure_reasons: List of reasons for failure (if any)
        structural_completeness: Whether session has required structure
        hard_constraints_compliant: Whether all hard constraints were met
    """

    session_id: int
    session_type: str
    timestamp: datetime
    success: bool
    movement_count: int
    time_utilization: float
    pattern_diversity: int
    muscle_coverage: int
    dimension_scores: DimensionScores
    failure_reasons: tuple[str, ...] = field(default_factory=tuple)
    structural_completeness: bool = True
    hard_constraints_compliant: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of metrics.
        """
        return {
            "session_id": self.session_id,
            "session_type": self.session_type,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "movement_count": self.movement_count,
            "time_utilization": self.time_utilization,
            "pattern_diversity": self.pattern_diversity,
            "muscle_coverage": self.muscle_coverage,
            "dimension_scores": self.dimension_scores.to_dict(),
            "failure_reasons": list(self.failure_reasons),
            "structural_completeness": self.structural_completeness,
            "hard_constraints_compliant": self.hard_constraints_compliant,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScoringMetrics:
        """Create metrics from dictionary.

        Args:
            data: Dictionary containing metrics data.

        Returns:
            ScoringMetrics instance.
        """
        return cls(
            session_id=data["session_id"],
            session_type=data["session_type"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            success=data["success"],
            movement_count=data["movement_count"],
            time_utilization=data["time_utilization"],
            pattern_diversity=data["pattern_diversity"],
            muscle_coverage=data["muscle_coverage"],
            dimension_scores=DimensionScores.from_dict(data["dimension_scores"]),
            failure_reasons=tuple(data.get("failure_reasons", [])),
            structural_completeness=data.get("structural_completeness", True),
            hard_constraints_compliant=data.get("hard_constraints_compliant", True),
        )


@dataclass
class SessionContext:
    """Context information for session evaluation.

    Attributes:
        target_duration_minutes: Target duration for the session
        session_type: Type of session being evaluated
        microcycle_sessions: All sessions in the current microcycle
        user_goals: User's training goals
        available_equipment: Equipment available to user
        movement_rules: User-specific movement rules
    """

    target_duration_minutes: int
    session_type: str
    microcycle_sessions: list[dict[str, Any]] = field(default_factory=list)
    user_goals: list[str] = field(default_factory=list)
    available_equipment: list[str] = field(default_factory=list)
    movement_rules: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionResult:
    """Result of session generation containing all relevant data.

    Attributes:
        session_id: ID of the generated session
        session_type: Type of the session
        warmup_exercises: List of warmup exercise IDs
        main_exercises: List of main exercise IDs
        accessory_exercises: List of accessory exercise IDs
        finisher_exercises: List of finisher exercise IDs
        cooldown_exercises: List of cooldown exercise IDs
        estimated_duration_minutes: Estimated duration in minutes
        movements: List of Movement objects used
        patterns: List of movement patterns used
        muscle_groups: List of muscle groups targeted
        hard_constraint_violations: List of any hard constraint violations
    """

    session_id: int
    session_type: str
    warmup_exercises: list[int] = field(default_factory=list)
    main_exercises: list[int] = field(default_factory=list)
    accessory_exercises: list[int] = field(default_factory=list)
    finisher_exercises: list[int] = field(default_factory=list)
    cooldown_exercises: list[int] = field(default_factory=list)
    estimated_duration_minutes: int = 0
    movements: list[Any] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    muscle_groups: list[str] = field(default_factory=list)
    hard_constraint_violations: list[str] = field(default_factory=list)


class ScoringMetricsTracker:
    """Tracker for session scoring metrics and analysis.

    This class provides comprehensive metrics collection, storage, and analysis
    for session generation success rates and dimension effectiveness.

    The tracker:
    - Records session metrics in structured JSON format
    - Calculates success rates based on multi-criteria evaluation
    - Analyzes dimension effectiveness across sessions
    - Provides metrics aggregation and reporting

    Example:
        >>> tracker = ScoringMetricsTracker(metrics_path="metrics.json")
        >>> result = SessionResult(session_id=1, session_type="strength", ...)
        >>> context = SessionContext(target_duration_minutes=60, session_type="strength")
        >>> tracker.record_session(result, context)
        >>> success_rate = tracker.get_success_rate()
        >>> effectiveness = tracker.get_dimension_effectiveness()
    """

    def __init__(self, metrics_path: str | Path | None = None) -> None:
        """Initialize the scoring metrics tracker.

        Args:
            metrics_path: Path to JSON file for storing metrics. If None,
                metrics are kept in memory only.

        Raises:
            MetricsStorageError: If metrics file cannot be loaded.
        """
        self._metrics_path = Path(metrics_path) if metrics_path else None
        self._metrics: list[ScoringMetrics] = []
        self._load_metrics()

    def record_session(
        self, result: SessionResult, context: SessionContext
    ) -> ScoringMetrics:
        """Record metrics for a generated session.

        Evaluates the session against all success criteria and stores
        the metrics in structured format.

        Args:
            result: Session result containing generated content.
            context: Context information for evaluation.

        Returns:
            ScoringMetrics: The recorded metrics.

        Raises:
            MetricsValidationError: If validation fails.
        """
        try:
            # Calculate metrics
            movement_count = self._calculate_movement_count(result)
            time_utilization = self._calculate_time_utilization(result, context)
            pattern_diversity = self._calculate_pattern_diversity(result)
            muscle_coverage = self._calculate_muscle_coverage(result, context)

            # Evaluate success criteria
            structural_complete = self._check_structural_completeness(result)
            movement_valid = self._check_movement_count(result, context)
            time_valid = self._check_time_utilization(result, context)
            hard_constraints_valid = self._check_hard_constraints(result)

            # Determine overall success
            success = all([
                structural_complete,
                movement_valid,
                time_valid,
                hard_constraints_valid,
            ])

            # Collect failure reasons
            failure_reasons: list[str] = []
            if not structural_complete:
                failure_reasons.append("structural_incomplete")
            if not movement_valid:
                failure_reasons.append("invalid_movement_count")
            if not time_valid:
                failure_reasons.append("poor_time_utilization")
            if not hard_constraints_valid:
                failure_reasons.append("hard_constraint_violation")

            # Calculate dimension scores (simplified for now)
            dimension_scores = self._calculate_dimension_scores(result, context)

            # Create metrics object
            metrics = ScoringMetrics(
                session_id=result.session_id,
                session_type=result.session_type,
                timestamp=datetime.utcnow(),
                success=success,
                movement_count=movement_count,
                time_utilization=time_utilization,
                pattern_diversity=pattern_diversity,
                muscle_coverage=muscle_coverage,
                dimension_scores=dimension_scores,
                failure_reasons=tuple(failure_reasons),
                structural_completeness=structural_complete,
                hard_constraints_compliant=hard_constraints_valid,
            )

            # Store metrics
            self._metrics.append(metrics)

            # Persist to file if path specified
            if self._metrics_path:
                self._save_metrics()

            logger.info(
                f"Recorded metrics for session {result.session_id}: "
                f"success={success}, movement_count={movement_count}, "
                f"time_utilization={time_utilization:.2f}"
            )

            return metrics

        except Exception as e:
            raise MetricsValidationError(
                f"Failed to record metrics for session {result.session_id}: {e}"
            ) from e

    def get_success_rate(
        self, session_type: str | None = None, limit: int | None = None
    ) -> float:
        """Calculate success rate for recorded sessions.

        Success is defined as meeting ALL criteria:
        1. Structural completeness: warmup + main + (accessory/finisher) + cooldown
        2. Movement count: >=8 (regular/cardio/conditioning), <=15 (finisher = 1 unit)
        3. Time utilization: +/-5% of target duration
        4. Pattern diversity: Depends on session type (no hard number)
        5. Muscle coverage: No major muscle group missed in microcycle
        6. Hard constraint compliance: Equipment, variety, time, user rules

        Args:
            session_type: Optional filter by session type. If None, includes all.
            limit: Optional limit on number of most recent sessions to consider.

        Returns:
            Success rate as a float between 0.0 and 1.0.
        """
        # Filter metrics by session type if specified
        metrics_to_analyze = self._metrics
        if session_type:
            metrics_to_analyze = [
                m for m in metrics_to_analyze if m.session_type == session_type
            ]

        # Apply limit if specified (most recent)
        if limit and limit < len(metrics_to_analyze):
            metrics_to_analyze = metrics_to_analyze[-limit:]

        if not metrics_to_analyze:
            return 0.0

        # Calculate success rate
        successful = sum(1 for m in metrics_to_analyze if m.success)
        success_rate = successful / len(metrics_to_analyze)

        logger.debug(
            f"Success rate calculation: {successful}/{len(metrics_to_analyze)} "
            f"= {success_rate:.3f}"
        )

        return success_rate

    def get_dimension_effectiveness(
        self, session_type: str | None = None
    ) -> dict[str, dict[str, float]]:
        """Analyze which dimensions work best across sessions.

        Returns statistics for each dimension including:
        - mean: Average score
        - median: Median score
        - std: Standard deviation
        - min: Minimum score
        - max: Maximum score

        Args:
            session_type: Optional filter by session type.

        Returns:
            Dictionary mapping dimension names to their statistics.
        """
        # Filter metrics by session type if specified
        metrics_to_analyze = self._metrics
        if session_type:
            metrics_to_analyze = [
                m for m in metrics_to_analyze if m.session_type == session_type
            ]

        if not metrics_to_analyze:
            return {}

        # Collect scores per dimension
        dimension_scores: dict[str, list[float]] = defaultdict(list)
        for metrics in metrics_to_analyze:
            for dim_name, score in metrics.dimension_scores.to_dict().items():
                dimension_scores[dim_name].append(score)

        # Calculate statistics for each dimension
        effectiveness: dict[str, dict[str, float]] = {}
        for dim_name, scores in dimension_scores.items():
            if not scores:
                continue

            sorted_scores = sorted(scores)
            n = len(scores)
            mean = sum(scores) / n
            median = sorted_scores[n // 2] if n % 2 == 1 else (
                sorted_scores[n // 2 - 1] + sorted_scores[n // 2]
            ) / 2
            variance = sum((s - mean) ** 2 for s in scores) / n
            std = variance ** 0.5

            effectiveness[dim_name] = {
                "mean": round(mean, 4),
                "median": round(median, 4),
                "std": round(std, 4),
                "min": round(min(scores), 4),
                "max": round(max(scores), 4),
                "sample_size": n,
            }

        logger.debug(f"Dimension effectiveness calculated for {len(effectiveness)} dimensions")

        return effectiveness

    def get_failure_reasons(self, session_type: str | None = None) -> dict[str, int]:
        """Get count of each failure reason across sessions.

        Args:
            session_type: Optional filter by session type.

        Returns:
            Dictionary mapping failure reasons to their counts.
        """
        metrics_to_analyze = self._metrics
        if session_type:
            metrics_to_analyze = [
                m for m in metrics_to_analyze if m.session_type == session_type
            ]

        failure_counts: dict[str, int] = defaultdict(int)
        for metrics in metrics_to_analyze:
            if not metrics.success:
                for reason in metrics.failure_reasons:
                    failure_counts[reason] += 1

        return dict(failure_counts)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get overall summary of all recorded metrics.

        Returns:
            Dictionary containing summary statistics.
        """
        if not self._metrics:
            return {
                "total_sessions": 0,
                "successful_sessions": 0,
                "success_rate": 0.0,
                "by_session_type": {},
            }

        # Overall stats
        total = len(self._metrics)
        successful = sum(1 for m in self._metrics if m.success)

        # Group by session type
        by_type: dict[str, list[ScoringMetrics]] = defaultdict(list)
        for m in self._metrics:
            by_type[m.session_type].append(m)

        by_type_summary = {}
        for session_type, type_metrics in by_type.items():
            type_total = len(type_metrics)
            type_successful = sum(1 for m in type_metrics if m.success)
            by_type_summary[session_type] = {
                "total": type_total,
                "successful": type_successful,
                "success_rate": type_successful / type_total if type_total > 0 else 0.0,
            }

        return {
            "total_sessions": total,
            "successful_sessions": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_session_type": by_type_summary,
        }

    def export_metrics(self, output_path: str | Path) -> None:
        """Export all metrics to a JSON file.

        Args:
            output_path: Path to output JSON file.

        Raises:
            MetricsStorageError: If export fails.
        """
        try:
            output_file = Path(output_path)
            metrics_data = [m.to_dict() for m in self._metrics]

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)

            logger.info(f"Exported {len(metrics_data)} metrics to {output_file}")

        except Exception as e:
            raise MetricsStorageError(
                f"Failed to export metrics to {output_path}: {e}"
            ) from e

    def clear_metrics(self) -> None:
        """Clear all recorded metrics from memory and storage.

        If a metrics file path was specified, the file will be cleared.
        """
        self._metrics.clear()

        if self._metrics_path:
            try:
                with open(self._metrics_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
                logger.info(f"Cleared metrics from {self._metrics_path}")
            except Exception as e:
                logger.error(f"Failed to clear metrics file: {e}")

        logger.info("Cleared all metrics from memory")

    # Private helper methods

    def _calculate_movement_count(self, result: SessionResult) -> int:
        """Calculate total unique movement count.

        Args:
            result: Session result to analyze.

        Returns:
            Number of unique movements.
        """
        all_exercises = (
            result.warmup_exercises
            + result.main_exercises
            + result.accessory_exercises
            + result.finisher_exercises
            + result.cooldown_exercises
        )
        return len(set(all_exercises))

    def _calculate_time_utilization(
        self, result: SessionResult, context: SessionContext
    ) -> float:
        """Calculate time utilization ratio.

        Args:
            result: Session result to analyze.
            context: Session context with target duration.

        Returns:
            Time utilization ratio (0-1, where 1.0 = perfect match).
        """
        if context.target_duration_minutes == 0:
            return 0.0

        actual = result.estimated_duration_minutes
        target = context.target_duration_minutes

        # Calculate ratio, capped at reasonable bounds
        ratio = actual / target if target > 0 else 0.0

        # Clamp to [0, 2] range for practical purposes
        return max(0.0, min(2.0, ratio))

    def _calculate_pattern_diversity(self, result: SessionResult) -> int:
        """Calculate pattern diversity (unique patterns).

        Args:
            result: Session result to analyze.

        Returns:
            Number of unique patterns.
        """
        return len(set(result.patterns))

    def _calculate_muscle_coverage(
        self, result: SessionResult, context: SessionContext
    ) -> int:
        """Calculate muscle coverage (unique muscle groups).

        Args:
            result: Session result to analyze.
            context: Session context with microcycle information.

        Returns:
            Number of unique muscle groups covered.
        """
        return len(set(result.muscle_groups))

    def _calculate_dimension_scores(
        self, result: SessionResult, context: SessionContext
    ) -> DimensionScores:
        """Calculate scores for each dimension.

        This is a simplified implementation. In production, this would
        use the actual GlobalMovementScorer to calculate dimension scores.

        Args:
            result: Session result to analyze.
            context: Session context.

        Returns:
            DimensionScores object with per-dimension scores.
        """
        # Simplified scoring based on available data
        # In production, integrate with GlobalMovementScorer

        pattern_alignment = 0.7  # Placeholder
        muscle_coverage_score = 0.6  # Placeholder
        discipline_preference = 0.8  # Placeholder
        compound_bonus = 0.5  # Placeholder
        specialization = 0.7  # Placeholder
        goal_alignment = 0.6  # Placeholder
        time_utilization = min(1.0, self._calculate_time_utilization(result, context))

        return DimensionScores(
            pattern_alignment=pattern_alignment,
            muscle_coverage=muscle_coverage_score,
            discipline_preference=discipline_preference,
            compound_bonus=compound_bonus,
            specialization=specialization,
            goal_alignment=goal_alignment,
            time_utilization=time_utilization,
        )

    @final
    def _check_structural_completeness(self, result: SessionResult) -> bool:
        """Check if session has required structural components.

        Criteria: warmup + main + (accessory OR finisher) + cooldown

        Args:
            result: Session result to check.

        Returns:
            True if structurally complete, False otherwise.
        """
        has_warmup = len(result.warmup_exercises) > 0
        has_main = len(result.main_exercises) > 0
        has_accessory_or_finisher = (
            len(result.accessory_exercises) > 0 or len(result.finisher_exercises) > 0
        )
        has_cooldown = len(result.cooldown_exercises) > 0

        return has_warmup and has_main and has_accessory_or_finisher and has_cooldown

    @final
    def _check_movement_count(self, result: SessionResult, context: SessionContext) -> bool:
        """Check if movement count meets requirements.

        Criteria:
        - Regular/cardio/conditioning: >= 8 movements
        - Finisher sessions: <= 15 (finisher = 1 unit)

        Args:
            result: Session result to check.
            context: Session context.

        Returns:
            True if movement count is valid, False otherwise.
        """
        movement_count = self._calculate_movement_count(result)

        # Check if finisher session (special handling)
        if context.session_type.lower() in SessionTypes.FINISHER_TYPES:
            return movement_count <= MovementCounts.MAX_SESSION_MOVEMENTS

        # Regular sessions need minimum movement count
        return movement_count >= MovementCounts.MIN_SESSION_MOVEMENTS

    @final
    def _check_time_utilization(self, result: SessionResult, context: SessionContext) -> bool:
        """Check if time utilization is within acceptable range.

        Criteria: +/- 5% of target duration

        Args:
            result: Session result to check.
            context: Session context.

        Returns:
            True if time utilization is acceptable, False otherwise.
        """
        if context.target_duration_minutes == 0:
            return True  # Can't validate if no target

        actual = result.estimated_duration_minutes
        target = context.target_duration_minutes

        # Calculate percentage difference
        pct_diff = abs(actual - target) / target if target > 0 else 1.0

        # Check if within tolerance
        return pct_diff <= TimeUtilization.TOLERANCE_PERCENT

    @final
    def _check_hard_constraints(self, result: SessionResult) -> bool:
        """Check if all hard constraints were satisfied.

        Criteria: Equipment, variety, time, user rules

        Args:
            result: Session result to check.

        Returns:
            True if all hard constraints satisfied, False otherwise.
        """
        return len(result.hard_constraint_violations) == 0

    def _load_metrics(self) -> None:
        """Load existing metrics from file if path specified.

        Raises:
            MetricsStorageError: If loading fails.
        """
        if not self._metrics_path or not self._metrics_path.exists():
            return

        try:
            with open(self._metrics_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._metrics = [ScoringMetrics.from_dict(m) for m in data]
            logger.info(f"Loaded {len(self._metrics)} metrics from {self._metrics_path}")

        except json.JSONDecodeError as e:
            raise MetricsStorageError(
                f"Invalid JSON in metrics file {self._metrics_path}: {e}"
            ) from e
        except Exception as e:
            raise MetricsStorageError(
                f"Failed to load metrics from {self._metrics_path}: {e}"
            ) from e

    def _save_metrics(self) -> None:
        """Save current metrics to file.

        Raises:
            MetricsStorageError: If saving fails.
        """
        if not self._metrics_path:
            return

        try:
            metrics_data = [m.to_dict() for m in self._metrics]

            # Create parent directory if needed
            self._metrics_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics_data, f, indent=2)

            logger.debug(f"Saved {len(metrics_data)} metrics to {self._metrics_path}")

        except Exception as e:
            raise MetricsStorageError(
                f"Failed to save metrics to {self._metrics_path}: {e}"
            ) from e
