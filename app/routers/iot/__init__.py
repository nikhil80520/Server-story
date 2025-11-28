"""IoT device routers."""
from .iot import router as iot_router
from .ntp import router as ntp_router

__all__ = ['iot_router', 'ntp_router']
