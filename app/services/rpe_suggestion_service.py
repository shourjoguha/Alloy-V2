"""
RPE Suggestion Service

Provides intelligent RPE suggestions based on:
- Program type and microcycle phase
- Movement characteristics (pattern, CNS load, discipline)
- Training frequency and weekly volume
- User recovery state
- Pattern recovery status

Core Philosophy: Fatigue and stimulus are NOT inherent movement properties.
They are functions of how movements are used (RPE 1-10).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional
from datetime import datetime

from app.config.optimization_config_loader import get_optimization_config
from app.models.enums import ExerciseRole, MovementPattern, Goal
from app.models.movement import Movement

if TYPE_CHECKING:
    from app.models.program import PatternRecoveryState, Microcycle


logger = logging.getLogger(__name__)


@dataclass
class RPESuggestion:
    """Result of RPE suggestion for a movement."""
    min_rpe: float
    max_rpe: float
    adjustment_reason: str | None = None


@dataclass
class SessionRPESuggestion:
    """RPE suggestion for an entire session by exercise role."""
    exercise_role: ExerciseRole
    min_rpe: float
    max_rpe: float


class RPESuggestionService:
    """
    Intelligent RPE suggestion service.
    
    Suggests appropriate RPE ranges for exercises based on:
    - Program type (strength, hypertrophy, endurance, power)
    - Microcycle phase (accumulation, intensification, peaking, deload)
    - Movement characteristics (pattern, CNS load, discipline)
    - Training frequency and volume constraints
    - User recovery state (sleep, HRV, soreness)
    - Pattern recovery status
    """
    
    def __init__(self):
        self._config = get_optimization_config().rpe_suggestion
    
    async def suggest_rpe_for_movement(
        self,
        movement: Movement,
        exercise_role: ExerciseRole,
        program_type: str,
        microcycle_phase: str,
        training_days_per_week: int,
        session_high_rpe_sets_count: int,
        user_recovery_state: dict[str, Any],
        pattern_recovery_hours: dict[str, datetime | None],
    ) -> RPESuggestion:
        """
        Suggest RPE range for a specific movement.
        
        Args:
            movement: Movement to suggest RPE for
            exercise_role: Role in session (warmup, main_strength, etc.)
            program_type: Type of training program
            microcycle_phase: Current microcycle phase
            training_days_per_week: User's training frequency
            session_high_rpe_sets_count: Number of high-RPE sets already in this session
            user_recovery_state: User's current recovery signals
            pattern_recovery_hours: Dict of pattern -> last_trained_at datetime
        
        Returns:
            RPESuggestion with min_rpe, max_rpe, and optional adjustment_reason
        """
        base_min, base_max = self._get_base_rpe_range(
            exercise_role, program_type, microcycle_phase
        )
        
        min_rpe, max_rpe = self._apply_cns_discipline_cap(
            movement, base_min, base_max, program_type
        )
        
        min_rpe, max_rpe, adjustment_reason = self._apply_fatigue_adjustments(
            min_rpe, max_rpe, user_recovery_state
        )
        
        min_rpe, max_rpe = self._check_pattern_recovery_constraint(
            movement, min_rpe, max_rpe, pattern_recovery_hours
        )
        
        min_rpe, max_rpe = self._check_high_rpe_set_limit(
            movement, min_rpe, max_rpe, session_high_rpe_sets_count
        )
        
        return RPESuggestion(
            min_rpe=round(min_rpe, 1),
            max_rpe=round(max_rpe, 1),
            adjustment_reason=adjustment_reason,
        )
    
    async def suggest_rpe_for_session(
        self,
        session_type: str,
        program_type: str,
        microcycle_phase: str,
        user_goals: list[Goal],
        user_recovery_state: dict[str, Any],
        weekly_high_rpe_sets_count: int,
    ) -> dict[ExerciseRole, tuple[float, float]]:
        """
        Suggest RPE ranges for an entire session by exercise role.
        
        Args:
            session_type: Type of session (strength, hypertrophy, etc.)
            program_type: Type of training program
            microcycle_phase: Current microcycle phase
            user_goals: User's training goals
            user_recovery_state: User's current recovery signals
            weekly_high_rpe_sets_count: Number of high-RPE sets this week
        
        Returns:
            Dict mapping exercise_role -> (min_rpe, max_rpe)
        """
        rpe_ranges = {}
        
        for role in [
            ExerciseRole.WARMUP,
            ExerciseRole.MAIN,
            ExerciseRole.ACCESSORY,
            ExerciseRole.COOLDOWN,
        ]:
            base_min, base_max = self._get_base_rpe_range(
                role, program_type, microcycle_phase
            )
            
            base_min, base_max, _ = self._apply_fatigue_adjustments(
                base_min, base_max, user_recovery_state
            )
            
            rpe_ranges[role] = (round(base_min, 1), round(base_max, 1))
        
        logger.info(
            f"Session RPE suggestions: {session_type} program, "
            f"{microcycle_phase} phase: {rpe_ranges}"
        )
        
        return rpe_ranges
    
    def _get_base_rpe_range(
        self,
        exercise_role: ExerciseRole,
        program_type: str,
        microcycle_phase: str,
    ) -> tuple[float, float]:
        """Get base RPE range from configuration."""
        
        profile = self._config.program_type_profiles.get(program_type)
        if profile is None:
            logger.warning(f"No RPE profile for program type: {program_type}")
            profile = self._config.program_type_profiles.get("strength", profile)
        
        progression = profile.microcycle_progression
        
        if exercise_role == ExerciseRole.WARMUP:
            return tuple(self._config.warmup_rpe)
        elif exercise_role == ExerciseRole.COOLDOWN:
            return tuple(self._config.cooldown_rpe)
        elif exercise_role == ExerciseRole.MAIN:
            if microcycle_phase and hasattr(progression, microcycle_phase):
                phase_rpe = getattr(progression, microcycle_phase)
                if phase_rpe:
                    return tuple(phase_rpe)
            return tuple(self._config.main_strength_rpe)
        elif exercise_role == ExerciseRole.ACCESSORY:
            return tuple(profile.accessory_rpe)
        
        logger.warning(f"Unknown exercise role: {exercise_role}")
        return (6.0, 8.0)
    
    def _apply_cns_discipline_cap(
        self,
        movement: Movement,
        base_min: float,
        base_max: float,
        program_type: str,
    ) -> tuple[float, float]:
        """Apply RPE caps for high-CNS movements."""
        
        if movement.cns_load not in ["high", "very_high"]:
            return base_min, base_max
        
        # Check disciplines via relationship (movement.disciplines is a list of MovementDiscipline)
        high_cns_disciplines = ["olympic_weightlifting", "powerlifting"]
        movement_disciplines = []
        if hasattr(movement, 'disciplines') and movement.disciplines:
            movement_disciplines = [d.discipline.value if hasattr(d.discipline, 'value') else str(d.discipline) for d in movement.disciplines]
        
        if not any(d in high_cns_disciplines for d in movement_disciplines):
            return base_min, base_max
        
        high_cns_config = self._config.cns_discipline_adjustments.get(
            "high_cns_olympic_powerlifting"
        )
        if high_cns_config:
            capped_max = min(base_max, high_cns_config.rpe_cap)
            logger.info(
                f"Applied CNS discipline cap for {movement.name}: "
                f"{base_max} -> {capped_max} (cap: {high_cns_config.rpe_cap})"
            )
            return base_min, capped_max
        
        return base_min, base_max
    
    def _apply_fatigue_adjustments(
        self,
        base_min: float,
        base_max: float,
        recovery_state: dict[str, Any],
    ) -> tuple[float, float, str | None]:
        """Reduce RPE based on recovery signals."""
        
        total_adjustment = 0.0
        adjustment_reasons = []
        
        fatigue_config = self._config.fatigue_adjustments
        
        sleep_hours = recovery_state.get("sleep_hours", 8)
        if sleep_hours < 6:
            adjustment = fatigue_config.sleep_under_6h
            total_adjustment += adjustment
            adjustment_reasons.append(f"sleep_{int(sleep_hours)}h")
        elif sleep_hours < 5:
            adjustment = fatigue_config.sleep_under_5h
            total_adjustment += adjustment
            adjustment_reasons.append(f"sleep_{int(sleep_hours)}h")
        
        hrv_percentage = recovery_state.get("hrv_percentage_change", 0)
        if hrv_percentage < -20:
            adjustment = fatigue_config.hrv_below_baseline_20pct
            total_adjustment += adjustment
            adjustment_reasons.append("low_hrv")
        
        soreness = recovery_state.get("soreness", 0)
        if soreness > 7:
            adjustment = fatigue_config.soreness_above_7
            total_adjustment += adjustment
            adjustment_reasons.append("high_soreness")
        
        consecutive_high_rpe_days = recovery_state.get("consecutive_high_rpe_days", 0)
        if consecutive_high_rpe_days >= 2:
            adjustment = fatigue_config.consecutive_high_rpe_days
            total_adjustment += adjustment
            adjustment_reasons.append("consecutive_high_rpe")
        
        if total_adjustment < 0:
            adjusted_min = max(base_min + total_adjustment, 3.0)
            adjusted_max = max(base_max + total_adjustment, 4.0)
            reason = "_".join(adjustment_reasons) if adjustment_reasons else None
            logger.info(
                f"Applied fatigue adjustments: {base_min}-{base_max} -> "
                f"{adjusted_min}-{adjusted_max} (reasons: {reason})"
            )
            return adjusted_min, adjusted_max, reason
        
        return base_min, base_max, None
    
    def _check_pattern_recovery_constraint(
        self,
        movement: Movement,
        base_min: float,
        base_max: float,
        pattern_recovery_hours: dict[str, datetime | None],
    ) -> tuple[float, float]:
        """Adjust RPE if pattern hasn't recovered."""
        
        if movement.pattern not in pattern_recovery_hours:
            return base_min, base_max
        
        last_trained_at = pattern_recovery_hours[movement.pattern]
        if last_trained_at is None:
            return base_min, base_max
        
        hours_since = (datetime.utcnow() - last_trained_at).total_seconds() / 3600
        
        recovery_hours = self._config.recovery_hours_by_rpe
        
        if hours_since >= recovery_hours.rpe_6_7:
            return base_min, base_max
        
        if hours_since >= recovery_hours.rpe_8:
            return max(base_min - 1.0, 4.0), max(base_max - 1.0, 5.0)
        elif hours_since >= 48:
            return max(base_min - 0.5, 5.0), max(base_max - 0.5, 6.0)
        
        logger.info(
            f"Pattern {movement.pattern} not fully recovered ({hours_since:.0f}h ago), "
            f"reducing RPE from {base_min}-{base_max} to "
            f"{max(base_min - 1.0, 4.0)}-{max(base_max - 1.0, 5.0)}"
        )
        return max(base_min - 1.0, 4.0), max(base_max - 1.0, 5.0)
    
    def _check_high_rpe_set_limit(
        self,
        movement: Movement,
        base_min: float,
        base_max: float,
        session_high_rpe_sets_count: int,
    ) -> tuple[float, float]:
        """Reduce RPE if session has too many high-RPE sets already."""
        
        if movement.pattern not in ["hinge", "squat", "lunge", "olympic"]:
            return base_min, base_max
        
        max_high_rpe_sets = 6
        
        if session_high_rpe_sets_count < max_high_rpe_sets:
            return base_min, base_max
        
        if base_max >= 8.0:
            reduced_max = 7.5
            logger.info(
                f"Session has {session_high_rpe_sets_count} high-RPE sets "
                f"(max {max_high_rpe_sets}), capping {movement.pattern} "
                f"at RPE {reduced_max}"
            )
            return base_min, reduced_max
        
        return base_min, base_max


def get_rpe_suggestion_service() -> RPESuggestionService:
    """Get singleton RPESuggestionService instance."""
    return RPESuggestionService()
