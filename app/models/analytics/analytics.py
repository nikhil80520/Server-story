"""
Analytics Models
=================
Pydantic models for user analytics and metrics.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


class UserMetrics(BaseModel):
    """Core user metrics"""
    total_users: int = Field(..., description="Total number of users in the system")
    active_users: int = Field(..., description="Users with active status (trial_active or active_paid)")
    paid_users: int = Field(..., description="Users with active paid subscriptions")
    trial_users: int = Field(..., description="Users on active trial")
    expired_users: int = Field(..., description="Users with expired trials or subscriptions")
    disabled_users: int = Field(..., description="Users disabled by admin")
    cancelled_users: int = Field(..., description="Users who cancelled their subscription")


class RevenueMetrics(BaseModel):
    """Revenue-related metrics"""
    estimated_mrr: float = Field(..., description="Estimated Monthly Recurring Revenue (assuming $10/month)")
    estimated_arr: float = Field(..., description="Estimated Annual Recurring Revenue")
    paid_conversion_rate: float = Field(..., description="Percentage of users who converted to paid")
    trial_conversion_rate: float = Field(..., description="Percentage of trials that converted to paid")


class GrowthMetrics(BaseModel):
    """Growth and engagement metrics"""
    new_users_today: int = Field(..., description="Users created today")
    new_users_this_week: int = Field(..., description="Users created this week")
    new_users_this_month: int = Field(..., description="Users created this month")
    churn_rate: float = Field(..., description="Percentage of users who cancelled")
    retention_rate: float = Field(..., description="Percentage of users still active")


class UserStatusBreakdown(BaseModel):
    """Detailed breakdown by account status"""
    trial_active: int = 0
    trial_expired: int = 0
    active_paid: int = 0
    grace_period: int = 0
    suspended_unpaid: int = 0
    cancelled: int = 0
    disabled_by_admin: int = 0
    deleted: int = 0


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series"""
    date: str = Field(..., description="Date in ISO format")
    value: int = Field(..., description="Metric value for this date")


class TimeSeriesMetrics(BaseModel):
    """Time series data for charts"""
    user_growth: List[TimeSeriesDataPoint] = Field(default_factory=list, description="Daily user growth")
    paid_growth: List[TimeSeriesDataPoint] = Field(default_factory=list, description="Daily paid user growth")
    revenue_trend: List[TimeSeriesDataPoint] = Field(default_factory=list, description="Daily revenue trend")


class AnalyticsSummary(BaseModel):
    """Complete analytics summary"""
    timestamp: str = Field(..., description="When these metrics were calculated")
    user_metrics: UserMetrics
    revenue_metrics: RevenueMetrics
    growth_metrics: GrowthMetrics
    status_breakdown: UserStatusBreakdown
    time_series: Optional[TimeSeriesMetrics] = None


class AnalyticsResponse(BaseModel):
    """API response wrapper for analytics"""
    success: bool = True
    data: AnalyticsSummary
    message: str = "Analytics retrieved successfully"
