"""Interference management service for goal conflict detection and adjustment."""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Goal, HeuristicConfig


@dataclass
class GoalConflict:
    """Represents a goal conflict and its adjustment."""
    goal_1: Goal
    goal_2: Goal
    conflict_type: str  # e.g., "volume_conflict", "frequency_conflict"
    severity: float  # 0-1 scale
    adjustment: Dict[str, float]  # e.g., {"frequency_reduction": 0.2}
    recommendation: str


class InterferenceService:
    """
    Manages goal interference rules and validations.
    
    Goals can have conflicting dose/frequency requirements. This service
    loads heuristic configs and applies interference logic to adjust
    program parameters.
    """
    
    def __init__(self):
        """Initialize service with empty cache; load heuristics on demand."""
        self._interference_rules: Optional[Dict] = None
    
    async def validate_goals(
        self,
        db: AsyncSession,
        goal_1: Goal,
        goal_2: Goal,
        goal_3: Goal,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that goals don't have disqualifying conflicts.
        
        Note: Accepts 3 goals for API compatibility, but duplicates are allowed
        (used for padding when user selects fewer than 3 goals).
        
        Args:
            db: Database session
            goal_1, goal_2, goal_3: Program goals (may contain duplicates for padding)
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        goal_list = [goal_1, goal_2, goal_3]
        
        # Get unique goals only (to handle padding)
        unique_goals = list(dict.fromkeys(goal_list))  # Preserves order, removes duplicates
        
        # If only 1 unique goal, no conflicts possible
        if len(unique_goals) == 1:
            return True, []
        
        # Load interference rules
        rules = await self._load_interference_rules(db)
        
        # Check pairwise conflicts (only between unique goals)
        n = len(unique_goals)
        for i in range(n):
            for j in range(i + 1, n):
                g1, g2 = unique_goals[i], unique_goals[j]
                conflict_key = f"{g1.value}_{g2.value}"
                reverse_key = f"{g2.value}_{g1.value}"
                
                conflict_rule = rules.get(conflict_key) or rules.get(reverse_key)
                if conflict_rule:
                    if conflict_rule.get("severity", 0) > 0.8:
                        # Hard conflict
                        return False, [f"Goals {g1.value} and {g2.value} conflict heavily"]
                    else:
                        warnings.append(f"Goals {g1.value} and {g2.value} have some conflict")
        
        return True, warnings
    
    async def get_conflicts(
        self,
        db: AsyncSession,
        goal_1: Goal,
        goal_2: Goal,
        goal_3: Goal,
    ) -> List[GoalConflict]:
        """
        Get all conflicts between the three goals.
        
        Args:
            db: Database session
            goal_1, goal_2, goal_3: The three program goals
        
        Returns:
            List of GoalConflict objects
        """
        conflicts = []
        goal_list = [goal_1, goal_2, goal_3]
        rules = await self._load_interference_rules(db)
        
        for i in range(3):
            for j in range(i + 1, 3):
                g1, g2 = goal_list[i], goal_list[j]
                conflict_key = f"{g1.value}_{g2.value}"
                reverse_key = f"{g2.value}_{g1.value}"
                
                conflict_rule = rules.get(conflict_key) or rules.get(reverse_key)
                if conflict_rule:
                    conflict = GoalConflict(
                        goal_1=g1,
                        goal_2=g2,
                        conflict_type=conflict_rule.get("type", "unknown"),
                        severity=conflict_rule.get("severity", 0.5),
                        adjustment=conflict_rule.get("adjustment", {}),
                        recommendation=conflict_rule.get("recommendation", ""),
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    async def apply_dose_adjustments(
        self,
        db: AsyncSession,
        goal_1: Goal,
        goal_2: Goal,
        goal_3: Goal,
        base_frequency: Dict[str, int],  # pattern -> sessions/week
    ) -> Dict[str, int]:
        """
        Apply dose adjustments based on goal conflicts.
        
        Args:
            db: Database session
            goal_1, goal_2, goal_3: Program goals
            base_frequency: Base sessions per week per pattern
        
        Returns:
            Adjusted frequency dict
        """
        adjusted = base_frequency.copy()
        conflicts = await self.get_conflicts(db, goal_1, goal_2, goal_3)
        
        for conflict in conflicts:
            if conflict.adjustment:
                # Apply adjustments (simplified: assume adjustment is frequency reduction factor)
                for pattern, factor in conflict.adjustment.items():
                    if pattern in adjusted:
                        adjusted[pattern] = max(1, int(adjusted[pattern] * (1 - factor)))
        
        return adjusted
    
    async def _load_interference_rules(self, db: AsyncSession) -> Dict:
        """
        Load interference rules from HeuristicConfig table.
        
        Looks for config with name 'interference_rules'.
        """
        if self._interference_rules is not None:
            return self._interference_rules
        
        result = await db.execute(
            select(HeuristicConfig).where(HeuristicConfig.name == "interference_rules", HeuristicConfig.active == True).limit(1)
        )
        config = result.scalar_one_or_none()
        
        if config and config.json_blob:
            self._interference_rules = config.json_blob
        else:
            # Default rules (empty, no conflicts)
            self._interference_rules = {}
        
        return self._interference_rules
    
    def clear_cache(self):
        """Clear cached interference rules."""
        self._interference_rules = None


# Singleton instance
interference_service = InterferenceService()
