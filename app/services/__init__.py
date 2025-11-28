"""
Services package - organized by functional area.

Structure:
- auth/: Authentication, user management, password reset, email services
- content/: Story generation, media creation, child management services
- storage/: Firebase storage service
- iot/: IoT device management, security, MQTT services
- ai/: AI services (Cartesia TTS)
- analytics/: Analytics and metrics services
- infrastructure/: Background tasks, websocket management
"""

# Re-export commonly used services for backward compatibility
from app.services.auth.auth_service import AuthService, auth_service
from app.services.auth.user_service import UserService, user_service
from app.services.auth.account_status_service import account_status_service
from app.services.content.child_service import ChildService, child_service
from app.services.storage.storage_service import StorageService, storage_service

__all__ = [
    'AuthService', 'auth_service',
    'UserService', 'user_service', 
    'account_status_service',
    'ChildService', 'child_service',
    'StorageService', 'storage_service'
]
