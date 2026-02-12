"""Circuit metrics calculation service.

This service provides functionality to calculate normalized metrics for circuit templates,
treating circuits as "super-movements" with comparable recovery metrics.
"""
from typing import Any

from app.models.circuit import CircuitTemplate
from app.models.enums import CircuitType
from app.repositories.movement_repository import MovementRepository


class CircuitMetricsCalculator:
    """Calculate normalized metrics for circuit templates.
    
    This class provides methods to compute recovery and muscle-level metrics for circuits,
    enabling them to be treated as first-class entities in the optimization engine alongside
    individual movements.
    """

    def __init__(self, movement_repository: MovementRepository):
        """Initialize the calculator with required repositories.
        
        Args:
            movement_repository: Repository for fetching movement data
        """
        self._movement_repository = movement_repository

    async def calculate_circuit_metrics(
        self,
        circuit: CircuitTemplate,
        rounds: int | None = None,
        duration_seconds: int | None = None
    ) -> dict[str, Any]:
        """Calculate all normalized metrics for a circuit.
        
        Args:
            circuit: CircuitTemplate to calculate metrics for
            rounds: Number of rounds (defaults to circuit.default_rounds or 1)
            duration_seconds: Duration in seconds (defaults to circuit.default_duration_seconds)
            
        Returns:
            Dictionary containing all calculated metrics:
            - min_recovery_hours: Recovery time after circuit
            - muscle_volume: Dict mapping muscle names to total volume
            - muscle_fatigue: Dict mapping muscle names to total fatigue
            - total_reps: Total reps across all exercises × rounds
            - estimated_work_seconds: Total work time (excluding rest)
            - effective_work_volume: Weighted work volume metric
        """
        # Use provided values or fall back to circuit defaults
        rounds = rounds or circuit.default_rounds or 1
        duration_seconds = duration_seconds or circuit.default_duration_seconds
        
        # Get exercises from circuit
        exercises = circuit.exercises_json or []
        
        # Handle empty circuits
        if not exercises:
            return self._get_default_metrics()
        
        # Fetch movement data for all exercises using repository
        movement_ids = [ex.get("movement_id") for ex in exercises if ex.get("movement_id")]
        movements = []
        
        if movement_ids:
            movements_by_id = {m.id: m for m in await self._movement_repository.list_by_ids(movement_ids)}
            
            for exercise in exercises:
                movement_id = exercise.get("movement_id")
                if movement_id in movements_by_id:
                    movements.append(movements_by_id[movement_id])
        
        # If no movements found, return default metrics
        if not movements:
            return self._get_default_metrics()
        
        # Calculate metrics
        metrics = {
            "total_reps": self._calculate_total_reps(exercises, rounds),
            "estimated_work_seconds": self._calculate_work_time(exercises, rounds, duration_seconds),
        }
        
        # Calculate recovery hours
        base_recovery = max(m.min_recovery_hours or 24 for m in movements)
        metrics["min_recovery_hours"] = self._apply_recovery_modifier(base_recovery, circuit.circuit_type)
        
        # Calculate muscle-level metrics
        muscle_volume, muscle_fatigue = self._calculate_muscle_metrics(movements, exercises, rounds)
        metrics["muscle_volume"] = muscle_volume
        metrics["muscle_fatigue"] = muscle_fatigue
        
        # Calculate effective work volume
        metrics["effective_work_volume"] = self._calculate_effective_volume(
            metrics["total_reps"],
            metrics["estimated_work_seconds"]
        )
        
        return metrics

    def _get_default_metrics(self) -> dict[str, Any]:
        """Return default metrics for empty or invalid circuits."""
        return {
            "min_recovery_hours": 24,
            "muscle_volume": {},
            "muscle_fatigue": {},
            "total_reps": 0,
            "estimated_work_seconds": 0,
            "effective_work_volume": 0.0,
        }

    def _calculate_total_reps(self, exercises: list[dict], rounds: int) -> int:
        """Calculate total reps across all exercises and rounds."""
        total_reps = 0
        for exercise in exercises:
            reps = exercise.get("reps") or 0
            total_reps += reps
        
        return total_reps * rounds

    def _calculate_work_time(
        self,
        exercises: list[dict],
        rounds: int,
        duration_seconds: int | None
    ) -> int:
        """Calculate estimated work time in seconds."""
        # If duration is provided (for AMRAP/EMOM), use that
        if duration_seconds:
            return duration_seconds
        
        # Otherwise estimate based on reps
        total_time = 0
        for exercise in exercises:
            reps = exercise.get("reps") or 10
            duration = exercise.get("duration_seconds") or 0
            total_time += duration + (reps * 3)  # Assume 3 seconds per rep
        
        return total_time * rounds

    def _apply_recovery_modifier(self, base_recovery: int, circuit_type: CircuitType) -> int:
        """Apply circuit type-specific recovery modifiers.
        
        Modifiers:
        - ROUNDS_FOR_TIME: +12 hours
        - AMRAP: +8 hours
        - EMOM: +4 hours
        - LADDER: +6 hours
        - TABATA: +10 hours
        - CHIPPER: +4 hours
        - STATION: +8 hours
        """
        modifiers = {
            CircuitType.ROUNDS_FOR_TIME: 12,
            CircuitType.AMRAP: 8,
            CircuitType.EMOM: 4,
            CircuitType.LADDER: 6,
            CircuitType.TABATA: 10,
            CircuitType.CHIPPER: 4,
            CircuitType.STATION: 8,
        }
        
        modifier = modifiers.get(circuit_type, 0)
        return base_recovery + modifier

    def _calculate_muscle_metrics(
        self,
        movements: list,
        exercises: list[dict],
        rounds: int
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Calculate muscle-level volume and fatigue metrics.
        
        Returns:
            Tuple of (muscle_volume, muscle_fatigue) dictionaries
        """
        muscle_volume: dict[str, float] = {}
        muscle_fatigue: dict[str, float] = {}
        
        for exercise in exercises:
            movement_id = exercise.get("movement_id")
            if not movement_id:
                continue
            
            # Find the movement
            movement = next((m for m in movements if m.id == movement_id), None)
            if not movement:
                continue
            
            reps = exercise.get("reps") or 1
            
            # Primary muscle gets full contribution
            if movement.primary_muscle:
                primary = movement.primary_muscle.lower()
                muscle_volume[primary] = muscle_volume.get(primary, 0) + (reps * rounds)
                muscle_fatigue[primary] = muscle_fatigue.get(primary, 0) + (reps * rounds)
            
            # Secondary muscles get half contribution
            if movement.secondary_muscles:
                for secondary in movement.secondary_muscles:
                    sec_lower = secondary.lower()
                    muscle_volume[sec_lower] = muscle_volume.get(sec_lower, 0) + ((reps * rounds) * 0.5)
                    muscle_fatigue[sec_lower] = muscle_fatigue.get(sec_lower, 0) + ((reps * rounds) * 0.5)
        
        return muscle_volume, muscle_fatigue

    def _calculate_effective_volume(
        self,
        total_reps: int,
        work_seconds: int
    ) -> float:
        """Calculate effective work volume as weighted metric."""
        # Combine reps and time into a single volume metric
        # Formula: (reps * 0.7) + (time/60 * 0.3)
        reps_component = total_reps * 0.7
        time_component = (work_seconds / 60) * 0.3  # Convert to minutes
        
        return reps_component + time_component


# Standalone function exports for convenience (requires manual instantiation with repository)
async def calculate_circuit_metrics(
    circuit: CircuitTemplate,
    movement_repository: MovementRepository,
    rounds: int | None = None,
    duration_seconds: int | None = None
) -> dict[str, Any]:
    """Calculate normalized metrics for a circuit template.
    
    This is a convenience function that creates a CircuitMetricsCalculator instance
    and calculates metrics. For better performance in bulk operations, create an
    instance of CircuitMetricsCalculator and reuse it.
    
    Args:
        circuit: CircuitTemplate to calculate metrics for
        movement_repository: Repository for fetching movement data
        rounds: Number of rounds (defaults to circuit.default_rounds or 1)
        duration_seconds: Duration in seconds (defaults to circuit.default_duration_seconds)
        
    Returns:
        Dictionary containing all calculated metrics
    """
    calculator = CircuitMetricsCalculator(movement_repository)
    return await calculator.calculate_circuit_metrics(
        circuit, rounds, duration_seconds
    )
