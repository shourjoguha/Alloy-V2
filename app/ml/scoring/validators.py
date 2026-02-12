"""Shared validation utilities for ML scoring system.

This module provides reusable validation functions and utilities that can be used
across KPI modules to eliminate duplicate validation logic and ensure consistent
error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Protocol,
    Sequence,
    TypeVar,
    Union,
)

import numpy as np
from pydantic import ValidationError, conint, constr


__all__ = [
    "ValidationErrorResult",
    "ValidationResult",
    "Validator",
    "StatisticalMetrics",
    "validate_range",
    "validate_value",
    "validate_numeric_sequence",
    "calculate_statistics",
    "build_validation_message",
    "create_validator",
    "chain_validators",
]


T = TypeVar("T")
N = TypeVar("N", int, float)


@dataclass(frozen=True)
class ValidationErrorResult:
    """Represents a single validation error.

    Attributes:
        field: Name of the field that failed validation
        message: Human-readable error message
        value: The value that failed validation
        constraint: Description of the constraint that was violated
    """

    field: str
    message: str
    value: Any
    constraint: str


@dataclass(frozen=True)
class ValidationResult(Generic[T]):
    """Generic container for validation results.

    Attributes:
        is_valid: Whether validation passed
        value: The validated value (if valid)
        errors: List of validation errors (if invalid)
    """

    is_valid: bool
    value: T | None
    errors: list[ValidationErrorResult]

    @classmethod
    def valid(cls, value: T) -> ValidationResult[T]:
        """Create a successful validation result."""
        return cls(is_valid=True, value=value, errors=[])

    @classmethod
    def invalid(cls, errors: Sequence[ValidationErrorResult]) -> ValidationResult[T]:
        """Create a failed validation result."""
        return cls(is_valid=False, value=None, errors=list(errors))


@dataclass(frozen=True)
class StatisticalMetrics:
    """Container for statistical calculation results.

    Attributes:
        mean: Arithmetic mean of the values
        median: Median of the values
        std: Standard deviation
        min_val: Minimum value
        max_val: Maximum value
        count: Number of values in the dataset
    """

    mean: float
    median: float
    std: float
    min_val: float
    max_val: float
    count: int

    def to_dict(self) -> dict[str, float | int]:
        """Convert metrics to dictionary format."""
        return {
            "mean": self.mean,
            "median": self.median,
            "std": self.std,
            "min": self.min_val,
            "max": self.max_val,
            "count": self.count,
        }


class Validator(Protocol[T]):
    """Protocol for validator functions.

    A validator is a callable that takes a value and returns a ValidationResult.
    """

    def __call__(self, value: T) -> ValidationResult[T]: ...


def validate_range(
    value: N,
    min_val: N | None = None,
    max_val: N | None = None,
    inclusive: bool = True,
    field_name: str = "value",
) -> ValidationResult[N]:
    """Validate that a numeric value falls within the specified range.

    Args:
        value: The numeric value to validate
        min_val: Minimum allowed value (None for no minimum)
        max_val: Maximum allowed value (None for no maximum)
        inclusive: Whether the range boundaries are inclusive
        field_name: Name of the field being validated (for error messages)

    Returns:
        ValidationResult indicating success or failure

    Examples:
        >>> validate_range(5, min_val=0, max_val=10)
        ValidationResult(is_valid=True, value=5, errors=[])

        >>> validate_range(15, min_val=0, max_val=10)
        ValidationResult(is_valid=False, value=None, errors=[...])
    """
    errors: list[ValidationErrorResult] = []

    if min_val is not None:
        if inclusive and value < min_val:
            errors.append(
                ValidationErrorResult(
                    field=field_name,
                    message=f"Value must be at least {min_val}",
                    value=value,
                    constraint=f">={min_val}",
                )
            )
        elif not inclusive and value <= min_val:
            errors.append(
                ValidationErrorResult(
                    field=field_name,
                    message=f"Value must be greater than {min_val}",
                    value=value,
                    constraint=f">{min_val}",
                )
            )

    if max_val is not None:
        if inclusive and value > max_val:
            errors.append(
                ValidationErrorResult(
                    field=field_name,
                    message=f"Value must be at most {max_val}",
                    value=value,
                    constraint=f"<={max_val}",
                )
            )
        elif not inclusive and value >= max_val:
            errors.append(
                ValidationErrorResult(
                    field=field_name,
                    message=f"Value must be less than {max_val}",
                    value=value,
                    constraint=f"<{max_val}",
                )
            )

    if errors:
        return ValidationResult.invalid(errors)

    return ValidationResult.valid(value)


def validate_value(
    value: Any,
    validator: Callable[[Any], bool],
    error_message: str,
    field_name: str = "value",
    constraint_description: str = "custom constraint",
) -> ValidationResult[Any]:
    """Generic validator utility that applies a custom validation function.

    Args:
        value: The value to validate
        validator: Callable that returns True if value is valid
        error_message: Human-readable error message if validation fails
        field_name: Name of the field being validated
        constraint_description: Description of the constraint being checked

    Returns:
        ValidationResult indicating success or failure

    Examples:
        >>> is_even = lambda x: x % 2 == 0
        >>> validate_value(4, is_even, "Value must be even")
        ValidationResult(is_valid=True, value=4, errors=[])

        >>> validate_value(3, is_even, "Value must be even")
        ValidationResult(is_valid=False, value=None, errors=[...])
    """
    try:
        if validator(value):
            return ValidationResult.valid(value)

        return ValidationResult.invalid(
            [
                ValidationErrorResult(
                    field=field_name,
                    message=error_message,
                    value=value,
                    constraint=constraint_description,
                )
            ]
        )
    except Exception as e:
        return ValidationResult.invalid(
            [
                ValidationErrorResult(
                    field=field_name,
                    message=f"Validation failed: {str(e)}",
                    value=value,
                    constraint=constraint_description,
                )
            ]
        )


def validate_numeric_sequence(
    values: Sequence[N],
    min_length: int | None = None,
    max_length: int | None = None,
    min_value: N | None = None,
    max_value: N | None = None,
    field_name: str = "sequence",
) -> ValidationResult[Sequence[N]]:
    """Validate a sequence of numeric values.

    Args:
        values: Sequence of numeric values to validate
        min_length: Minimum number of elements (None for no minimum)
        max_length: Maximum number of elements (None for no maximum)
        min_value: Minimum allowed value per element (None for no minimum)
        max_value: Maximum allowed value per element (None for no maximum)
        field_name: Name of the field being validated

    Returns:
        ValidationResult indicating success or failure

    Examples:
        >>> validate_numeric_sequence([1, 2, 3], min_length=1, max_value=10)
        ValidationResult(is_valid=True, value=[1, 2, 3], errors=[])
    """
    errors: list[ValidationErrorResult] = []

    # Validate sequence length
    if min_length is not None and len(values) < min_length:
        errors.append(
            ValidationErrorResult(
                field=field_name,
                message=f"Sequence must have at least {min_length} elements",
                value=len(values),
                constraint=f"length>={min_length}",
            )
        )

    if max_length is not None and len(values) > max_length:
        errors.append(
            ValidationErrorResult(
                field=field_name,
                message=f"Sequence must have at most {max_length} elements",
                value=len(values),
                constraint=f"length<={max_length}",
            )
        )

    # Validate individual values
    if min_value is not None or max_value is not None:
        for idx, val in enumerate(values):
            result = validate_range(
                val,
                min_val=min_value,
                max_val=max_value,
                field_name=f"{field_name}[{idx}]",
            )
            if not result.is_valid:
                errors.extend(result.errors)

    if errors:
        return ValidationResult.invalid(errors)

    return ValidationResult.valid(values)


def calculate_statistics(values: Iterable[N]) -> StatisticalMetrics:
    """Calculate statistical metrics for a collection of numeric values.

    Args:
        values: Iterable of numeric values

    Returns:
        StatisticalMetrics containing mean, median, std, min, max, and count

    Raises:
        ValueError: If values is empty

    Examples:
        >>> calculate_statistics([1, 2, 3, 4, 5])
        StatisticalMetrics(mean=3.0, median=3.0, std=1.414..., min_val=1.0, ...)
    """
    # Convert to numpy array for efficient calculations
    arr = np.array(list(values), dtype=float)

    if len(arr) == 0:
        raise ValueError("Cannot calculate statistics on empty sequence")

    return StatisticalMetrics(
        mean=float(np.mean(arr)),
        median=float(np.median(arr)),
        std=float(np.std(arr)),
        min_val=float(np.min(arr)),
        max_val=float(np.max(arr)),
        count=len(arr),
    )


def build_validation_message(
    results: Sequence[ValidationResult[Any]],
    prefix: str = "Validation failed",
    separator: str = "\n",
) -> str:
    """Build a formatted message from validation results.

    Args:
        results: Sequence of ValidationResult objects
        prefix: Prefix for the message (used if any validation failed)
        separator: String used to separate error messages

    Returns:
        Formatted message string, or empty string if all validations passed

    Examples:
        >>> result1 = validate_range(15, min_val=0, max_val=10)
        >>> result2 = validate_range(-5, min_val=0, max_val=10)
        >>> build_validation_message([result1, result2])
        "Validation failed\\nvalue: Value must be at most 10\\nvalue: Value must be at least 0"
    """
    all_errors: list[ValidationErrorResult] = []

    for result in results:
        if not result.is_valid:
            all_errors.extend(result.errors)

    if not all_errors:
        return ""

    error_messages = [
        f"{error.field}: {error.message} (got {error.value}, constraint: {error.constraint})"
        for error in all_errors
    ]

    return f"{prefix}{separator}{separator.join(error_messages)}"


def create_validator(
    validators: Sequence[Validator[T]],
    stop_on_first_error: bool = False,
) -> Validator[T]:
    """Create a composite validator from multiple validators.

    Args:
        validators: Sequence of validator functions
        stop_on_first_error: Whether to stop validation on first error

    Returns:
        Composite validator function

    Examples:
        >>> range_validator = lambda x: validate_range(x, 0, 100)
        >>> even_validator = lambda x: validate_value(x, lambda v: v % 2 == 0, "Must be even")
        >>> combined = create_validator([range_validator, even_validator])
        >>> combined(50).is_valid
        True
    """
    def validator(value: T) -> ValidationResult[T]:
        errors: list[ValidationErrorResult] = []

        for v in validators:
            result = v(value)
            if not result.is_valid:
                errors.extend(result.errors)
                if stop_on_first_error:
                    break

        if errors:
            return ValidationResult.invalid(errors)

        return ValidationResult.valid(value)

    return validator


def chain_validators(
    *validators: Validator[T],
) -> Validator[T]:
    """Chain multiple validators together in sequence.

    Each validator receives the output of the previous validator.
    This is useful for validation pipelines where each step depends on the previous.

    Args:
        *validators: Variable number of validators to chain

    Returns:
        Chained validator function

    Examples:
        >>> def strip_validator(s: str) -> ValidationResult[str]:
        ...     return ValidationResult.valid(s.strip())
        >>> def length_validator(s: str) -> ValidationResult[str]:
        ...     return validate_range(len(s), 1, 100, field_name="length")
        >>> def content_validator(s: str) -> ValidationResult[str]:
        ...     return validate_value(s, bool, "String cannot be empty", "content")
        >>> chained = chain_validators(strip_validator, content_validator)
        >>> result = chained("  hello  ")
    """
    def validator(value: T) -> ValidationResult[T]:
        current_value = value

        for v in validators:
            result = v(current_value)
            if not result.is_valid:
                return result  # type: ignore[return-value]
            current_value = result.value

        return ValidationResult.valid(current_value)

    return validator


# Common validators for reuse
def create_range_validator(
    min_val: N | None = None,
    max_val: N | None = None,
    field_name: str = "value",
) -> Validator[N]:
    """Factory function to create a range validator.

    Args:
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        field_name: Name of the field being validated

    Returns:
        Configured range validator function
    """
    return lambda value: validate_range(value, min_val, max_val, field_name=field_name)


def create_type_validator(expected_type: type[T], field_name: str = "value") -> Validator[Any]:
    """Factory function to create a type validator.

    Args:
        expected_type: The expected type for validation
        field_name: Name of the field being validated

    Returns:
        Configured type validator function
    """
    def validator(value: Any) -> ValidationResult[Any]:
        if isinstance(value, expected_type):
            return ValidationResult.valid(value)

        return ValidationResult.invalid(
            [
                ValidationErrorResult(
                    field=field_name,
                    message=f"Expected type {expected_type.__name__}, got {type(value).__name__}",
                    value=value,
                    constraint=f"isinstance({expected_type.__name__})",
                )
            ]
        )

    return validator
