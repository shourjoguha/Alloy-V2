"""
Greedy Optimization Service

This module implements a greedy movement selection algorithm as an alternative
to OR-Tools constraint solver. Uses GlobalMovementScorer for
multi-dimensional evaluation and progressive relaxation for constraint satisfaction.

Benefits over OR-Tools:
- O(n log n) complexity vs exponential
- Deterministic and reproducible
- Easier to debug and reason about
- No external dependency on OR-Tools
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from app.config.optimization_config_loader import get_optimization_config
from app.ml.scoring.movement_scorer import (
    GlobalMovementScorer,
    ScoringContext,
    ScoringResult,
)
from app.models.enums import CircuitType, SkillLevel
from app.models.movement import Movement
from app.models.user import UserProfile

if TYPE_CHECKING:
    from app.services.optimization_types import (
        OptimizationRequestV2,
        OptimizationResultV2,
        SolverCircuit,
        SolverMovement,
    )
else:
    from app.services.optimization_types import (
        OptimizationRequestV2,
        OptimizationResultV2,
        SolverCircuit,
        SolverMovement,
    )


logger = logging.getLogger(__name__)


class RelaxationConfig:
    """Configuration for progressive relaxation steps loaded from unified config."""

    def __init__(self):
        config = get_optimization_config()
        self.pattern_compatibility_expansion: bool = False
        self.include_synergist_muscles: bool = False
        self.discipline_weight_multiplier: float = 1.0
        self.allow_isolation_movements: bool = False
        self.allow_generic_movements: bool = False
        self.emergency_mode: bool = False
        self._config = config

    def apply_step(self, step: int) -> None:
        """Apply relaxation settings for a given step from unified config."""
        step_config = self._config.get_relaxation_step(step)
        self.pattern_compatibility_expansion = step_config.pattern_compatibility_expansion
        self.include_synergist_muscles = step_config.include_synergist_muscles
        self.discipline_weight_multiplier = step_config.discipline_weight_multiplier
        self.allow_isolation_movements = step_config.allow_isolation_movements
        self.allow_generic_movements = step_config.allow_generic_movements
        self.emergency_mode = step_config.emergency_mode

    def reset(self) -> None:
        """Reset to initial (strict) configuration."""
        step_config = self._config.get_relaxation_step(0)
        self.pattern_compatibility_expansion = step_config.pattern_compatibility_expansion
        self.include_synergist_muscles = step_config.include_synergist_muscles
        self.discipline_weight_multiplier = step_config.discipline_weight_multiplier
        self.allow_isolation_movements = step_config.allow_isolation_movements
        self.allow_generic_movements = step_config.allow_generic_movements
        self.emergency_mode = step_config.emergency_mode


class GreedyOptimizationService:
    """Greedy movement selection service using GlobalMovementScorer.

    This service replaces OR-Tools constraint solver with a deterministic
    greedy algorithm that selects movements based on multi-dimensional scores.

    Algorithm:
    1. Pre-score all movements using GlobalMovementScorer
    2. Sort movements by total_score descending
    3. Iteratively select highest-scoring movements that satisfy constraints
    4. Track remaining budgets (volume, fatigue, time, equipment)
    5. Apply progressive relaxation if no solution found

    Progressive relaxation strategy matches optimization_v2.py:
    - Step 0: Strict mode - all constraints enforced
    - Step 1: Expand pattern compatibility matrix
    - Step 2: Include synergist muscles in volume calculation
    - Step 3: Reduce discipline weight by 30%
    - Step 4: Accept isolation movements
    - Step 5: Accept generic movements (low tier)
    - Step 6: Emergency mode - minimal constraints

    Example:
        >>> service = GreedyOptimizationService()
        >>> request = OptimizationRequestV2(...)
        >>> result = service.solve_session(request)
        >>> print(f"Selected {len(result.selected_movements)} movements")
    """

    def __init__(self, scorer: GlobalMovementScorer | None = None):
        """Initialize greedy optimization service.

        Args:
            scorer: Optional GlobalMovementScorer instance. If not provided,
                   a new one will be instantiated.
        """
        self._scorer = scorer or GlobalMovementScorer()
        self._relaxation_config = RelaxationConfig()
        self._config = get_optimization_config()
        logger.info("GreedyOptimizationService initialized")

    def solve_session_with_diversity_scoring(
        self, request: OptimizationRequestV2
    ) -> OptimizationResultV2:
        """Solve for optimal movements using greedy selection.

        This is an alias for solve_session to maintain compatibility with
        existing tests and code that references the old method name.
        """
        return self._solve_with_config(request, 0)

    def solve_session(
        self, request: OptimizationRequestV2
    ) -> OptimizationResultV2:
        """Solve for optimal movements using greedy selection.

        This method attempts to find a solution using strict constraints
        first, then progressively relaxes constraints through 6 steps if needed.

        Args:
            request: Optimization request with movements, constraints, and
                    scoring context.

        Returns:
            OptimizationResultV2 with selected movements, scoring results,
            and relaxation step that produced solution.
        """
        logger.info(
            f"Starting greedy optimization for session: "
            f"{len(request.available_movements)} movements, "
            f"{len(request.target_muscle_volumes)} target muscles"
        )

        # Try solving with progressive relaxation
        for step in range(request.max_relaxation_steps + 1):
            self._relaxation_config.reset()
            self._relaxation_config.apply_step(step)

            logger.debug(
                f"Attempting solution with relaxation step {step}: "
                f"pattern_compat={self._relaxation_config.pattern_compatibility_expansion}, "
                f"synergist={self._relaxation_config.include_synergist_muscles}, "
                f"discipline_mult={self._relaxation_config.discipline_weight_multiplier}"
            )

            result = self._solve_with_config(request, step)

            if result.status != "INFEASIBLE":
                logger.info(
                    f"Solution found at relaxation step {step}: "
                    f"{len(result.selected_movements)} movements, "
                    f"status={result.status}"
                )
                return result

        # No solution found even with maximum relaxation
        logger.warning("No feasible solution found even with maximum relaxation")
        return OptimizationResultV2(
            selected_movements=[],
            selected_circuits=[],
            estimated_duration=0,
            status="INFEASIBLE",
            relaxation_step_used=request.max_relaxation_steps,
        )

    def _solve_with_config(
        self, request: OptimizationRequestV2, relaxation_step: int
    ) -> OptimizationResultV2:
        """Solve optimization with current relaxation configuration.

        Args:
            request: Optimization request.
            relaxation_step: Current relaxation step (0-6).

        Returns:
            OptimizationResultV2 with solution or INFEASIBLE status.
        """
        # Pre-score all movements using GlobalMovementScorer
        movement_scores = self._pre_score_movements(request)

        # Sort movements by total_score descending
        sorted_movements = sorted(
            movement_scores.items(),
            key=lambda x: x[1].total_score,
            reverse=True,
        )

        # Apply relaxation to target volumes
        volume_reduction_pct = self._config.or_tools.volume_target_reduction_pct
        reduced_target_volumes = {
            muscle: int(target_sets * (1 - volume_reduction_pct))
            for muscle, target_sets in request.target_muscle_volumes.items()
        }

        # Emergency mode: further reduce volume targets
        if self._relaxation_config.emergency_mode:
            reduced_target_volumes = {
                muscle: int(target * self._config.emergency_mode.volume_multiplier)
                for muscle, target in reduced_target_volumes.items()
            }

        # Greedy selection
        selected_movements = []
        selected_circuits = []
        session_muscle_counts = defaultdict(int)

        # Calculate budgets
        max_duration = request.session_duration_minutes
        if self._relaxation_config.emergency_mode:
            max_duration = max_duration * self._config.emergency_mode.duration_multiplier

        current_duration = 0
        volumes_achieved = defaultdict(int)

        # Required movements must be selected first
        for req_id in request.required_movement_ids:
            for movement in request.available_movements:
                if movement.id == req_id:
                    selected_movements.append(movement)
                    current_duration += self._calculate_movement_duration(movement, request)
                    session_muscle_counts[movement.primary_muscle] += 1
                    if movement.id in movement_scores:
                        volumes_achieved[movement.primary_muscle] += self._config.or_tools.min_sets_per_movement

        # Greedy selection from sorted list
        for movement_id, score_result in sorted_movements:
            if movement_id not in [m.id for m in selected_movements]:
                movement = self._get_movement_by_id(request, movement_id)
                if not movement:
                    continue

                # Check if movement is allowed by relaxation
                if not self._movement_allowed_by_relaxation(movement, request):
                    continue

                # Check equipment constraint
                if request.available_equipment:
                    if not any(eq in request.available_equipment for eq in movement.equipment_needed):
                        continue

                # Calculate duration for this movement
                movement_duration = self._calculate_movement_duration(movement, request)

                # Check duration constraint
                if current_duration + movement_duration > max_duration:
                    continue

                # Check muscle coverage constraint
                primary_muscle = movement.primary_muscle
                current_count = session_muscle_counts.get(primary_muscle, 0)

                # Primary muscle limit: max 2 per session
                if current_count >= 2:
                    continue

                # Check volume target (simplified)
                target_volume = reduced_target_volumes.get(primary_muscle, 0)
                current_volume = volumes_achieved.get(primary_muscle, 0)

                if current_volume >= target_volume:
                    continue

                # Select movement
                selected_movements.append(movement)
                current_duration += movement_duration
                session_muscle_counts[primary_muscle] = current_count + 1
                volumes_achieved[primary_muscle] = current_volume + self._config.or_tools.min_sets_per_movement

                # Add circuits if allowed and time remains
                if request.allow_circuits and request.available_circuits:
                    for circuit in request.available_circuits:
                        if circuit.id not in [c.id for c in selected_circuits]:
                            circuit_duration = circuit.duration_seconds // self._config.constants.seconds_per_minute

                            if current_duration + circuit_duration <= max_duration:
                                selected_circuits.append(circuit)
                                current_duration += circuit_duration

        # Build scoring results dict
        scoring_results = {}
        for m in selected_movements:
            if m.id in movement_scores:
                scoring_results[m.id] = movement_scores[m.id]

        # Determine status
        if selected_movements:
            status = "OPTIMAL" if len(selected_movements) >= 8 else "FEASIBLE"
        else:
            status = "INFEASIBLE"

        return OptimizationResultV2(
            selected_movements=selected_movements,
            selected_circuits=selected_circuits,
            estimated_duration=int(current_duration),
            status=status,
            relaxation_step_used=relaxation_step,
            scoring_results=scoring_results,
        )

    def _pre_score_movements(
        self, request: OptimizationRequestV2
    ) -> dict[int, ScoringResult]:
        """Pre-score all available movements using GlobalMovementScorer.

        Args:
            request: Optimization request.

        Returns:
            Dictionary mapping movement_id to ScoringResult.
        """
        movement_scores = {}

        for movement in request.available_movements:
            if movement.id in request.excluded_movement_ids:
                continue

            # Create scoring context
            context = self._create_scoring_context(movement, request)

            # Score the movement
            try:
                score_result = self._scorer.score_movement(movement, context)
                movement_scores[movement.id] = score_result
            except Exception as e:
                logger.warning(f"Failed to score movement {movement.id}: {e}")
                # Create minimal score result
                movement_scores[movement.id] = self._create_fallback_score(movement)

        return movement_scores

    def _create_scoring_context(
        self, movement, request: OptimizationRequestV2
    ) -> ScoringContext:
        """Create scoring context for a movement.

        Args:
            movement: Movement to create context for.
            request: Optimization request.

        Returns:
            ScoringContext populated with request data.
        """
        from app.ml.scoring.movement_scorer import get_config_loader

        config = get_config_loader().get_config()

        return ScoringContext(
            movement=movement,
            user_profile=request.user_profile,
            config=config,
            session_movements=request.session_movements,
            microcycle_movements=request.microcycle_movements,
            user_goals=request.user_goals,
            discipline_preferences={
                k: v for k, v in request.discipline_preferences.items()
            },
            required_pattern=request.required_pattern,
            target_muscles=request.target_muscles,
        )

    def _create_fallback_score(self, movement) -> ScoringResult:
        """Create fallback score result for movements that can't be scored.

        Args:
            movement: Movement that failed scoring.

        Returns:
            ScoringResult with neutral score.
        """
        from app.ml.scoring.movement_scorer import ScoringResult

        base_score = self._config.constants.neutral_base_score

        # Apply discipline preferences
        if movement.disciplines:
            for discipline in movement.disciplines:
                if discipline in {"olympic", "plyometric", "calisthenics"}:
                    base_score += self._config.constants.discipline_preference_bonus

        # Apply compound bonus
        if movement.compound:
            base_score += self._config.constants.compound_bonus

        # Normalize to 0-1
        base_score = min(
            max(base_score, self._config.constants.score_min_bound),
            self._config.constants.score_max_bound,
        )

        return ScoringResult(
            movement_id=movement.id,
            movement_name=movement.name,
            total_score=base_score,
            dimension_scores={
                "pattern_alignment": base_score * self._config.constants.dimension_score_weight,
                "muscle_coverage": base_score * self._config.constants.dimension_score_weight,
                "discipline_preference": base_score * self._config.constants.dimension_score_weight,
                "compound_bonus": base_score * self._config.constants.dimension_score_weight,
                "goal_alignment": base_score * self._config.constants.dimension_score_weight,
            },
            dimension_details={},
            qualified=base_score >= self._config.constants.min_qualified_score,
            raw_scores={},
            normalized_weights={},
        )

    def _calculate_movement_duration(self, movement, request: OptimizationRequestV2) -> int:
        """Calculate estimated duration for a movement.

        Args:
            movement: Movement to calculate duration for.
            request: Optimization request.

        Returns:
            Duration in minutes.
        """
        avg_sets_per_movement = (
            self._config.or_tools.min_sets_per_movement
            + self._config.or_tools.max_sets_per_movement
        ) / 2
        mins_per_movement = int(avg_sets_per_movement * self._config.constants.seconds_per_set)
        return mins_per_movement

    def _get_movement_by_id(
        self, request: OptimizationRequestV2, movement_id: int
    ):
        """Get movement from request by ID.

        Args:
            request: Optimization request.
            movement_id: Movement ID to find.

        Returns:
            SolverMovement if found, None otherwise.
        """
        for movement in request.available_movements:
            if movement.id == movement_id:
                return movement
        return None

    def _movement_allowed_by_relaxation(
        self, movement, request: OptimizationRequestV2
    ) -> bool:
        """Check if movement is allowed based on current relaxation configuration.

        Args:
            movement: Movement to check.
            request: Optimization request with relaxation configuration.

        Returns:
            True if movement is allowed, False otherwise.
        """
        config = self._relaxation_config

        # Step 1: Pattern compatibility constraint
        if request.required_pattern and not config.pattern_compatibility_expansion:
            if movement.pattern != request.required_pattern:
                return False

        # Step 4+: Allow isolation movements
        if not movement.compound and not config.allow_isolation_movements:
            return False

        # Step 5+: Allow generic movements (low tier)
        if not config.allow_generic_movements:
            if movement.tier in ["bronze", "generic"]:
                return False

        # Equipment constraint (always checked)
        if request.available_equipment:
            if not any(eq in request.available_equipment for eq in movement.equipment_needed):
                return False

        return True
