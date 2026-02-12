"""Scoring configuration management API endpoints.

This module provides admin-only endpoints for managing the movement scoring
configuration, including viewing current config, hot-reloading, and validation.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.exceptions import NotFoundError as DomainNotFoundError
from app.core.exceptions import ValidationError as DomainValidationError

from app.config.settings import get_settings
from app.ml.scoring.config_loader import (
    ConfigError,
    ConfigLoadError,
    ConfigNotFoundError,
    ConfigValidationError,
    get_config,
    get_config_loader,
)
from app.api.routes.dependencies import require_admin

router = APIRouter()
settings = get_settings()


# Response Schemas
class ConfigMetadataResponse(BaseModel):
    """Configuration metadata response."""

    version: str
    last_updated: str
    author: str
    description: str
    schema_version: str


class GlobalConfigResponse(BaseModel):
    """Global configuration settings response."""

    normalization_enabled: bool
    normalization_method: str
    tie_breaker_enabled: bool
    tie_breaker_strategy: str
    relaxation_enabled: bool
    relaxation_strategy: str
    debug_enabled: bool
    cache_scores: bool
    validate_on_load: bool
    strict_mode: bool


class ScoringDimensionSummary(BaseModel):
    """Summary of a scoring dimension."""

    name: str
    priority_level: int
    weight: float
    description: str


class ConfigResponse(BaseModel):
    """Complete configuration response."""

    metadata: ConfigMetadataResponse
    global_config: GlobalConfigResponse
    scoring_dimensions: list[ScoringDimensionSummary]


class ConfigReloadResponse(BaseModel):
    """Configuration reload response."""

    success: bool
    message: str
    config_version: str


class ConfigValidateRequest(BaseModel):
    """Request body for config validation."""

    check_schema: bool = True
    check_constraints: bool = True


class ConfigValidationErrorModel(BaseModel):
    """Single validation error."""

    field: str
    message: str


class ConfigValidateResponse(BaseModel):
    """Configuration validation response."""

    valid: bool
    message: str
    errors: list[ConfigValidationErrorModel] = []
    warnings: list[str] = []


class ConfigErrorResponse(BaseModel):
    """Error response for config operations."""

    error: str
    detail: str | None = None


# Endpoints
@router.get("/config", response_model=ConfigResponse)
async def get_scoring_config(admin: bool = Depends(require_admin)):
    """Get current scoring configuration.

    Returns the currently loaded movement scoring configuration,
    including metadata, global settings, and scoring dimensions.

    Args:
        admin: Admin authentication (injected by dependency)

    Returns:
        ConfigResponse: Current configuration

    Raises:
        HTTPException: If config cannot be loaded
    """
    try:
        config = get_config()
        loader = get_config_loader()

        # Build metadata response
        metadata = ConfigMetadataResponse(
            version=config.metadata.version,
            last_updated=config.metadata.last_updated,
            author=config.metadata.author,
            description=config.metadata.description,
            schema_version=config.metadata.schema_version,
        )

        # Build global config response
        global_config = GlobalConfigResponse(
            normalization_enabled=config.global_config.normalization_enabled,
            normalization_method=config.global_config.normalization_method,
            tie_breaker_enabled=config.global_config.tie_breaker_enabled,
            tie_breaker_strategy=config.global_config.tie_breaker_strategy,
            relaxation_enabled=config.global_config.relaxation_enabled,
            relaxation_strategy=config.global_config.relaxation_strategy,
            debug_enabled=config.global_config.debug_enabled,
            cache_scores=config.global_config.cache_scores,
            validate_on_load=config.global_config.validate_on_load,
            strict_mode=config.global_config.strict_mode,
        )

        # Build scoring dimensions summary
        scoring_dimensions = [
            ScoringDimensionSummary(
                name=name,
                priority_level=dimension.priority_level,
                weight=dimension.weight,
                description=dimension.description,
            )
            for name, dimension in config.scoring_dimensions.items()
        ]

        return ConfigResponse(
            metadata=metadata,
            global_config=global_config,
            scoring_dimensions=scoring_dimensions,
        )

    except ConfigLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration load error: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.post("/config/reload", response_model=ConfigReloadResponse)
async def reload_scoring_config(admin: bool = Depends(require_admin)):
    """Hot-reload scoring configuration from file.

    Triggers a reload of the scoring configuration from the YAML file.
    This allows configuration changes without restarting the application.

    Args:
        admin: Admin authentication (injected by dependency)

    Returns:
        ConfigReloadResponse: Reload status and new config version

    Raises:
        HTTPException: If reload fails
    """
    try:
        loader = get_config_loader()
        config = loader.reload_config()

        return ConfigReloadResponse(
            success=True,
            message="Configuration reloaded successfully",
            config_version=config.metadata.version,
        )

    except ConfigNotFoundError as e:
        raise DomainNotFoundError(
            "ScoringConfig",
            f"Configuration file not found: {e.path}",
            details={"path": e.path}
        )
    except ConfigLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to load configuration: {e.message}",
        )
    except ConfigValidationError as e:
        raise DomainValidationError(
            "scoring_config",
            f"Configuration validation failed: {e.message}",
            details={"message": e.message}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during reload: {str(e)}",
        )


@router.post("/config/validate", response_model=ConfigValidateResponse)
async def validate_scoring_config(
    request: ConfigValidateRequest,
    admin: bool = Depends(require_admin),
):
    """Validate scoring configuration schema and constraints.

    Validates the currently loaded configuration against the schema
    and constraint rules. Returns detailed validation errors if any.

    Args:
        request: Validation request options
        admin: Admin authentication (injected by dependency)

    Returns:
        ConfigValidateResponse: Validation results with errors and warnings
    """
    errors = []
    warnings = []

    try:
        loader = get_config_loader()
        config = loader.get_config()

        # Perform schema validation if requested
        if request.check_schema:
            try:
                loader.validate_schema(config)
            except ConfigValidationError as e:
                # Parse validation error to extract field-level errors
                error_msg = e.message
                if "scoring dimensions" in error_msg.lower():
                    errors.append(
                        ConfigValidationErrorModel(field="scoring_dimensions", message=error_msg)
                    )
                elif "pattern compatibility" in error_msg.lower():
                    errors.append(
                        ConfigValidationErrorModel(field="pattern_compatibility_matrix", message=error_msg)
                    )
                elif "goal profiles" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="goal_profiles", message=error_msg))
                elif "discipline modifiers" in error_msg.lower():
                    errors.append(
                        ConfigValidationErrorModel(field="discipline_modifiers", message=error_msg)
                    )
                elif "hard constraints" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="hard_constraints", message=error_msg))
                elif "rep/set ranges" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="rep_set_ranges", message=error_msg))
                elif "circuit config" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="circuit_config", message=error_msg))
                elif "global config" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="global_config", message=error_msg))
                elif "metadata" in error_msg.lower():
                    errors.append(ConfigValidationErrorModel(field="metadata", message=error_msg))
                else:
                    errors.append(ConfigValidationErrorModel(field="unknown", message=error_msg))

        # Check constraints if requested
        if request.check_constraints:
            # Check scoring dimensions constraints
            for name, dimension in config.scoring_dimensions.items():
                if dimension.priority_level < 1 or dimension.priority_level > 7:
                    errors.append(
                        ConfigValidationErrorModel(
                            field=f"scoring_dimensions.{name}.priority_level",
                            message=f"Priority level must be between 1 and 7, got {dimension.priority_level}",
                        )
                    )
                if dimension.weight < 0.0 or dimension.weight > 2.0:
                    warnings.append(
                        f"Weight for dimension '{name}' is outside typical range [0.0, 2.0]: {dimension.weight}"
                    )

            # Check hard constraints
            constraints = config.hard_constraints
            if constraints.max_time_per_session_minutes <= constraints.max_time_per_block_minutes:
                errors.append(
                    ConfigValidationErrorModel(
                        field="hard_constraints.time",
                        message="max_time_per_session_minutes must be greater than max_time_per_block_minutes",
                    )
                )

            # Check global config
            global_config = config.global_config
            if global_config.normalization_method not in ["min_max", "z_score", "rank"]:
                errors.append(
                    ConfigValidationErrorModel(
                        field="global_config.normalization_method",
                        message=f"Invalid normalization method: {global_config.normalization_method}",
                    )
                )

            # Check for warnings
            if global_config.debug_enabled:
                warnings.append("Debug mode is enabled - this may impact performance")

            if not global_config.cache_scores:
                warnings.append("Score caching is disabled - this may impact performance")

        # Determine overall validity
        is_valid = len(errors) == 0

        return ConfigValidateResponse(
            valid=is_valid,
            message="Configuration validation passed" if is_valid else "Configuration validation failed",
            errors=errors,
            warnings=warnings,
        )

    except ConfigLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration load error: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during validation: {str(e)}",
        )


@router.get("/config/metadata", response_model=ConfigMetadataResponse)
async def get_config_metadata(admin: bool = Depends(require_admin)):
    """Get configuration metadata only.

    Returns lightweight metadata about the current configuration
    without loading the full configuration structure.

    Args:
        admin: Admin authentication (injected by dependency)

    Returns:
        ConfigMetadataResponse: Configuration metadata

    Raises:
        HTTPException: If config cannot be loaded
    """
    try:
        config = get_config()

        return ConfigMetadataResponse(
            version=config.metadata.version,
            last_updated=config.metadata.last_updated,
            author=config.metadata.author,
            description=config.metadata.description,
            schema_version=config.metadata.schema_version,
        )

    except ConfigLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration load error: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


@router.get("/config/global", response_model=GlobalConfigResponse)
async def get_global_config(admin: bool = Depends(require_admin)):
    """Get global configuration settings only.

    Returns global settings that control scoring behavior,
    normalization, tie-breaking, and relaxation strategies.

    Args:
        admin: Admin authentication (injected by dependency)

    Returns:
        GlobalConfigResponse: Global configuration settings

    Raises:
        HTTPException: If config cannot be loaded
    """
    try:
        config = get_config()

        return GlobalConfigResponse(
            normalization_enabled=config.global_config.normalization_enabled,
            normalization_method=config.global_config.normalization_method,
            tie_breaker_enabled=config.global_config.tie_breaker_enabled,
            tie_breaker_strategy=config.global_config.tie_breaker_strategy,
            relaxation_enabled=config.global_config.relaxation_enabled,
            relaxation_strategy=config.global_config.relaxation_strategy,
            debug_enabled=config.global_config.debug_enabled,
            cache_scores=config.global_config.cache_scores,
            validate_on_load=config.global_config.validate_on_load,
            strict_mode=config.global_config.strict_mode,
        )

    except ConfigLoadError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configuration load error: {e.message}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )
