"""Session quality KPIs for block-specific validation.

This module provides comprehensive validation for training sessions against
block-specific movement count requirements and structural completeness criteria.

The SessionQualityKPI class validates:
- Movement counts per block (warmup, cooldown, main, accessory, finisher)
- Structural completeness (warmup + main + (accessory/finisher) + cooldown)
- Session-type specific requirements

Block-Specific Movement Count Rules:
- Warmup: 2-5 movements
- Cooldown: 2-5 movements
- Main: 2-5 (strength/hypertrophy/cardio), 6-10 (endurance)
- Accessory: 2-4 movements
- Finisher: 1 unit (circuit counted as whole, not individual movements)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.enums import SessionType

from app.ml.scoring.base import BaseValidationResult, ValidationMixin
from app.ml.scoring.constants import (
    MessageTemplates,
    MovementCounts,
    SessionTypes,
)
from app.ml.scoring.exceptions import (
    BlockCountValidationError,
    SessionValidationError,
    StructureValidationError,
    ValidationException,
)
from app.ml.scoring.validators import validate_range

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlockValidationResult(BaseValidationResult):
    """Result of validating a single block's movement count.

    Attributes:
        block_name: Name of the block (e.g., 'warmup', 'main', 'accessory')
        actual_count: Actual number of movements in the block
        expected_min: Minimum expected movement count
        expected_max: Maximum expected movement count
        passed: Whether the validation passed
        message: Detailed feedback message
    """

    block_name: str
    actual_count: int
    expected_min: int
    expected_max: int
    passed: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "block_name": self.block_name,
            "actual_count": self.actual_count,
            "expected_min": self.expected_min,
            "expected_max": self.expected_max,
            "passed": self.passed,
            "message": self.message,
        }


@dataclass(frozen=True)
class StructureValidationResult(BaseValidationResult):
    """Result of validating session structure completeness.

    Attributes:
        has_warmup: Whether session has warmup block
        has_main: Whether session has main block
        has_accessory_or_finisher: Whether session has accessory or finisher
        has_cooldown: Whether session has cooldown block
        passed: Whether structure is complete
        message: Detailed feedback message
        missing_blocks: List of missing block names
    """

    has_warmup: bool
    has_main: bool
    has_accessory_or_finisher: bool
    has_cooldown: bool
    passed: bool
    message: str
    missing_blocks: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_warmup": self.has_warmup,
            "has_main": self.has_main,
            "has_accessory_or_finisher": self.has_accessory_or_finisher,
            "has_cooldown": self.has_cooldown,
            "passed": self.passed,
            "message": self.message,
            "missing_blocks": list(self.missing_blocks),
        }


@dataclass(frozen=True)
class SessionValidationResult:
    """Complete result of session quality validation.

    Attributes:
        session_type: Type of session being validated
        passed: Whether all validations passed
        block_validations: List of block-specific validation results
        structure_validation: Structure completeness validation result
        overall_message: Summary message for the entire validation
        message: Alias for overall_message
    """

    session_type: str
    passed: bool
    block_validations: tuple[BlockValidationResult, ...]
    structure_validation: StructureValidationResult
    overall_message: str

    @property
    def message(self) -> str:
        """Alias for overall_message."""
        return self.overall_message

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_type": self.session_type,
            "passed": self.passed,
            "block_validations": [b.to_dict() for b in self.block_validations],
            "structure_validation": self.structure_validation.to_dict(),
            "overall_message": self.overall_message,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_type": self.session_type,
            "passed": self.passed,
            "block_validations": [b.to_dict() for b in self.block_validations],
            "structure_validation": self.structure_validation.to_dict(),
            "overall_message": self.overall_message,
        }


@dataclass(frozen=True)
class SessionResult:
    """Session result containing exercise blocks.

    Attributes:
        session_id: ID of the session
        session_type: Type of the session
        warmup_exercises: List of warmup exercise IDs
        main_exercises: List of main exercise IDs
        accessory_exercises: List of accessory exercise IDs
        finisher_exercises: List of finisher exercise IDs
        cooldown_exercises: List of cooldown exercise IDs
        finisher_circuit_id: Optional circuit ID for finisher
    """

    session_id: int
    session_type: str
    warmup_exercises: list[int] = field(default_factory=list)
    main_exercises: list[int] = field(default_factory=list)
    accessory_exercises: list[int] = field(default_factory=list)
    finisher_exercises: list[int] = field(default_factory=list)
    cooldown_exercises: list[int] = field(default_factory=list)
    finisher_circuit_id: int | None = None


class SessionQualityKPI:
    """Validator for session quality KPIs with block-specific validation.

    This class provides comprehensive validation of training sessions against
    movement count requirements per block and structural completeness criteria.

    Example:
        >>> validator = SessionQualityKPI()
        >>> result = SessionResult(
        ...     session_id=1,
        ...     session_type="strength",
        ...     warmup_exercises=[1, 2, 3],
        ...     main_exercises=[4, 5, 6],
        ...     accessory_exercises=[7, 8],
        ...     cooldown_exercises=[9, 10]
        ... )
        >>> validation = validator.validate_session(result)
        >>> print(validation.overall_message)
        >>> print(validation.passed)
    """

    def __init__(self) -> None:
        """Initialize the session quality KPI validator."""
        logger.debug("Initialized SessionQualityKPI validator")

    def validate_session(self, session_result: SessionResult) -> SessionValidationResult:
        """Validate complete session quality including all blocks and structure.

        Args:
            session_result: Session result containing exercise blocks.

        Returns:
            SessionValidationResult: Complete validation result with all details.

        Raises:
            SessionValidationError: If validation process fails.
        """
        try:
            # Validate block counts
            block_validations = self.validate_block_counts(
                session_result, session_result.session_type
            )

            # Validate structure
            structure_validation = self.validate_structure(session_result)

            # Determine overall pass/fail
            all_blocks_passed = all(bv.passed for bv in block_validations)
            structure_passed = structure_validation.passed
            overall_passed = all_blocks_passed and structure_passed

            # Build overall message
            overall_message = self._build_overall_message(
                session_result.session_type,
                overall_passed,
                block_validations,
                structure_validation,
            )

            return SessionValidationResult(
                session_type=session_result.session_type,
                passed=overall_passed,
                block_validations=block_validations,
                structure_validation=structure_validation,
                overall_message=overall_message,
            )

        except Exception as e:
            raise SessionValidationError(
                f"Failed to validate session {session_result.session_id}: {e}"
            ) from e

    def validate_block_counts(
        self, session_result: SessionResult, session_type: str | SessionType
    ) -> tuple[BlockValidationResult, ...]:
        """Validate movement counts per block for the session.

        Validates each block against its specific movement count range:
        - Warmup: 2-5 movements
        - Cooldown: 2-5 movements
        - Main: 2-5 (strength/hypertrophy/cardio), 6-10 (endurance)
        - Accessory: 2-4 movements
        - Finisher: 1 unit (circuit counted as whole)

        Args:
            session_result: Session result containing exercise blocks.
            session_type: Type of session for determining main block requirements.

        Returns:
            Tuple of BlockValidationResult objects for each block.

        Raises:
            BlockCountValidationError: If block count validation fails.
        """
        try:
            # Normalize session type to string
            session_type_str = (
                session_type.value
                if hasattr(session_type, "value")
                else str(session_type).lower()
            )

            # Determine main block range based on session type
            main_min, main_max = MovementCounts.get_main_block_range(session_type_str)

            # Validate each block
            validations: list[BlockValidationResult] = []

            # Warmup
            warmup_count = len(session_result.warmup_exercises)
            validations.append(
                self._validate_block_range(
                    "warmup",
                    warmup_count,
                    MovementCounts.WARMUP_MIN,
                    MovementCounts.WARMUP_MAX,
                )
            )

            # Cooldown
            cooldown_count = len(session_result.cooldown_exercises)
            validations.append(
                self._validate_block_range(
                    "cooldown",
                    cooldown_count,
                    MovementCounts.COOLDOWN_MIN,
                    MovementCounts.COOLDOWN_MAX,
                )
            )

            # Main
            main_count = len(session_result.main_exercises)
            validations.append(
                self._validate_block_range(
                    "main",
                    main_count,
                    main_min,
                    main_max,
                    session_type_str,
                )
            )

            # Accessory (optional, but check if present)
            if session_result.accessory_exercises:
                accessory_count = len(session_result.accessory_exercises)
                validations.append(
                    self._validate_block_range(
                        "accessory",
                        accessory_count,
                        MovementCounts.ACCESSORY_MIN,
                        MovementCounts.ACCESSORY_MAX,
                    )
                )

            # Finisher (optional, special handling for circuits)
            if session_result.finisher_exercises or session_result.finisher_circuit_id:
                # If circuit is present, count as 1 unit
                if session_result.finisher_circuit_id:
                    finisher_count = 1
                    finisher_passed = True
                    finisher_message = (
                        f"Finisher has 1 circuit unit (acceptable: 1 unit)"
                    )
                else:
                    finisher_count = len(session_result.finisher_exercises)
                    finisher_passed = finisher_count == 1
                    finisher_message = (
                        f"Finisher has {finisher_count} movement(s) "
                        f"(expected: 1 unit, counted as whole)"
                    )

                validations.append(
                    BlockValidationResult(
                        block_name="finisher",
                        actual_count=finisher_count,
                        expected_min=1,
                        expected_max=1,
                        passed=finisher_passed,
                        message=finisher_message,
                    )
                )

            logger.debug(
                f"Validated block counts for session {session_result.session_id}: "
                f"{sum(1 for v in validations if v.passed)}/{len(validations)} passed"
            )

            return tuple(validations)

        except Exception as e:
            raise BlockCountValidationError(
                f"Failed to validate block counts for session {session_result.session_id}: {e}"
            ) from e

    def validate_structure(
        self, session_result: SessionResult
    ) -> StructureValidationResult:
        """Validate session structure completeness.

        Criteria: warmup + main + (accessory OR finisher) + cooldown

        Args:
            session_result: Session result containing exercise blocks.

        Returns:
            StructureValidationResult: Structure validation result with details.

        Raises:
            StructureValidationError: If structure validation fails.
        """
        try:
            # Check for each required component
            has_warmup = len(session_result.warmup_exercises) > 0
            has_main = len(session_result.main_exercises) > 0
            has_accessory_or_finisher = (
                len(session_result.accessory_exercises) > 0
                or len(session_result.finisher_exercises) > 0
                or session_result.finisher_circuit_id is not None
            )
            has_cooldown = len(session_result.cooldown_exercises) > 0

            # Determine if structure is complete
            passed = has_warmup and has_main and has_accessory_or_finisher and has_cooldown

            # Collect missing blocks
            missing_blocks: list[str] = []
            if not has_warmup:
                missing_blocks.append("warmup")
            if not has_main:
                missing_blocks.append("main")
            if not has_accessory_or_finisher:
                missing_blocks.append("accessory/finisher")
            if not has_cooldown:
                missing_blocks.append("cooldown")

            # Build message
            if passed:
                message = "Session structure is complete: warmup + main + (accessory/finisher) + cooldown"
            else:
                message = (
                    f"Session structure incomplete. Missing required blocks: "
                    f"{', '.join(missing_blocks)}"
                )

            logger.debug(
                f"Validated structure for session {session_result.session_id}: "
                f"passed={passed}, missing={missing_blocks}"
            )

            return StructureValidationResult(
                has_warmup=has_warmup,
                has_main=has_main,
                has_accessory_or_finisher=has_accessory_or_finisher,
                has_cooldown=has_cooldown,
                passed=passed,
                message=message,
                missing_blocks=tuple(missing_blocks),
            )

        except Exception as e:
            raise StructureValidationError(
                f"Failed to validate structure for session {session_result.session_id}: {e}"
            ) from e

    def _validate_block_range(
        self,
        block_name: str,
        actual_count: int,
        min_count: int,
        max_count: int,
        session_type: str | None = None,
    ) -> BlockValidationResult:
        """Validate that a block's movement count falls within acceptable range.

        Args:
            block_name: Name of the block being validated.
            actual_count: Actual movement count in the block.
            min_count: Minimum acceptable count.
            max_count: Maximum acceptable count.
            session_type: Optional session type for context in message.

        Returns:
            BlockValidationResult: Validation result for the block.
        """
        # Use validators.validate_range for range validation
        validation_result = validate_range(
            actual_count,
            min_val=min_count,
            max_val=max_count,
            field_name=block_name,
        )
        passed = validation_result.is_valid

        if passed:
            message = (
                f"{block_name.capitalize()} has {actual_count} movement(s) "
                f"(acceptable range: {min_count}-{max_count})"
            )
        else:
            # Provide more specific feedback based on what's wrong
            if actual_count < min_count:
                message = (
                    f"{block_name.capitalize()} has {actual_count} movement(s), "
                    f"which is below minimum {min_count}. "
                    f"Add {min_count - actual_count} more movement(s)."
                )
            else:
                message = (
                    f"{block_name.capitalize()} has {actual_count} movement(s), "
                    f"which exceeds maximum {max_count}. "
                    f"Remove {actual_count - max_count} movement(s)."
                )

            # Add session type context for main block
            if block_name == "main" and session_type:
                if session_type in SessionTypes.CONDITIONING_TYPES:
                    range_note = "Endurance sessions require 6-10 main movements"
                else:
                    range_note = "Regular sessions require 2-5 main movements"
                message += f" ({range_note})"

        return BlockValidationResult(
            block_name=block_name,
            actual_count=actual_count,
            expected_min=min_count,
            expected_max=max_count,
            passed=passed,
            message=message,
        )

    def _build_overall_message(
        self,
        session_type: str,
        passed: bool,
        block_validations: tuple[BlockValidationResult, ...],
        structure_validation: StructureValidationResult,
    ) -> str:
        """Build overall validation message.

        Args:
            session_type: Type of session validated.
            passed: Whether overall validation passed.
            block_validations: Block validation results.
            structure_validation: Structure validation result.

        Returns:
            Overall validation message.
        """
        if passed:
            return (
                f"Session type '{session_type}' passed all quality checks. "
                f"All blocks have acceptable movement counts and "
                f"structure is complete."
            )

        # Build detailed failure message
        issues: list[str] = []

        # Add structure issues
        if not structure_validation.passed:
            issues.append(structure_validation.message)

        # Add block count issues
        failed_blocks = [bv for bv in block_validations if not bv.passed]
        for block in failed_blocks:
            issues.append(block.message)

        return (
            f"Session type '{session_type}' failed quality checks. "
            f"Issues: {'; '.join(issues)}"
        )
