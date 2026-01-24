"""Circuit metrics calculation service.

Computes normalized fatigue, stimulus, and recovery metrics for circuits
to enable them to be treated as "super-movements" by the optimizer.
"""
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CircuitTemplate, Movement
from app.models.enums import CircuitType


class CircuitMetricsCalculator:
    """Calculates normalized metrics for circuit templates."""
    
    def __init__(self):
        """Initialize calculator."""
        pass
    
    async def calculate_circuit_metrics(
        self,
        db: AsyncSession,
        circuit: CircuitTemplate,
        rounds: Optional[int] = None,
        duration_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate all normalized metrics for a circuit.
        
        Args:
            db: Database session
            circuit: CircuitTemplate to calculate metrics for
            rounds: Override circuit.default_rounds if provided
            duration_seconds: Override circuit.default_duration_seconds if provided
            
        Returns:
            Dict with all calculated metrics
        """
        exercises_json = circuit.exercises_json or []
        if not exercises_json:
            return self._get_default_metrics()
        
        # Use provided values or fall back to circuit defaults
        rounds = rounds or circuit.default_rounds or 1
        duration_seconds = duration_seconds or circuit.default_duration_seconds or 600
        
        # Load movement data for all exercises in circuit
        movements_data = await self._load_movements_for_circuit(db, exercises_json)
        
        # Calculate base metrics
        metrics = {
            "fatigue_factor": 0.0,
            "stimulus_factor": 0.0,
            "min_recovery_hours": 0,
            "muscle_volume": {},
            "muscle_fatigue": {},
            "total_reps": 0,
            "estimated_work_seconds": 0,
            "effective_work_volume": 0.0,
        }
        
        # 1. Calculate per-exercise metrics aggregated across rounds
        total_reps = 0
        total_work_seconds = 0
        movement_fatigues = []
        movement_stimuli = []
        
        for exercise in exercises_json:
            movement_id = exercise.get("movement_id")
            movement = movements_data.get(movement_id)
            
            if not movement:
                continue
            
            reps_per_round = exercise.get("reps") or 1
            exercise_reps = reps_per_round * rounds
            total_reps += exercise_reps
            
            # Calculate work time for this exercise
            duration = exercise.get("duration_seconds")
            if duration:
                exercise_work_seconds = duration * rounds
            else:
                exercise_work_seconds = (reps_per_round or 10) * 3 * rounds
            
            total_work_seconds += exercise_work_seconds
            
            # Accumulate movement metrics
            movement_fatigues.append(movement.fatigue_factor)
            movement_stimuli.append(movement.stimulus_factor)
            
            # 5. Calculate Muscle-Level Metrics
            primary_muscle = str(movement.primary_muscle.value) if hasattr(movement.primary_muscle, 'value') else str(movement.primary_muscle)
            secondary_muscles = movement.secondary_muscles or []
            
            # Primary muscle gets full fatigue
            muscle_fatigue = movement.fatigue_factor * rounds
            metrics["muscle_fatigue"][primary_muscle] = metrics["muscle_fatigue"].get(primary_muscle, 0) + muscle_fatigue
            
            # Secondary muscles get half fatigue
            for sec in secondary_muscles:
                metrics["muscle_fatigue"][sec] = metrics["muscle_fatigue"].get(sec, 0) + (muscle_fatigue * 0.5)
            
            # Muscle volume (weighted by sets/rounds)
            muscle_volume = rounds
            metrics["muscle_volume"][primary_muscle] = metrics["muscle_volume"].get(primary_muscle, 0) + muscle_volume
            
            for sec in secondary_muscles:
                metrics["muscle_volume"][sec] = metrics["muscle_volume"].get(sec, 0) + (muscle_volume * 0.5)
        
        # Store aggregated metrics
        metrics["total_reps"] = total_reps
        metrics["estimated_work_seconds"] = total_work_seconds
        
        # 3. Calculate Fatigue Factor with circuit type modifiers
        if movement_fatigues:
            base_fatigue = sum(movement_fatigues) / len(movement_fatigues)
            fatigue_modifier = self._get_fatigue_modifier(circuit.circuit_type)
            metrics["fatigue_factor"] = round(base_fatigue * (1 + fatigue_modifier), 2)
        
        # 4. Calculate Stimulus Factor with volume adjustment
        if movement_stimuli:
            base_stimulus = sum(movement_stimuli) / len(movement_stimuli)
            baseline_volume = 10.0  # Arbitrary baseline for normalization
            volume_ratio = total_work_seconds / baseline_volume if baseline_volume > 0 else 1.0
            metrics["stimulus_factor"] = round(base_stimulus * min(volume_ratio, 2.0), 2)
        
        # 6. Determine Min Recovery Hours
        if movements_data:
            base_recovery = max(m.min_recovery_hours for m in movements_data.values())
            recovery_modifier = self._get_recovery_modifier(circuit.circuit_type)
            metrics["min_recovery_hours"] = base_recovery + recovery_modifier
        
        # Calculate effective work volume (weighted by fatigue)
        metrics["effective_work_volume"] = round(total_work_seconds * (metrics["fatigue_factor"] / 10.0), 2)
        
        return metrics
    
    def _get_fatigue_modifier(self, circuit_type: CircuitType) -> float:
        """
        Get fatigue modifier based on circuit type.
        
        Returns:
            Modifier as percentage (0.0 to 1.0)
        """
        modifiers = {
            CircuitType.ROUNDS_FOR_TIME: 0.15,
            CircuitType.AMRAP: 0.15,
            CircuitType.LADDER: 0.10,
            CircuitType.EMOM: 0.0,
            CircuitType.TABATA: 0.20,
            CircuitType.CHIPPER: 0.12,
            CircuitType.STATION: 0.08,
        }
        return modifiers.get(circuit_type, 0.0)
    
    def _get_recovery_modifier(self, circuit_type: CircuitType) -> int:
        """
        Get recovery hours modifier based on circuit type.
        
        Returns:
            Additional hours to add to base recovery
        """
        modifiers = {
            CircuitType.ROUNDS_FOR_TIME: 12,
            CircuitType.AMRAP: 8,
            CircuitType.EMOM: 4,
            CircuitType.LADDER: 10,
            CircuitType.TABATA: 6,
            CircuitType.CHIPPER: 10,
            CircuitType.STATION: 8,
        }
        return modifiers.get(circuit_type, 0)
    
    async def _load_movements_for_circuit(
        self,
        db: AsyncSession,
        exercises_json: list[dict]
    ) -> Dict[int, Movement]:
        """
        Load all movements referenced in circuit exercises.
        
        Args:
            db: Database session
            exercises_json: Circuit exercises_json data
            
        Returns:
            Dict mapping movement_id to Movement object
        """
        movement_ids = []
        for exercise in exercises_json:
            movement_id = exercise.get("movement_id")
            if movement_id:
                movement_ids.append(movement_id)
        
        if not movement_ids:
            return {}
        
        result = await db.execute(
            select(Movement).where(Movement.id.in_(movement_ids))
        )
        movements = result.scalars().all()
        
        return {m.id: m for m in movements}
    
    def _get_default_metrics(self) -> Dict[str, Any]:
        """
        Get default metrics for empty circuits.
        
        Returns:
            Dict with default metric values
        """
        return {
            "fatigue_factor": 1.0,
            "stimulus_factor": 1.0,
            "min_recovery_hours": 24,
            "muscle_volume": {},
            "muscle_fatigue": {},
            "total_reps": 0,
            "estimated_work_seconds": 0,
            "effective_work_volume": 0.0,
        }


# Singleton instance
circuit_metrics_calculator = CircuitMetricsCalculator()
