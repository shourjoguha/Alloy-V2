"""Base classes and protocols for scoring KPI validation results.

This module provides the foundation for all validation result classes used across
KPI modules (session quality, variety, muscle coverage, etc.). It defines a
consistent interface and structure for validation results.

The ValidationResult protocol ensures that all KPI validators return results with
a consistent interface, enabling generic handling of validation results across
the scoring system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol


class ValidationResult(Protocol):
    """Protocol defining the interface for all validation result classes.

    All KPI validation results must implement this protocol to ensure
    consistent handling across the scoring system. The protocol requires
    a `passed` boolean, a descriptive `message`, and a `to_dict()`
    method for serialization.

    Attributes:
        passed: Whether validation passed (True) or failed (False)
        message: Human-readable description of validation result

    Methods:
        to_dict(): Convert validation result to dictionary for serialization

    Example:
        ```python
        @dataclass(frozen=True)
        class MyValidationResult(ValidationResult):
            passed: bool
            message: str
            score: float  # Additional field specific to this validator

            def to_dict(self) -> dict[str, Any]:
                return {
                    "passed": self.passed,
                    "message": self.message,
                    "score": self.score,
                }
        ```
    """

    passed: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        """Convert validation result to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the validation result with all fields.
        """
        ...


@dataclass(frozen=True)
class BaseValidationResult:
    """Base implementation for validation results.

    This class provides a frozen dataclass foundation that implements
    the ValidationResult protocol. It includes common fields and methods
    that all validation results share.

    Subclasses can add additional fields specific to their validation context
    while inheriting the core validation result structure.

    Attributes:
        passed: Whether validation passed (True) or failed (False)
        message: Human-readable description of validation result

    Example:
        ```python
        @dataclass(frozen=True)
        class BlockValidationResult(BaseValidationResult):
            block_name: str
            actual_count: int
            expected_min: int
            expected_max: int

            def to_dict(self) -> dict[str, Any]:
                return {
                    "passed": self.passed,
                    "message": self.message,
                    "block_name": self.block_name,
                    "actual_count": self.actual_count,
                    "expected_min": self.expected_min,
                    "expected_max": self.expected_max,
                }
        ```
    """

    passed: bool
    message: str


class BaseValidator(ABC):
    """Abstract base class for all KPI validators.

    This class defines the common interface and structure for validators
    across all KPI modules. It provides logging infrastructure and
    a consistent validation pattern.

    Subclasses must implement the validate() method and should use
    the protected _log_validation() method for consistent logging.

    Example:
        ```python
        class MyValidator(BaseValidator):
            def __init__(self) -> None:
                super().__init__(__name__)

            def validate(self, data: Any) -> ValidationResult:
                # Implementation
                result = self._do_validation(data)
                self._log_validation("my_validation", result.passed)
                return result
        ```
    """

    def __init__(self, logger_name: str) -> None:
        """Initialize the base validator.

        Args:
            logger_name: Name for the logger instance (typically __name__)
        """
        self._logger_name = logger_name

    @abstractmethod
    def validate(self, *args: Any, **kwargs: Any) -> ValidationResult:
        """Perform validation and return result.

        This method must be implemented by all validator subclasses.

        Args:
            *args: Positional arguments specific to the validator
            **kwargs: Keyword arguments specific to the validator

        Returns:
            ValidationResult: The validation result

        Raises:
            ValidationError: If validation process encounters an error
        """
        ...

    def _log_validation(
        self,
        validation_name: str,
        passed: bool,
        context: str | None = None,
    ) -> None:
        """Log validation result with consistent format.

        This protected method provides consistent logging across all validators.
        It logs at DEBUG level for successful validations and WARNING level
        for failed validations.

        Args:
            validation_name: Name/type of validation performed
            passed: Whether validation passed
            context: Optional additional context for the log message
        """
        import logging

        logger = logging.getLogger(self._logger_name)

        status = "passed" if passed else "failed"
        context_str = f" - {context}" if context else ""

        if passed:
            logger.debug(f"{validation_name} validation{status_str}: {status}{context_str}")
        else:
            logger.warning(f"{validation_name} validation{status_str}: {status}{context_str}")


class ValidationMixin:
    """Mixin providing common validation utility methods.

    This mixin can be used by validator classes to add common validation
    helper methods without requiring inheritance from BaseValidator.

    Methods:
        _build_pass_message(): Build a success message
        _build_fail_message(): Build a failure message
        _format_range(): Format a range for display
    """

    @staticmethod
    def _build_pass_message(
        validation_name: str,
        entity_id: int | str,
        details: str | None = None,
    ) -> str:
        """Build a standardized pass message.

        Args:
            validation_name: Name of the validation
            entity_id: ID of the entity being validated
            details: Optional additional details

        Returns:
            Formatted pass message
        """
        message = f"{validation_name} passed for {entity_id}"
        if details:
            message += f". {details}"
        return message

    @staticmethod
    def _build_fail_message(
        validation_name: str,
        entity_id: int | str,
        reasons: list[str],
        recommendations: list[str] | None = None,
    ) -> str:
        """Build a standardized fail message.

        Args:
            validation_name: Name of the validation
            entity_id: ID of the entity being validated
            reasons: List of failure reasons
            recommendations: Optional list of recommendations

        Returns:
            Formatted fail message
        """
        message = f"{validation_name} failed for {entity_id}. "
        message += f"Reasons: {'; '.join(reasons)}."
        if recommendations:
            message += f" Recommendations: {'; '.join(recommendations)}."
        return message

    @staticmethod
    def _format_range(min_val: float | int, max_val: float | int) -> str:
        """Format a range for display.

        Args:
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            Formatted range string
        """
        return f"{min_val}-{max_val}"
