"""
Analytics Service
=================
Service for calculating and retrieving user analytics and metrics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

from app.models.analytics.analytics import (
    UserMetrics,
    RevenueMetrics,
    GrowthMetrics,
    UserStatusBreakdown,
    TimeSeriesDataPoint,
    TimeSeriesMetrics,
    AnalyticsSummary
)
from app.services.auth.user_service import UserService


class AnalyticsService:
    """Service for calculating user analytics and metrics"""
    
    def __init__(self):
        self.user_service = UserService()
        self.db = self.user_service.db
        # Estimated monthly price per user (can be configurable)
        self.monthly_price = 10.0
    
    async def get_complete_analytics(self, include_time_series: bool = False) -> AnalyticsSummary:
        """
        Get complete analytics summary
        
        Args:
            include_time_series: Whether to include time series data (more expensive query)
        
        Returns:
            AnalyticsSummary with all metrics
        """
        # Fetch all users
        users_ref = self.db.collection('users')
        users_docs = list(users_ref.stream())
        
        # Calculate metrics
        user_metrics = self._calculate_user_metrics(users_docs)
        revenue_metrics = self._calculate_revenue_metrics(users_docs, user_metrics)
        growth_metrics = self._calculate_growth_metrics(users_docs)
        status_breakdown = self._calculate_status_breakdown(users_docs)
        
        time_series = None
        if include_time_series:
            time_series = self._calculate_time_series(users_docs)
        
        return AnalyticsSummary(
            timestamp=datetime.utcnow().isoformat(),
            user_metrics=user_metrics,
            revenue_metrics=revenue_metrics,
            growth_metrics=growth_metrics,
            status_breakdown=status_breakdown,
            time_series=time_series
        )
    
    def _calculate_user_metrics(self, users_docs) -> UserMetrics:
        """Calculate core user metrics"""
        total_users = len(users_docs)
        active_users = 0
        paid_users = 0
        trial_users = 0
        expired_users = 0
        disabled_users = 0
        cancelled_users = 0
        
        for doc in users_docs:
            user_data = doc.to_dict()
            account_status = user_data.get('account_status', {})
            status = account_status.get('status', 'unknown')
            
            if status in ['trial_active', 'active_paid']:
                active_users += 1
            
            if status == 'active_paid':
                paid_users += 1
            
            if status == 'trial_active':
                trial_users += 1
            
            if status in ['trial_expired', 'suspended_unpaid']:
                expired_users += 1
            
            if status == 'disabled_by_admin':
                disabled_users += 1
            
            if status == 'cancelled':
                cancelled_users += 1
        
        return UserMetrics(
            total_users=total_users,
            active_users=active_users,
            paid_users=paid_users,
            trial_users=trial_users,
            expired_users=expired_users,
            disabled_users=disabled_users,
            cancelled_users=cancelled_users
        )
    
    def _calculate_revenue_metrics(self, users_docs, user_metrics: UserMetrics) -> RevenueMetrics:
        """Calculate revenue-related metrics"""
        paid_users = user_metrics.paid_users
        total_users = user_metrics.total_users
        trial_users = user_metrics.trial_users
        
        # MRR = number of paid users * monthly price
        estimated_mrr = paid_users * self.monthly_price
        estimated_arr = estimated_mrr * 12
        
        # Conversion rates
        paid_conversion_rate = (paid_users / total_users * 100) if total_users > 0 else 0.0
        
        # Trial conversion: paid users / (paid users + trial users + expired/cancelled)
        total_trial_users = trial_users + user_metrics.expired_users + user_metrics.cancelled_users
        trial_conversion_rate = (paid_users / (paid_users + total_trial_users) * 100) if (paid_users + total_trial_users) > 0 else 0.0
        
        return RevenueMetrics(
            estimated_mrr=round(estimated_mrr, 2),
            estimated_arr=round(estimated_arr, 2),
            paid_conversion_rate=round(paid_conversion_rate, 2),
            trial_conversion_rate=round(trial_conversion_rate, 2)
        )
    
    def _calculate_growth_metrics(self, users_docs) -> GrowthMetrics:
        """Calculate growth and engagement metrics"""
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        new_users_today = 0
        new_users_this_week = 0
        new_users_this_month = 0
        cancelled_count = 0
        active_count = 0
        
        for doc in users_docs:
            user_data = doc.to_dict()
            
            # Parse created_at
            created_at = user_data.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        # Firestore timestamp
                        created_date = created_at
                    
                    if created_date >= today_start:
                        new_users_today += 1
                    if created_date >= week_start:
                        new_users_this_week += 1
                    if created_date >= month_start:
                        new_users_this_month += 1
                except Exception:
                    pass
            
            # Count cancelled and active for churn/retention
            account_status = user_data.get('account_status', {})
            status = account_status.get('status', 'unknown')
            
            if status == 'cancelled':
                cancelled_count += 1
            if status in ['trial_active', 'active_paid']:
                active_count += 1
        
        total_users = len(users_docs)
        churn_rate = (cancelled_count / total_users * 100) if total_users > 0 else 0.0
        retention_rate = (active_count / total_users * 100) if total_users > 0 else 0.0
        
        return GrowthMetrics(
            new_users_today=new_users_today,
            new_users_this_week=new_users_this_week,
            new_users_this_month=new_users_this_month,
            churn_rate=round(churn_rate, 2),
            retention_rate=round(retention_rate, 2)
        )
    
    def _calculate_status_breakdown(self, users_docs) -> UserStatusBreakdown:
        """Calculate detailed breakdown by account status"""
        breakdown = UserStatusBreakdown()
        
        for doc in users_docs:
            user_data = doc.to_dict()
            account_status = user_data.get('account_status', {})
            status = account_status.get('status', 'unknown')
            
            if status == 'trial_active':
                breakdown.trial_active += 1
            elif status == 'trial_expired':
                breakdown.trial_expired += 1
            elif status == 'active_paid':
                breakdown.active_paid += 1
            elif status == 'grace_period':
                breakdown.grace_period += 1
            elif status == 'suspended_unpaid':
                breakdown.suspended_unpaid += 1
            elif status == 'cancelled':
                breakdown.cancelled += 1
            elif status == 'disabled_by_admin':
                breakdown.disabled_by_admin += 1
            elif status == 'deleted':
                breakdown.deleted += 1
        
        return breakdown
    
    def _calculate_time_series(self, users_docs, days: int = 30) -> TimeSeriesMetrics:
        """
        Calculate time series data for charts
        
        Args:
            users_docs: List of user documents
            days: Number of days to include in time series
        
        Returns:
            TimeSeriesMetrics with daily data points
        """
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Initialize daily counters
        daily_users = defaultdict(int)
        daily_paid = defaultdict(int)
        daily_revenue = defaultdict(float)
        
        for doc in users_docs:
            user_data = doc.to_dict()
            
            # Parse created_at
            created_at = user_data.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_date = created_at
                    
                    if created_date >= start_date:
                        date_key = created_date.strftime('%Y-%m-%d')
                        daily_users[date_key] += 1
                except Exception:
                    pass
            
            # Count paid users by their paid date
            account_status = user_data.get('account_status', {})
            status = account_status.get('status', 'unknown')
            
            if status == 'active_paid':
                # Use last_paid_date if available, otherwise created_at
                paid_date = account_status.get('last_paid_date') or created_at
                if paid_date:
                    try:
                        if isinstance(paid_date, str):
                            paid_datetime = datetime.fromisoformat(paid_date.replace('Z', '+00:00'))
                        else:
                            paid_datetime = paid_date
                        
                        if paid_datetime >= start_date:
                            date_key = paid_datetime.strftime('%Y-%m-%d')
                            daily_paid[date_key] += 1
                            daily_revenue[date_key] += self.monthly_price
                    except Exception:
                        pass
        
        # Create cumulative time series
        user_growth = []
        paid_growth = []
        revenue_trend = []
        
        cumulative_users = 0
        cumulative_paid = 0
        cumulative_revenue = 0.0
        
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            date_key = date.strftime('%Y-%m-%d')
            
            cumulative_users += daily_users.get(date_key, 0)
            cumulative_paid += daily_paid.get(date_key, 0)
            cumulative_revenue += daily_revenue.get(date_key, 0.0)
            
            user_growth.append(TimeSeriesDataPoint(
                date=date_key,
                value=cumulative_users
            ))
            paid_growth.append(TimeSeriesDataPoint(
                date=date_key,
                value=cumulative_paid
            ))
            revenue_trend.append(TimeSeriesDataPoint(
                date=date_key,
                value=int(cumulative_revenue)
            ))
        
        return TimeSeriesMetrics(
            user_growth=user_growth,
            paid_growth=paid_growth,
            revenue_trend=revenue_trend
        )
    
    async def get_user_metrics_only(self) -> UserMetrics:
        """Get just the basic user metrics (faster query)"""
        users_ref = self.db.collection('users')
        users_docs = list(users_ref.stream())
        return self._calculate_user_metrics(users_docs)
    
    async def get_status_breakdown_only(self) -> UserStatusBreakdown:
        """Get just the status breakdown (faster query)"""
        users_ref = self.db.collection('users')
        users_docs = list(users_ref.stream())
        return self._calculate_status_breakdown(users_docs)


# Global instance
analytics_service = AnalyticsService()
