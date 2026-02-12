"""
Optimization Types

Shared type definitions for optimization services.
These types are used by both greedy_optimizer and optimization_v2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import CircuitType, SkillLevel
from app.models.user import UserProfile


@dataclass
class SolverMovement:
    """Simplified movement data for solver (picklable)."""

    id: int
    name: str
    primary_muscle: str
    compound: bool
    is_complex_lift: bool
    pattern: str
    disciplines: list[str] = field(default_factory=list)
    equipment_needed: list[str] = field(default_factory=list)
    tier: str = "silver"


@dataclass
class SolverCircuit:
    """Normalized circuit for optimization solver (parallel to SolverMovement)."""

    id: int
    name: str
    primary_muscle: str
    effective_work_volume: float
    circuit_type: CircuitType
    duration_seconds: int
    equipment_needed: list[str] = field(default_factory=list)


@dataclass
class OptimizationRequestV2:
    """Extended request for diversity-aware optimization."""

    available_movements: list[SolverMovement]
    available_circuits: list[SolverCircuit]
    target_muscle_volumes: dict[str, int]  # muscle -> sets
    user_skill_level: SkillLevel
    excluded_movement_ids: list[int]
    required_movement_ids: list[int]
    session_duration_minutes: int
    allow_complex_lifts: bool
    allow_circuits: bool = True
    goal_weights: dict[str, int] | None = None
    preferred_movement_ids: list[int] | None = None

    # Scoring context fields
    user_profile: UserProfile | None = None
    session_movements: list[int] = field(default_factory=list)
    microcycle_movements: list[int] = field(default_factory=list)
    user_goals: list[str] = field(default_factory=list)
    discipline_preferences: dict[str, int] = field(default_factory=dict)
    required_pattern: str | None = None
    target_muscles: list[str] = field(default_factory=list)

    # Equipment constraints
    available_equipment: set[str] = field(default_factory=set)

    # Relaxation settings
    max_relaxation_steps: int = 6


@dataclass
class OptimizationResultV2:
    """Extended result with scoring breakdown."""

    selected_movements: list[SolverMovement]
    selected_circuits: list[SolverCircuit]
    estimated_duration: int
    status: str  # "OPTIMAL", "FEASIBLE", "INFEASIBLE"
    relaxation_step_used: int = 0
    scoring_results: dict[int, "ScoringResult"] = field(default_factory=dict)


# Import ScoringResult type for type annotation
try:
    from app.ml.scoring.movement_scorer import ScoringResult
except ImportError:
    # Define placeholder if import fails
    class ScoringResult:
        pass
