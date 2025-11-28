"""
Analytics Router
================
Client-facing endpoints for user analytics and metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.services.analytics.analytics_service import analytics_service
from app.models.analytics.analytics import AnalyticsResponse, UserMetrics, UserStatusBreakdown
from app.dependencies import get_current_user


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsResponse)
async def get_analytics_summary(
    include_time_series: bool = Query(False, description="Include time series data for charts"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get complete analytics summary
    
    Requires authentication. Returns comprehensive metrics including:
    - User metrics (total, active, paid, trial, etc.)
    - Revenue metrics (MRR, ARR, conversion rates)
    - Growth metrics (new users, churn, retention)
    - Status breakdown
    - Optional: Time series data for charts
    
    **Authentication Required**: Firebase ID token
    """
    try:
        analytics_data = await analytics_service.get_complete_analytics(
            include_time_series=include_time_series
        )
        
        return AnalyticsResponse(
            success=True,
            data=analytics_data,
            message="Analytics retrieved successfully"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )


@router.get("/metrics/users", response_model=UserMetrics)
async def get_user_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get basic user metrics only (faster endpoint)
    
    Returns:
    - Total users
    - Active users
    - Paid users
    - Trial users
    - Expired users
    - Disabled users
    - Cancelled users
    
    **Authentication Required**: Firebase ID token
    """
    try:
        metrics = await analytics_service.get_user_metrics_only()
        return metrics
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve user metrics: {str(e)}"
        )


@router.get("/metrics/status-breakdown", response_model=UserStatusBreakdown)
async def get_status_breakdown(
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed breakdown by account status (faster endpoint)
    
    Returns counts for each status:
    - trial_active
    - trial_expired
    - active_paid
    - grace_period
    - suspended_unpaid
    - cancelled
    - disabled_by_admin
    - deleted
    
    **Authentication Required**: Firebase ID token
    """
    try:
        breakdown = await analytics_service.get_status_breakdown_only()
        return breakdown
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve status breakdown: {str(e)}"
        )


@router.get("/health")
async def analytics_health():
    """
    Health check endpoint (no authentication required)
    """
    return {
        "status": "healthy",
        "service": "analytics",
        "endpoints": [
            "/analytics/summary",
            "/analytics/metrics/users",
            "/analytics/metrics/status-breakdown"
        ]
    }
