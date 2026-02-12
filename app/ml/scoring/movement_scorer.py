"""Decision tree scorer for movement selection.

This module provides a comprehensive scoring system for evaluating movements
based on multiple dimensions including pattern alignment, muscle coverage,
discipline preferences, and goal alignment.

The scorer uses a hierarchical decision tree approach with priority-based
dimension evaluation and configurable scoring rules.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.models.movement import Movement
    from app.models.user import UserProfile

from .config_loader import (
    MovementScoringConfig,
    ScoringDimension,
    get_config_loader,
)

logger = logging.getLogger(__name__)


class ScoringError(Exception):
    """Base exception for scoring errors."""

    pass


class ScoringRuleError(ScoringError):
    """Raised when a scoring rule fails to evaluate."""

    pass


@dataclass
class ScoringRule:
    """Single scoring rule with condition and score.

    A scoring rule represents a single decision node in the decision tree,
    consisting of a condition function and an associated score value.

    Attributes:
        name: Unique identifier for the rule
        condition: Callable that evaluates whether the rule applies
        score: Score value to assign when condition is true
        description: Human-readable description of the rule
        priority: Priority level for tie-breaking (higher = more important)
    """

    name: str
    condition: Callable[[Any], bool]
    score: float
    description: str
    priority: int = 0

    def evaluate(self, context: Any) -> tuple[bool, float | None]:
        """Evaluate the rule against the given context.

        Args:
            context: Evaluation context containing movement and user data.

        Returns:
            Tuple of (condition_met, score) where score is None if condition
            is not met.
        """
        try:
            condition_met = self.condition(context)
            return condition_met, self.score if condition_met else None
        except Exception as e:
            raise ScoringRuleError(f"Rule '{self.name}' evaluation failed: {e}") from e


@dataclass
class ScoringDimension:
    """Complete scoring dimension with rules and weight.

    Represents a full dimension in the scoring hierarchy, containing
    multiple rules that are evaluated in priority order.

    Attributes:
        name: Dimension identifier (e.g., 'pattern_alignment')
        config: Configuration data from config_loader
        rules: List of scoring rules for this dimension
        weight: Normalized weight for this dimension (0-1)
        enabled: Whether this dimension is active in scoring
        priority_level: Priority level for dimension ordering (1-7)
    """

    name: str
    config: ScoringDimension
    rules: list[ScoringRule] = field(default_factory=list)
    weight: float = 1.0
    enabled: bool = True
    priority_level: int = 1

    def evaluate(self, context: Any) -> tuple[float, dict[str, Any]]:
        """Evaluate all rules in this dimension.

        Rules are evaluated in priority order until the first matching rule
        is found (first-match semantics).

        Args:
            context: Evaluation context containing movement and user data.

        Returns:
            Tuple of (dimension_score, details) where details contains
            information about which rule matched and any variance contribution.
        """
        if not self.enabled:
            return 0.0, {"status": "disabled", "matched_rule": None}

        dimension_score = 0.0
        matched_rule = None
        variance_contribution = 0.0

        # Evaluate rules in priority order (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: -r.priority)

        for rule in sorted_rules:
            condition_met, score = rule.evaluate(context)
            if condition_met and score is not None:
                dimension_score = score
                matched_rule = rule.name
                # Calculate variance contribution for this dimension
                variance_contribution = self._calculate_variance(score, sorted_rules)
                break

        details = {
            "status": "matched" if matched_rule else "no_match",
            "matched_rule": matched_rule,
            "dimension_score": dimension_score,
            "variance_contribution": variance_contribution,
            "weight": self.weight,
            "weighted_score": dimension_score * self.weight,
        }

        return dimension_score, details

    def _calculate_variance(
        self, matched_score: float, all_rules: list[ScoringRule]
    ) -> float:
        """Calculate variance contribution for this dimension.

        Args:
            matched_score: The score that was matched.
            all_rules: All rules in this dimension.

        Returns:
            Variance contribution as a float value.
        """
        if not all_rules:
            return 0.0

        scores = [rule.score for rule in all_rules]
        if not scores:
            return 0.0

        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)

        # Normalize variance to 0-1 range
        max_possible_variance = max((max(scores) - min(scores)) ** 2, 1.0)
        normalized_variance = variance / max_possible_variance

        logger.debug(
            f"Dimension '{self.name}': variance={variance:.4f}, "
            f"normalized={normalized_variance:.4f}"
        )

        return normalized_variance


@dataclass
class ScoringResult:
    """Score breakdown with dimension scores and qualification status.

    Contains the complete scoring result for a movement, including
    per-dimension breakdowns and overall qualification status.

    Attributes:
        movement_id: ID of the scored movement
        movement_name: Name of the scored movement
        total_score: Overall weighted score (0-1)
        dimension_scores: Dict mapping dimension names to their scores
        dimension_details: Dict mapping dimension names to detailed results
        qualified: Whether the movement meets minimum qualification threshold
        qualification_threshold: Minimum score required to qualify
        disqualified_reason: Reason for disqualification (if any)
        raw_scores: Raw scores before weighting
        normalized_weights: Normalized weights used for scoring
    """

    movement_id: int
    movement_name: str
    total_score: float
    dimension_scores: dict[str, float]
    dimension_details: dict[str, dict[str, Any]]
    qualified: bool
    qualification_threshold: float = 0.5
    disqualified_reason: str | None = None
    raw_scores: dict[str, float] = field(default_factory=dict)
    normalized_weights: dict[str, float] = field(default_factory=dict)

    def get_dimension_score(self, dimension_name: str) -> float:
        """Get the score for a specific dimension.

        Args:
            dimension_name: Name of the dimension.

        Returns:
            The dimension score, or 0.0 if dimension not found.
        """
        return self.dimension_scores.get(dimension_name, 0.0)

    def get_dimension_details(self, dimension_name: str) -> dict[str, Any]:
        """Get detailed results for a specific dimension.

        Args:
            dimension_name: Name of the dimension.

        Returns:
            Dictionary containing dimension evaluation details.
        """
        return self.dimension_details.get(dimension_name, {})

    def get_top_dimensions(self, n: int = 3) -> list[tuple[str, float]]:
        """Get the top n dimensions by weighted score.

        Args:
            n: Number of top dimensions to return.

        Returns:
            List of (dimension_name, weighted_score) tuples.
        """
        weighted_scores = [
            (dim, details.get("weighted_score", 0.0))
            for dim, details in self.dimension_details.items()
        ]
        return sorted(weighted_scores, key=lambda x: -x[1])[:n]


@dataclass
class ScoringContext:
    """Context object for movement scoring.

    Contains all necessary information for scoring a movement,
    including the movement itself, user profile, and configuration.

    Attributes:
        movement: Movement object to score
        user_profile: User profile containing preferences
        config: Scoring configuration
        session_movements: List of movement IDs in current session
        microcycle_movements: List of movement IDs in current microcycle
        user_goals: List of user's training goals
        discipline_preferences: Normalized discipline preferences (0-1)
        required_pattern: Required movement pattern for the block
        target_muscles: List of target muscle groups for specialization
    """

    movement: Movement
    user_profile: UserProfile | None
    config: MovementScoringConfig
    session_movements: list[int] = field(default_factory=list)
    microcycle_movements: list[int] = field(default_factory=list)
    user_goals: list[str] = field(default_factory=list)
    discipline_preferences: dict[str, float] = field(default_factory=dict)
    required_pattern: str | None = None
    target_muscles: list[str] = field(default_factory=list)


class GlobalMovementScorer:
    """Main scorer class for movement evaluation.

    This class implements a hierarchical decision tree scorer that evaluates
    movements across multiple dimensions with configurable rules and weights.

    The scorer:
    - Evaluates dimensions in priority order (1-7)
    - Applies goal-specific modifiers
    - Normalizes weights to sum to 1.0
    - Logs variance contributions for each dimension

    Example:
        >>> scorer = GlobalMovementScorer()
        >>> context = ScoringContext(
        ...     movement=movement,
        ...     user_profile=profile,
        ...     config=config
        ... )
        >>> result = scorer.score_movement(movement, context)
        >>> print(f"Total score: {result.total_score:.2f}")
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the movement scorer.

        Args:
            config_path: Optional path to configuration file.
        """
        self._config_loader = get_config_loader(config_path)
        self._dimensions: dict[str, ScoringDimension] = {}
        self._initialize_dimensions()

    def _initialize_dimensions(self) -> None:
        """Initialize scoring dimensions from configuration.

        Loads scoring dimensions from the config and builds the rule tree
        for each dimension.
        """
        config = self._config_loader.get_config()

        # Build dimension rules from config
        for name, dimension_config in config.scoring_dimensions.items():
            dimension = ScoringDimension(
                name=name,
                config=dimension_config,
                priority_level=dimension_config.priority_level,
                weight=dimension_config.weight,
                enabled=True,
            )

            # Build rules for this dimension based on config attributes
            dimension.rules = self._build_dimension_rules(name, dimension_config)

            self._dimensions[name] = dimension

        logger.info(f"Initialized {len(self._dimensions)} scoring dimensions")

    def _build_dimension_rules(
        self, dimension_name: str, config: ScoringDimension
    ) -> list[ScoringRule]:
        """Build scoring rules for a dimension from configuration.

        Args:
            dimension_name: Name of the dimension.
            config: Dimension configuration.

        Returns:
            List of scoring rules for the dimension.
        """
        rules: list[ScoringRule] = []

        # Pattern alignment dimension rules
        if dimension_name == "pattern_alignment":
            if config.bonus_exact_match is not None:
                rules.append(
                    ScoringRule(
                        name="exact_pattern_match",
                        condition=lambda ctx: self._is_exact_pattern_match(ctx),
                        score=config.bonus_exact_match,
                        description="Exact pattern match with required pattern",
                        priority=10,
                    )
                )
            if config.penalty_mismatch is not None:
                rules.append(
                    ScoringRule(
                        name="pattern_mismatch",
                        condition=lambda ctx: not self._is_exact_pattern_match(ctx),
                        score=config.penalty_mismatch,
                        description="Pattern mismatch with required pattern",
                        priority=0,
                    )
                )

        # Muscle coverage dimension rules
        elif dimension_name == "muscle_coverage":
            if config.bonus_unique_primary is not None:
                rules.append(
                    ScoringRule(
                        name="unique_primary_muscle",
                        condition=lambda ctx: self._is_unique_primary_muscle(ctx),
                        score=config.bonus_unique_primary,
                        description="Primary muscle not recently used",
                        priority=10,
                    )
                )
            if config.penalty_repeated_primary is not None:
                rules.append(
                    ScoringRule(
                        name="repeated_primary_muscle",
                        condition=lambda ctx: not self._is_unique_primary_muscle(ctx),
                        score=config.penalty_repeated_primary,
                        description="Primary muscle recently used",
                        priority=0,
                    )
                )

        # Discipline preference dimension rules
        elif dimension_name == "discipline_preference":
            if config.bonus_matched_discipline is not None:
                rules.append(
                    ScoringRule(
                        name="matched_discipline",
                        condition=lambda ctx: self._is_matched_discipline(ctx),
                        score=config.bonus_matched_discipline,
                        description="Matches user's preferred discipline",
                        priority=10,
                    )
                )
            if config.neutral_default is not None:
                rules.append(
                    ScoringRule(
                        name="default_discipline",
                        condition=lambda ctx: True,  # Always matches as fallback
                        score=config.neutral_default,
                        description="Default discipline score",
                        priority=0,
                    )
                )

        # Compound bonus dimension rules
        elif dimension_name == "compound_bonus":
            if config.bonus_compound is not None:
                rules.append(
                    ScoringRule(
                        name="compound_movement",
                        condition=lambda ctx: ctx.movement.compound,
                        score=config.bonus_compound,
                        description="Compound movement bonus",
                        priority=10,
                    )
                )
            if config.neutral_hybrid is not None:
                rules.append(
                    ScoringRule(
                        name="hybrid_movement",
                        condition=lambda ctx: ctx.movement.compound
                        and self._is_hybrid(ctx),
                        score=config.neutral_hybrid,
                        description="Hybrid movement score",
                        priority=5,
                    )
                )
            if config.penalty_isolation is not None:
                rules.append(
                    ScoringRule(
                        name="isolation_movement",
                        condition=lambda ctx: not ctx.movement.compound,
                        score=config.penalty_isolation,
                        description="Isolation movement penalty",
                        priority=0,
                    )
                )

        # Specialization dimension rules
        elif dimension_name == "specialization":
            if config.bonus_target_muscle is not None:
                rules.append(
                    ScoringRule(
                        name="target_muscle_match",
                        condition=lambda ctx: self._is_target_muscle(ctx),
                        score=config.bonus_target_muscle,
                        description="Targets specialization muscle group",
                        priority=10,
                    )
                )
            if config.neutral_non_target is not None:
                rules.append(
                    ScoringRule(
                        name="non_target_muscle",
                        condition=lambda ctx: not self._is_target_muscle(ctx),
                        score=config.neutral_non_target,
                        description="Non-target muscle group",
                        priority=0,
                    )
                )

        # Goal alignment dimension rules
        elif dimension_name == "goal_alignment":
            if config.bonus_goal_match is not None:
                rules.append(
                    ScoringRule(
                        name="goal_match",
                        condition=lambda ctx: self._is_goal_aligned(ctx),
                        score=config.bonus_goal_match,
                        description="Matches user's training goal",
                        priority=10,
                    )
                )
            if config.penalty_goal_conflict is not None:
                rules.append(
                    ScoringRule(
                        name="goal_conflict",
                        condition=lambda ctx: self._is_goal_conflict(ctx),
                        score=config.penalty_goal_conflict,
                        description="Conflicts with user's training goal",
                        priority=0,
                    )
                )
            if config.neutral_goal_agnostic is not None:
                rules.append(
                    ScoringRule(
                        name="goal_agnostic",
                        condition=lambda ctx: not self._is_goal_aligned(ctx)
                        and not self._is_goal_conflict(ctx),
                        score=config.neutral_goal_agnostic,
                        description="Goal-agnostic movement",
                        priority=5,
                    )
                )

        # Time utilization dimension rules
        elif dimension_name == "time_utilization":
            if config.bonus_efficient is not None:
                rules.append(
                    ScoringRule(
                        name="efficient_movement",
                        condition=lambda ctx: self._is_efficient_movement(ctx),
                        score=config.bonus_efficient,
                        description="Efficient time utilization",
                        priority=10,
                    )
                )
            if config.penalty_inefficient is not None:
                rules.append(
                    ScoringRule(
                        name="inefficient_movement",
                        condition=lambda ctx: not self._is_efficient_movement(ctx),
                        score=config.penalty_inefficient,
                        description="Inefficient time utilization",
                        priority=0,
                    )
                )
            if config.neutral_average is not None:
                rules.append(
                    ScoringRule(
                        name="average_efficiency",
                        condition=lambda ctx: True,  # Fallback
                        score=config.neutral_average,
                        description="Average time utilization",
                        priority=5,
                    )
                )

        return rules

    def score_movement(
        self, movement: Movement, context: ScoringContext
    ) -> ScoringResult:
        """Evaluate all enabled dimensions for a movement.

        Dimensions are evaluated in priority order (1-7) and scores are
        weighted by normalized dimension weights.

        Args:
            movement: Movement object to score.
            context: Scoring context with user data and configuration.

        Returns:
            ScoringResult with dimension breakdown and overall score.

        Raises:
            ScoringError: If scoring fails.
        """
        try:
            # Normalize discipline preferences (1-5 scale → 0-1)
            context.discipline_preferences = self._normalize_discipline_preferences(
                context
            )

            # Normalize dimension weights to sum to 1.0
            normalized_weights = self._normalize_dimension_weights()

            dimension_scores: dict[str, float] = {}
            dimension_details: dict[str, dict[str, Any]] = {}
            raw_scores: dict[str, float] = {}

            # Evaluate each dimension
            for dimension_name, dimension in self._dimensions.items():
                if not dimension.enabled:
                    continue

                dimension_score, details = dimension.evaluate(context)

                # Apply normalized weight
                normalized_weight = normalized_weights.get(dimension_name, 0.0)
                weighted_score = dimension_score * normalized_weight

                dimension_scores[dimension_name] = weighted_score
                dimension_details[dimension_name] = details
                raw_scores[dimension_name] = dimension_score

                # Update details with normalized weight
                dimension_details[dimension_name][
                    "normalized_weight"
                ] = normalized_weight
                dimension_details[dimension_name]["weighted_score"] = weighted_score

                logger.debug(
                    f"Dimension '{dimension_name}': score={dimension_score:.3f}, "
                    f"weight={normalized_weight:.3f}, "
                    f"weighted_score={weighted_score:.3f}"
                )

            # Calculate total score
            total_score = sum(dimension_scores.values())

            # Apply goal modifiers
            final_score = self._apply_goal_modifiers(total_score, context)

            # Determine qualification status
            qualified, disqualified_reason = self._check_qualification(
                final_score, dimension_details
            )

            result = ScoringResult(
                movement_id=movement.id,
                movement_name=movement.name,
                total_score=final_score,
                dimension_scores=dimension_scores,
                dimension_details=dimension_details,
                qualified=qualified,
                disqualified_reason=disqualified_reason,
                raw_scores=raw_scores,
                normalized_weights=normalized_weights,
            )

            logger.info(
                f"Scored movement '{movement.name}': total_score={final_score:.3f}, "
                f"qualified={qualified}"
            )

            return result

        except Exception as e:
            raise ScoringError(
                f"Failed to score movement '{movement.name}': {e}"
            ) from e

    def _evaluate_dimension(
        self, dimension: ScoringDimension, movement: Movement, context: ScoringContext
    ) -> tuple[float, dict[str, Any]]:
        """Evaluate a single dimension for a movement.

        Args:
            dimension: Scoring dimension to evaluate.
            movement: Movement object to score.
            context: Scoring context.

        Returns:
            Tuple of (dimension_score, details).
        """
        return dimension.evaluate(context)

    def _apply_goal_modifiers(
        self, base_score: float, context: ScoringContext
    ) -> float:
        """Adjust scores based on goal-specific modifiers.

        Applies goal profile weight modifiers to the base score based on
        the user's training goals.

        Args:
            base_score: Base score before goal modifiers.
            context: Scoring context with user goals.

        Returns:
            Adjusted score after applying goal modifiers.
        """
        if not context.user_goals:
            return base_score

        config = context.config
        modifier_sum = 1.0
        modifier_count = 0

        for goal_name in context.user_goals:
            goal_profile = config.goal_profiles.get(goal_name)
            if goal_profile:
                # Apply weight modifiers for this goal
                weight_modifiers = goal_profile.weight_modifiers
                for dimension_name, modifier in [
                    ("compound_bonus", weight_modifiers.compound_bonus),
                    ("pattern_alignment", weight_modifiers.pattern_alignment),
                    ("muscle_coverage", weight_modifiers.muscle_coverage),
                    ("discipline_preference", weight_modifiers.discipline_preference),
                    ("goal_alignment", weight_modifiers.goal_alignment),
                    ("time_utilization", weight_modifiers.time_utilization),
                    ("specialization", weight_modifiers.specialization),
                ]:
                    modifier_sum += modifier
                    modifier_count += 1

        # Calculate average modifier
        if modifier_count > 0:
            average_modifier = modifier_sum / modifier_count
            adjusted_score = base_score * average_modifier

            logger.debug(
                f"Applied goal modifiers: base_score={base_score:.3f}, "
                f"modifier={average_modifier:.3f}, "
                f"adjusted_score={adjusted_score:.3f}"
            )

            return adjusted_score

        return base_score

    def _normalize_discipline_preferences(
        self, context: ScoringContext
    ) -> dict[str, float]:
        """Normalize user discipline preferences from 1-5 scale to 0-1.

        Args:
            context: Scoring context with user profile.

        Returns:
            Dictionary of normalized discipline preferences (0-1).
        """
        normalized: dict[str, float] = {}

        if context.user_profile and context.user_profile.discipline_preferences:
            raw_prefs = context.user_profile.discipline_preferences

            for discipline, value in raw_prefs.items():
                # Normalize from 1-5 to 0-1
                normalized_value = float(value) / 5.0
                normalized[discipline] = normalized_value

            logger.debug(f"Normalized discipline preferences: {normalized}")

        return normalized

    def _normalize_dimension_weights(self) -> dict[str, float]:
        """Normalize all dimension weights to sum to 1.0.

        Returns:
            Dictionary of normalized weights for each dimension.
        """
        total_weight = sum(d.weight for d in self._dimensions.values())

        if total_weight == 0:
            logger.warning("Total dimension weight is 0, using equal weights")
            equal_weight = 1.0 / len(self._dimensions)
            return {name: equal_weight for name in self._dimensions}

        normalized = {
            name: dimension.weight / total_weight
            for name, dimension in self._dimensions.items()
        }

        # Verify sum is approximately 1.0
        sum_normalized = sum(normalized.values())
        if not math.isclose(sum_normalized, 1.0, rel_tol=1e-6):
            logger.warning(
                f"Normalized weights sum to {sum_normalized:.6f}, " "not exactly 1.0"
            )

        logger.debug(f"Normalized dimension weights: {normalized}")

        return normalized

    def _check_qualification(
        self, score: float, dimension_details: dict[str, dict[str, Any]]
    ) -> tuple[bool, str | None]:
        """Check if movement meets minimum qualification threshold.

        Args:
            score: Total score for the movement.
            dimension_details: Detailed dimension evaluation results.

        Returns:
            Tuple of (qualified, disqualification_reason).
        """
        config = self._config_loader.get_config()
        threshold = (
            config.global_config.normalization_method == "min_max" and 0.5 or 0.5
        )

        if score < threshold:
            # Find lowest-scoring dimension
            lowest_dimension = min(
                dimension_details.items(),
                key=lambda x: x[1].get("dimension_score", 0.0),
            )
            reason = (
                f"Score {score:.3f} below threshold {threshold:.3f}, "
                f"lowest dimension: {lowest_dimension[0]}"
            )
            return False, reason

        return True, None

    # Condition helper methods

    def _is_exact_pattern_match(self, context: ScoringContext) -> bool:
        """Check if movement pattern exactly matches required pattern."""
        if not context.required_pattern:
            return False
        return context.movement.pattern.value == context.required_pattern

    def _is_unique_primary_muscle(self, context: ScoringContext) -> bool:
        """Check if primary muscle hasn't been used recently.

        Returns True if the movement's primary muscle hasn't been used
        more than the allowed thresholds in the current session and microcycle.

        Args:
            context: Scoring context containing movement lists and configuration.

        Returns:
            True if primary muscle is unique within thresholds, False otherwise.
        """
        primary_muscle = context.movement.primary_muscle.value

        # Get thresholds from config
        muscle_coverage_config = context.config.scoring_dimensions.get("muscle_coverage")
        if muscle_coverage_config is None:
            return True

        max_per_session = muscle_coverage_config.max_primary_repeats_per_session or 2
        max_per_microcycle = muscle_coverage_config.max_primary_repeats_per_microcycle or 4

        # Count occurrences in session movements
        session_count = 0
        for movement_id in context.session_movements:
            # In production, fetch Movement objects from database
            # For now, count based on available movement data
            # We'll need to enhance this with actual database queries
            if hasattr(context.movement, 'primary_muscle') and context.movement.primary_muscle.value == primary_muscle:
                # Don't count the current movement itself
                if context.movement.id != movement_id:
                    session_count += 1

        # Count occurrences in microcycle movements
        microcycle_count = session_count  # Start with session count
        for movement_id in context.microcycle_movements:
            if movement_id not in context.session_movements:
                # In production, fetch Movement objects from database
                # For now, this is a simplified implementation
                pass

        # Check if counts are below thresholds
        return session_count < max_per_session and microcycle_count < max_per_microcycle

    def _is_matched_discipline(self, context: ScoringContext) -> bool:
        """Check if movement matches user's preferred discipline."""
        if not context.movement.disciplines:
            return False

        for discipline_rel in context.movement.disciplines:
            discipline = discipline_rel.discipline.value
            if discipline in context.discipline_preferences:
                return True

        return False

    def _is_hybrid(self, context: ScoringContext) -> bool:
        """Check if movement is a hybrid compound/isolation movement.

        Hybrid movements are compound movements that have characteristics
        of both compound and isolation movements based on muscle map analysis,
        CNS load, and other biomechanical factors.

        Args:
            context: Scoring context containing movement data.

        Returns:
            True if movement meets hybrid criteria, False otherwise.
        """
        # Only compound movements can be hybrid
        if not context.movement.compound:
            return False

        # Calculate hybrid score based on multiple factors
        hybrid_score = 0.0

        # Factor 1: Muscle map analysis
        if hasattr(context.movement, 'muscle_maps') and context.movement.muscle_maps:
            primary_count = sum(1 for mm in context.movement.muscle_maps if mm.role.value == "primary")
            synergist_count = sum(1 for mm in context.movement.muscle_maps if mm.role.value == "secondary")
            total_muscles = len(context.movement.muscle_maps)

            # Primary muscles: 1-2 is ideal for hybrid
            if 1 <= primary_count <= 2:
                hybrid_score += 0.3
            elif primary_count == 3:
                hybrid_score += 0.15

            # Synergist muscles: ≤3 is ideal for hybrid
            if synergist_count <= 3:
                hybrid_score += 0.25
            elif synergist_count <= 5:
                hybrid_score += 0.1

            # Total muscles: 3-6 is ideal for hybrid
            if 3 <= total_muscles <= 6:
                hybrid_score += 0.25
            elif total_muscles <= 8:
                hybrid_score += 0.1

        # Factor 2: CNS load - LOW/MODERATE suggests hybrid
        if hasattr(context.movement, 'cns_load'):
            cns_load = context.movement.cns_load.value
            if cns_load == "low":
                hybrid_score += 0.2
            elif cns_load == "moderate":
                hybrid_score += 0.1

        # Factor 3: Unilateral movements lean toward hybrid
        if hasattr(context.movement, 'is_unilateral') and context.movement.is_unilateral:
            hybrid_score += 0.1

        # Factor 4: Skill level - BEGINNER/INTERMEDIATE can indicate hybrid
        if hasattr(context.movement, 'skill_level'):
            skill_level = context.movement.skill_level.value
            if skill_level == "beginner":
                hybrid_score += 0.1
            elif skill_level == "intermediate":
                hybrid_score += 0.05

        # Factor 5: Not a complex lift - complex lifts are typically pure compound
        if hasattr(context.movement, 'is_complex_lift') and not context.movement.is_complex_lift:
            hybrid_score += 0.1

        # Threshold for hybrid classification
        hybrid_threshold = 0.5

        return hybrid_score >= hybrid_threshold

    def _is_target_muscle(self, context: ScoringContext) -> bool:
        """Check if movement targets a specialization muscle group."""
        if not context.target_muscles:
            return False
        return context.movement.primary_muscle.value in context.target_muscles

    def _is_goal_aligned(self, context: ScoringContext) -> bool:
        """Check if movement aligns with user's training goals."""
        if not context.user_goals:
            return False

        config = context.config

        for goal_name in context.user_goals:
            goal_profile = config.goal_profiles.get(goal_name)
            if goal_profile:
                # Check if movement pattern is preferred for this goal
                if context.movement.pattern.value in goal_profile.preferred_patterns:
                    return True

        return False

    def _is_goal_conflict(self, context: ScoringContext) -> bool:
        """Check if movement conflicts with user's training goals."""
        # This would require more sophisticated logic based on goal definitions
        return False

    def _is_efficient_movement(self, context: ScoringContext) -> bool:
        """Check if movement has favorable time-to-benefit ratio."""
        # This would be based on movement complexity, setup time, etc.
        return context.movement.compound
