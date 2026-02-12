"""Scoring metrics API endpoints for admin monitoring and analysis.

This module provides admin-only endpoints for accessing scoring metrics,
including per-user metrics, aggregate summaries, success rates, and dimension
effectiveness analysis.

All endpoints require admin authentication via X-Admin-Token header.
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.exceptions import NotFoundError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.database import get_db
from app.models import User
from app.ml.scoring.scoring_metrics import (
    DimensionScores,
    ScoringMetrics,
    ScoringMetricsTracker,
)
from app.api.routes.dependencies import require_admin

router = APIRouter()
settings = get_settings()


# Response Schemas
class DimensionScoresResponse(BaseModel):
    """Response for dimension scores."""

    pattern_alignment: float
    muscle_coverage: float
    discipline_preference: float
    compound_bonus: float
    specialization: float
    goal_alignment: float
    time_utilization: float


class ScoringMetricsResponse(BaseModel):
    """Response for a single session's scoring metrics."""

    session_id: int
    session_type: str
    timestamp: datetime
    success: bool
    movement_count: int
    time_utilization: float
    pattern_diversity: int
    muscle_coverage: int
    dimension_scores: DimensionScoresResponse
    failure_reasons: list[str]
    structural_completeness: bool
    hard_constraints_compliant: bool


class UserMetricsSummaryResponse(BaseModel):
    """Response for user metrics summary."""

    user_id: int
    total_sessions: int
    successful_sessions: int
    success_rate: float
    by_session_type: dict[str, dict[str, int | float]]


class AggregateMetricsResponse(BaseModel):
    """Response for aggregate metrics across all users."""

    total_users: int
    total_sessions: int
    successful_sessions: int
    overall_success_rate: float
    by_session_type: dict[str, dict[str, int | float]]
    by_user: dict[int, UserMetricsSummaryResponse]


class SuccessRateResponse(BaseModel):
    """Response for success rate metrics."""

    success_rate: float
    total_sessions: int
    successful_sessions: int
    session_type_filter: str | None
    time_range: str


class DimensionEffectivenessResponse(BaseModel):
    """Response for dimension effectiveness analysis."""

    dimension_name: str
    mean: float
    median: float
    std: float
    min: float
    max: float
    sample_size: int


class DimensionEffectivenessSummaryResponse(BaseModel):
    """Response for all dimension effectiveness."""

    dimensions: dict[str, DimensionEffectivenessResponse]
    session_type_filter: str | None
    total_dimensions: int


class ErrorResponse(BaseModel):
    """Error response for API errors."""

    error: str
    detail: str | None = None


# Helper Functions
def _dimension_scores_to_response(scores: DimensionScores) -> DimensionScoresResponse:
    """Convert DimensionScores to response model.

    Args:
        scores: DimensionScores object

    Returns:
        DimensionScoresResponse instance
    """
    return DimensionScoresResponse(
        pattern_alignment=scores.pattern_alignment,
        muscle_coverage=scores.muscle_coverage,
        discipline_preference=scores.discipline_preference,
        compound_bonus=scores.compound_bonus,
        specialization=scores.specialization,
        goal_alignment=scores.goal_alignment,
        time_utilization=scores.time_utilization,
    )


def _metrics_to_response(metrics: ScoringMetrics) -> ScoringMetricsResponse:
    """Convert ScoringMetrics to response model.

    Args:
        metrics: ScoringMetrics object

    Returns:
        ScoringMetricsResponse instance
    """
    return ScoringMetricsResponse(
        session_id=metrics.session_id,
        session_type=metrics.session_type,
        timestamp=metrics.timestamp,
        success=metrics.success,
        movement_count=metrics.movement_count,
        time_utilization=metrics.time_utilization,
        pattern_diversity=metrics.pattern_diversity,
        muscle_coverage=metrics.muscle_coverage,
        dimension_scores=_dimension_scores_to_response(metrics.dimension_scores),
        failure_reasons=list(metrics.failure_reasons),
        structural_completeness=metrics.structural_completeness,
        hard_constraints_compliant=metrics.hard_constraints_compliant,
    )


# Endpoints
@router.get("/scoring/metrics/{user_id}", response_model=list[ScoringMetricsResponse])
async def get_user_scoring_metrics(
    user_id: int,
    admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    session_type: str | None = Query(
        None,
        description="Filter by session type (e.g., 'strength', 'cardio', 'conditioning')"
    ),
    limit: int | None = Query(
        None,
        ge=1,
        le=1000,
        description="Limit number of results (most recent)"
    ),
):
    """Get scoring metrics for a specific user.

    Retrieves all recorded scoring metrics for a user, with optional
    filtering by session type and result limiting.

    Args:
        user_id: ID of the user to fetch metrics for
        admin: Admin authentication (injected by dependency)
        db: Database session (injected by dependency)
        session_type: Optional filter by session type
        limit: Optional limit on number of results

    Returns:
        List of ScoringMetricsResponse objects

    Raises:
        HTTPException: If user not found or on database error
    """
    try:
        # Verify user exists
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", details={"user_id": user_id})

        # Initialize metrics tracker
        # In production, this would load from a persistent store per user
        tracker = ScoringMetricsTracker(metrics_path=None)

        # For MVP, we need to retrieve metrics from storage
        # This is a placeholder implementation - in production, you would
        # load user-specific metrics from a database or file storage
        # For now, return empty list as the tracker doesn't persist per-user data

        # TODO: Implement per-user metrics persistence
        # Example implementation would:
        # 1. Load metrics from database where user_id matches
        # 2. Convert to ScoringMetrics objects
        # 3. Apply filters and limits
        # 4. Return as response models

        return []
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving metrics for user {user_id}: {str(e)}"
        ) from e


@router.get("/scoring/metrics/summary", response_model=AggregateMetricsResponse)
async def get_aggregate_metrics(
    admin: bool = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregate scoring metrics across all users.

    Provides a comprehensive summary of scoring metrics aggregated
    across all users in the system, including overall success rates
    and breakdowns by session type and individual user.

    Args:
        admin: Admin authentication (injected by dependency)
        db: Database session (injected by dependency)

    Returns:
        AggregateMetricsResponse with summary statistics

    Raises:
        HTTPException: On database error
    """
    try:
        # Get total user count
        result = await db.execute(select(User.id))
        user_ids = [row[0] for row in result.fetchall()]
        total_users = len(user_ids)

        # Initialize metrics tracker
        tracker = ScoringMetricsTracker(metrics_path=None)

        # Get overall summary
        summary = tracker.get_metrics_summary()

        # Build per-user summaries
        by_user: dict[int, UserMetricsSummaryResponse] = {}
        for user_id in user_ids:
            # TODO: Load per-user metrics from database
            # For now, create empty summary
            by_user[user_id] = UserMetricsSummaryResponse(
                user_id=user_id,
                total_sessions=0,
                successful_sessions=0,
                success_rate=0.0,
                by_session_type={},
            )

        return AggregateMetricsResponse(
            total_users=total_users,
            total_sessions=summary["total_sessions"],
            successful_sessions=summary["successful_sessions"],
            overall_success_rate=summary["success_rate"],
            by_session_type=summary["by_session_type"],
            by_user=by_user,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving aggregate metrics: {str(e)}"
        ) from e


@router.get("/scoring/metrics/success-rate", response_model=SuccessRateResponse)
async def get_success_rate(
    admin: bool = Depends(require_admin),
    session_type: str | None = Query(
        None,
        description="Filter by session type (e.g., 'strength', 'cardio', 'conditioning')"
    ),
    limit: int | None = Query(
        None,
        ge=1,
        le=10000,
        description="Limit to most recent N sessions"
    ),
    time_range: str = Query(
        "all",
        description="Time range: 'all', 'today', 'week', 'month', 'year'"
    ),
):
    """Calculate success rate for generated sessions.

    Computes the success rate based on recorded metrics, with optional
    filtering by session type and time range. Success is defined as
    meeting all criteria: structural completeness, movement count,
    time utilization, and hard constraint compliance.

    Args:
        admin: Admin authentication (injected by dependency)
        session_type: Optional filter by session type
        limit: Optional limit on number of recent sessions
        time_range: Time range filter (default: 'all')

    Returns:
        SuccessRateResponse with success rate statistics

    Raises:
        HTTPException: On error calculating success rate
    """
    try:
        # Initialize metrics tracker
        tracker = ScoringMetricsTracker(metrics_path=None)

        # Calculate success rate
        success_rate = tracker.get_success_rate(
            session_type=session_type,
            limit=limit,
        )

        # Get summary for additional context
        summary = tracker.get_metrics_summary()

        # Apply session type filter if specified
        if session_type:
            type_summary = summary["by_session_type"].get(session_type, {})
            total_sessions = type_summary.get("total", 0)
            successful_sessions = type_summary.get("successful", 0)
        else:
            total_sessions = summary["total_sessions"]
            successful_sessions = summary["successful_sessions"]

        # TODO: Implement time_range filtering
        # This would require timestamp filtering in the tracker

        return SuccessRateResponse(
            success_rate=success_rate,
            total_sessions=total_sessions,
            successful_sessions=successful_sessions,
            session_type_filter=session_type,
            time_range=time_range,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating success rate: {str(e)}"
        ) from e


@router.get("/scoring/metrics/dimension-effectiveness", response_model=DimensionEffectivenessSummaryResponse)
async def get_dimension_effectiveness(
    admin: bool = Depends(require_admin),
    session_type: str | None = Query(
        None,
        description="Filter by session type (e.g., 'strength', 'cardio', 'conditioning')"
    ),
):
    """Analyze dimension effectiveness across sessions.

    Provides statistical analysis for each scoring dimension including
    mean, median, standard deviation, min, and max scores. This helps
    identify which dimensions are performing well and which may need
    adjustment in the scoring configuration.

    Args:
        admin: Admin authentication (injected by dependency)
        session_type: Optional filter by session type

    Returns:
        DimensionEffectivenessSummaryResponse with per-dimension statistics

    Raises:
        HTTPException: On error analyzing dimensions
    """
    try:
        # Initialize metrics tracker
        tracker = ScoringMetricsTracker(metrics_path=None)

        # Get dimension effectiveness
        effectiveness = tracker.get_dimension_effectiveness(session_type=session_type)

        # Convert to response format
        dimensions: dict[str, DimensionEffectivenessResponse] = {}
        for dim_name, stats in effectiveness.items():
            dimensions[dim_name] = DimensionEffectivenessResponse(
                dimension_name=dim_name,
                mean=stats["mean"],
                median=stats["median"],
                std=stats["std"],
                min=stats["min"],
                max=stats["max"],
                sample_size=stats["sample_size"],
            )

        return DimensionEffectivenessSummaryResponse(
            dimensions=dimensions,
            session_type_filter=session_type,
            total_dimensions=len(dimensions),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing dimension effectiveness: {str(e)}"
        ) from e
