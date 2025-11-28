"""
Push Notification Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DeviceToken(BaseModel):
    """Model for storing device push notification tokens"""
    user_id: str = Field(..., description="Firebase user ID")
    device_token: str = Field(..., description="Expo/FCM push token")
    platform: str = Field(..., description="Platform: ios or android")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationData(BaseModel):
    """Custom data payload for notifications"""
    type: str = Field(..., description="Notification type: new_story, story_shared, comment, promotion")
    story_id: Optional[str] = None
    action: Optional[str] = Field(None, description="Action: open_story, open_profile, open_settings")
    user_id: Optional[str] = None
    custom_field: Optional[Dict[str, Any]] = None


class NotificationFilter(BaseModel):
    """Filter for mass notifications"""
    all_users: bool = Field(default=False, description="Send to all users")
    user_ids: Optional[List[str]] = Field(default_factory=list, description="Specific user IDs")
    platforms: Optional[List[str]] = Field(default_factory=lambda: ["ios", "android"], description="Target platforms")


class MassNotificationRequest(BaseModel):
    """Request model for mass notifications"""
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[NotificationData] = None
    filter: NotificationFilter = Field(default_factory=NotificationFilter)


class IndividualNotificationRequest(BaseModel):
    """Request model for individual notifications"""
    user_id: str = Field(..., description="Target user ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[NotificationData] = None


class NotificationResponse(BaseModel):
    """Response model for notification operations"""
    success: bool
    message: str
    sent: Optional[int] = None
    failed: Optional[int] = None
    deleted: Optional[int] = None
