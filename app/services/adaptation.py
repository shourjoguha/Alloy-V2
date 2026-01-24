"""
AdaptationService - Adapts sessions based on user feedback and constraints.

Responsible for:
- Parsing and applying movement rule constraints (forbidden moves, injury restrictions)
- Adapting sessions based on soreness and recovery signals
- Suggesting exercise substitutions via LLM
- Managing optional session sections (warmup, finisher, conditioning)
- Enforcing user preferences (enjoyable activities weighting)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import (
    UserMovementRule, UserEnjoyableActivity
)
from app.models.logging import (
    SorenessLog, RecoverySignal
)
from app.models.program import Session, Microcycle, Program, SessionExercise
from app.schemas.daily import AdaptationRequest


class AdaptationService:
    """
    Adapts workout sessions in real-time based on user state.
    
    Constraints applied:
    - Movement rules (forbidden exercises, injury restrictions)
    - Soreness feedback (avoid sore body parts)
    - Recovery status (adjust volume if low recovery)
    - User preferences (weight enjoyable activities, avoid disliked)
    
    Adaptations may include:
    - Removing/substituting exercises
    - Adding/removing optional sections (warmup, finisher)
    - Adjusting sets/reps based on recovery
    - Suggesting alternative movements
    """
    
    async def adapt_session(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: int,
        request: AdaptationRequest,
    ) -> Dict[str, Any]:
        """
        Adapt a session based on user state and constraints.
        
        Args:
            db: Database session
            user_id: User ID
            session_id: Session ID
            request: Adaptation request (soreness, recovery_signal, notes)
        
        Returns:
            Dict with adapted_patterns (list), removed_patterns (list), 
            added_sections (list), notes (str)
        
        Raises:
            ValueError: If session not found
        """
        # Fetch session and movements
        session_result = await db.execute(
            select(Session)
            .join(Microcycle)
            .join(Program)
            .where(
                and_(
                    Session.id == session_id,
                    Program.user_id == user_id
                )
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        patterns_result = await db.execute(
            select(SessionExercise).options(joinedload(SessionExercise.movement)).where(
                SessionExercise.session_id == session_id
            )
        )
        patterns = list(patterns_result.scalars().all())
        
        # Load constraints
        rules = await self._get_movement_rules(db, user_id)
        preferences = await self._get_user_preferences(db, user_id)
        recovery = await self._assess_recovery(db, user_id, request)
        
        # Adapt patterns
        adapted = []
        removed = []
        for pattern in patterns:
            # Check movement rules
            forbidden = self._is_movement_forbidden(pattern.movement, rules)
            if forbidden:
                removed.append({"movement": pattern.movement, "reason": f"Forbidden: {forbidden}"})
                continue
            
            # Check soreness
            soreness_dict = {s.body_part: s.level for s in request.soreness or []}
            affected_by_soreness = self._check_soreness_conflict(pattern, soreness_dict)
            if affected_by_soreness:
                removed.append({"movement": pattern.movement, "reason": f"Conflicts with soreness: {affected_by_soreness}"})
                continue
            
            # Adjust sets/reps based on recovery
            adjusted = self._adjust_volume(pattern, recovery)
            adapted.append(adjusted)
        
        # Add optional sections based on recovery
        added_sections = []
        if recovery.get("recovery_score", 50) > 70:
            added_sections.append("conditioning")
        if recovery.get("recovery_score", 50) < 40:
            added_sections.append("extra_warmup")
        
        return {
            "adapted_patterns": adapted,
            "removed_patterns": removed,
            "added_sections": added_sections,
            "recovery_score": recovery.get("recovery_score"),
            "notes": f"Adapted {len(adapted)} patterns, removed {len(removed)}, added {len(added_sections)} sections",
        }
    
    async def suggest_exercise_substitution(
        self,
        db: AsyncSession,
        user_id: int,
        movement: str,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Suggest alternative exercises (MVP: returns empty list).
        
        Args:
            db: Database session
            user_id: User ID
            movement: Movement to substitute
            context: Optional context (goal, intensity, equipment)
        
        Returns:
            Dict with suggested_movements (list), reasoning (str)
        """
        # MVP: no LLM-based suggestions yet
        return {
            "original_movement": movement,
            "suggested_movements": [],
            "reasoning": "LLM-based suggestions not yet implemented. Manual review needed.",
        }
    
    async def apply_movement_rule(
        self,
        db: AsyncSession,
        user_id: int,
        movement_id: int,
        rule_type: str,
        reason: str,
    ) -> "UserMovementRule":
        """
        Create or update a movement rule for user.
        
        Args:
            db: Database session
            user_id: User ID
            movement_id: Movement ID
            rule_type: Rule type (hard_no, hard_yes, preferred)
            reason: Reason for the rule
        
        Returns:
            Created/updated UserMovementRule
        """
        from app.models.enums import MovementRuleType, RuleCadence
        
        # Check if rule exists
        existing = await db.execute(
            select(UserMovementRule).where(
                and_(
                    UserMovementRule.user_id == user_id,
                    UserMovementRule.movement_id == movement_id
                )
            )
        )
        rule = existing.scalar_one_or_none()
        
        if rule:
            rule.rule_type = MovementRuleType(rule_type)
            rule.notes = reason
        else:
            rule = UserMovementRule(
                user_id=user_id,
                movement_id=movement_id,
                rule_type=MovementRuleType(rule_type),
                cadence=RuleCadence.PER_MICROCYCLE,
                notes=reason,
            )
            db.add(rule)
        
        await db.commit()
        return rule
    
    def _is_movement_forbidden(self, movement: Any, rules: List[Dict]) -> Optional[str]:
        """
        Check if movement violates any rules.
        
        Args:
            movement: Movement name
            rules: List of rule dicts
        
        Returns:
            Reason if forbidden, None otherwise
        """
        movement_id = getattr(movement, "id", None)
        movement_name = getattr(movement, "name", None) or str(movement)

        for rule in rules:
            if rule.get("rule_type") != "hard_no":
                continue

            if movement_id is not None and rule.get("movement_id") == movement_id:
                return rule.get("reason", "Rule violation")

            if "movement" in rule and isinstance(rule["movement"], str) and rule["movement"].lower() in movement_name.lower():
                return rule.get("reason", "Rule violation")
        return None
    
    def _check_soreness_conflict(
        self,
        pattern: "SessionExercise",
        soreness_data: Dict[str, int],
    ) -> Optional[str]:
        """
        Check if movement conflicts with reported soreness.
        
        Args:
            pattern: Movement pattern
            soreness_data: Dict of body_part -> soreness_level (0-10)
        
        Returns:
            Body part if conflict, None otherwise
        """
        if not soreness_data:
            return None
        
        movement_name = getattr(getattr(pattern, "movement", None), "name", None) or ""
        movement_lower = movement_name.lower()
        for body_part, level in soreness_data.items():
            # Simple heuristic: if body part mentioned in movement name and soreness > 6
            if level > 6 and body_part.lower() in movement_lower:
                return body_part
        
        return None
    
    def _adjust_volume(
        self,
        pattern: "SessionExercise",
        recovery: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Adjust sets/reps based on recovery status.
        
        Args:
            pattern: Movement pattern
            recovery: Recovery assessment dict
        
        Returns:
            Adjusted pattern dict
        """
        recovery_score = recovery.get("recovery_score", 50)
        
        adjusted = {
            "movement": getattr(getattr(pattern, "movement", None), "name", None),
            "sets": pattern.target_sets,
            "rep_range_min": pattern.target_rep_range_min,
            "rep_range_max": pattern.target_rep_range_max,
            "rpe": pattern.target_rpe,
        }
        
        if recovery_score < 40:
            # Low recovery: reduce sets, increase reps
            adjusted["sets"] = max(2, pattern.target_sets - 1)
            if adjusted["rep_range_min"] is not None:
                adjusted["rep_range_min"] = min(20, adjusted["rep_range_min"] + 1)
            if adjusted["rep_range_max"] is not None:
                adjusted["rep_range_max"] = min(20, adjusted["rep_range_max"] + 2)
            if adjusted["rpe"] is not None:
                adjusted["rpe"] = max(5, adjusted["rpe"] - 1)
            adjusted["note"] = "Volume reduced due to low recovery"
        elif recovery_score > 75:
            # High recovery: increase sets or reps
            adjusted["sets"] = pattern.target_sets + 1
            adjusted["note"] = "Volume increased due to strong recovery"
        
        return adjusted
    
    async def _get_movement_rules(self, db: AsyncSession, user_id: int) -> List[Dict]:
        """
        Fetch all movement rules for user.
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            List of rule dicts
        """
        result = await db.execute(
            select(UserMovementRule).where(UserMovementRule.user_id == user_id)
        )
        rules = list(result.scalars().all())
        
        return [
            {
                "movement_id": r.movement_id,
                "rule_type": r.rule_type.value if hasattr(r.rule_type, 'value') else r.rule_type,
                "reason": r.notes or "",
            }
            for r in rules
        ]
    
    async def _get_user_preferences(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """
        Fetch user preferences (enjoyable activities, etc).
        
        Args:
            db: Database session
            user_id: User ID
        
        Returns:
            Dict of preferences
        """
        result = await db.execute(
            select(UserEnjoyableActivity).where(UserEnjoyableActivity.user_id == user_id)
        )
        activities = list(result.scalars().all())
        
        enjoyable = [str(a.activity_type.value) if hasattr(a.activity_type, 'value') else str(a.activity_type) for a in activities if a.enabled]
        
        return {
            "enjoyable_activities": enjoyable,
        }
    
    async def _assess_recovery(
        self,
        db: AsyncSession,
        user_id: int,
        request: AdaptationRequest,
    ) -> Dict[str, Any]:
        """
        Assess overall recovery status.
        
        Args:
            db: Database session
            user_id: User ID
            request: Adaptation request with recovery signals
        
        Returns:
            Recovery assessment dict with recovery_score (0-100)
        """
        components = []
        
        # Recovery signal from request
        if request.recovery:
            sleep_hours = request.recovery.sleep_hours or 7
            sleep_score = min(100, (sleep_hours / 8) * 100)  # 8 hours = 100%
            energy = request.recovery.energy_level or 5
            stress = 100 - (request.recovery.stress_level or 5) * 10  # Higher stress = lower recovery
            components = [sleep_score, energy * 10, stress]
        
        # Soreness impact (negative)
        if request.soreness:
            max_soreness = max([s.level for s in request.soreness])
            soreness_impact = (5 - max_soreness) * 20  # 5 level scale -> 0-100
            components.append(soreness_impact)
        
        # Calculate average
        recovery_score = int(sum(components) / len(components)) if components else 50
        
        return {
            "recovery_score": max(0, min(100, recovery_score)),
            "components": components,
        }


# Singleton instance
adaptation_service = AdaptationService()
