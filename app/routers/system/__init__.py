"""System routers."""
from .health import router as health_router
from .analytics import router as analytics_router
from .admin import router as admin_router

__all__ = ['health_router', 'analytics_router', 'admin_router']
