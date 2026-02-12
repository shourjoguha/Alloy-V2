"""Consolidated exception hierarchy for scoring KPI modules.

This module provides a unified exception hierarchy for all scoring-related errors
across KPI validation modules (session quality, variety, muscle coverage, metrics).

Exception Hierarchy:
- ScoringException (base)
  - ValidationException (validation failures)
    - SessionValidationError (session-level validation failures)
    - BlockCountValidationError (block movement count failures)
    - StructureValidationError (session structure failures)
    - PatternRotationError (pattern rotation failures)
    - MovementDiversityError (movement diversity failures)
    - InsufficientCoverageError (muscle coverage failures)
    - MetricsValidationError (metrics validation failures)
  - StorageException (storage-related failures)
    - MetricsStorageError (metrics storage failures)

Example:
    try:
        validator.validate_session(session_result)
    except BlockCountValidationError as e:
        logger.error(f"Block count validation failed: {e}")
    except StructureValidationError as e:
        logger.error(f"Structure validation failed: {e}")
    except ScoringException as e:
        logger.error(f"General scoring error: {e}")
"""

from __future__ import annotations


# =============================================================================
# Base Exception
# =============================================================================

class ScoringException(Exception):
    """Base exception for all scoring-related errors.

    This is the root exception class for the entire scoring system.
    All scoring-related exceptions should inherit from this class to enable
    consistent error handling across the application.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context

    Example:
        ```python
        try:
            validate_session(session)
        except ScoringException as e:
            logger.error(f"Scoring error: {e}")
            # Handle all scoring errors uniformly
        ```
    """

    def __init__(self, message: str, details: dict | None = None) -> None:
        """Initialize the scoring exception.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return string representation."""
        return self.message


# =============================================================================
# Validation Exceptions
# =============================================================================

class ValidationException(ScoringException):
    """Base exception for validation-related errors.

    This exception class represents failures in validation processes
    across all KPI modules. It serves as a parent class for specific
    validation failure types.

    Example:
        ```python
        try:
            validate_kpi(data)
        except ValidationException as e:
            logger.warning(f"Validation failed: {e}")
        ```
    """

    pass


class SessionValidationError(ValidationException):
    """Raised when session-level validation fails.

    This exception is raised when a session fails validation checks,
    such as missing required blocks or invalid structure.

    Example:
        ```python
        if not has_warmup or not has_main or not has_cooldown:
            raise SessionValidationError(
                "Session structure incomplete",
                details={"missing_blocks": ["warmup", "cooldown"]}
            )
        ```
    """

    pass


class BlockCountValidationError(ValidationException):
    """Raised when block movement count validation fails.

    This exception is raised when a session block (warmup, main, accessory,
    cooldown, finisher) has an invalid number of movements.

    Example:
        ```python
        if actual_count < min_count or actual_count > max_count:
            raise BlockCountValidationError(
                f"Block '{block_name}' has {actual_count} movements, "
                f"expected {min_count}-{max_count}",
                details={
                    "block_name": block_name,
                    "actual_count": actual_count,
                    "expected_min": min_count,
                    "expected_max": max_count,
                }
            )
        ```
    """

    pass


class StructureValidationError(ValidationException):
    """Raised when session structure validation fails.

    This exception is raised when a session does not have the required
    structural components (warmup + main + accessory/finisher + cooldown).

    Example:
        ```python
        if not (has_warmup and has_main and has_accessory_or_finisher and has_cooldown):
            raise StructureValidationError(
                "Session structure incomplete",
                details={"missing_blocks": missing_blocks}
            )
        ```
    """

    pass


class PatternRotationError(ValidationException):
    """Raised when pattern rotation validation fails.

    This exception is raised when a movement pattern is repeated within
    the minimum required number of sessions of the same type.

    Example:
        ```python
        if current_pattern in recent_patterns:
            raise PatternRotationError(
                f"Pattern '{current_pattern}' repeated within 2 sessions",
                details={
                    "pattern": current_pattern,
                    "session_type": session_type,
                    "recent_sessions": recent_patterns,
                }
            )
        ```
    """

    pass


class MovementDiversityError(ValidationException):
    """Raised when movement diversity validation fails.

    This exception is raised when a microcycle has insufficient movement
    variety (too many repeated movements).

    Example:
        ```python
        if unique_percentage < threshold:
            raise MovementDiversityError(
                f"Movement diversity {unique_percentage:.1f}% below threshold {threshold}%",
                details={
                    "unique_percentage": unique_percentage,
                    "threshold": threshold,
                    "unique_movements": unique_count,
                    "total_movements": total_count,
                }
            )
        ```
    """

    pass


class InsufficientCoverageError(ValidationException):
    """Raised when muscle coverage validation fails.

    This exception is raised when a microcycle does not cover all required
    major muscle groups.

    Example:
        ```python
        if coverage_score < threshold:
            raise InsufficientCoverageError(
                f"Muscle coverage {coverage_score:.1f}% below threshold {threshold}%",
                details={
                    "coverage_score": coverage_score,
                    "threshold": threshold,
                    "covered_muscles": list(covered),
                    "missing_muscles": list(missing),
                }
            )
        ```
    """

    pass


class MetricsValidationError(ValidationException):
    """Raised when metrics validation fails.

    This exception is raised when scoring metrics fail validation checks,
    such as invalid values or missing required fields.

    Example:
        ```python
        if not all_required_fields_present(metrics_data):
            raise MetricsValidationError(
                "Metrics validation failed: missing required fields",
                details={"missing_fields": missing_fields}
            )
        ```
    """

    pass


# =============================================================================
# Storage Exceptions
# =============================================================================

class StorageException(ScoringException):
    """Base exception for storage-related errors.

    This exception class represents failures in storage operations
    such as saving, loading, or persisting metrics data.

    Example:
        ```python
        try:
            save_metrics(metrics, path)
        except StorageException as e:
            logger.error(f"Storage error: {e}")
            # Handle storage failures
        ```
    """

    pass


class MetricsStorageError(StorageException):
    """Raised when metrics storage operation fails.

    This exception is raised when there's an error storing or retrieving
    scoring metrics from a persistent storage (file, database, etc.).

    Example:
        ```python
        try:
            with open(metrics_path, "w") as f:
                json.dump(metrics, f)
        except (IOError, json.JSONDecodeError) as e:
            raise MetricsStorageError(
                f"Failed to save metrics to {metrics_path}: {e}",
                details={"path": str(metrics_path)}
            ) from e
        ```
    """

    pass


# =============================================================================
# Utility Functions
# =============================================================================

def is_validation_error(exception: Exception) -> bool:
    """Check if exception is a validation-related error.

    This utility function helps with error handling by identifying
    validation exceptions vs other types of errors.

    Args:
        exception: The exception to check

    Returns:
        True if exception is a ValidationException or subclass

    Example:
        ```python
        try:
            validate(data)
        except ScoringException as e:
            if is_validation_error(e):
                logger.warning(f"Validation failed: {e}")
            else:
                logger.error(f"System error: {e}")
        ```
    """
    return isinstance(exception, ValidationException)


def is_storage_error(exception: Exception) -> bool:
    """Check if exception is a storage-related error.

    This utility function helps with error handling by identifying
    storage exceptions vs other types of errors.

    Args:
        exception: The exception to check

    Returns:
        True if exception is a StorageException or subclass

    Example:
        ```python
        try:
            save_metrics(metrics)
        except ScoringException as e:
            if is_storage_error(e):
                # Retry or use fallback storage
                logger.warning(f"Storage failed, using fallback: {e}")
            else:
                raise
        ```
    """
    return isinstance(exception, StorageException)
