"""
Push Notifications Router
Endpoints for managing push notifications using Firestore
"""
from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from app.models.system.notification import (
    DeviceToken,
    MassNotificationRequest,
    IndividualNotificationRequest,
    NotificationResponse
)
from app.services.system.notification_service import NotificationService
from app.core.dependencies import get_current_user, get_firestore_db, require_admin
from typing import Dict

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(db: firestore.firestore.Client = Depends(get_firestore_db)) -> NotificationService:
    """Dependency to get notification service"""
    return NotificationService(db)


@router.post("/register", response_model=NotificationResponse)
async def register_device_token(
    token_data: DeviceToken,
    current_user: Dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Register a device token for push notifications
    
    - **user_id**: Firebase user ID (must match authenticated user)
    - **device_token**: Expo/FCM push token
    - **platform**: "ios" or "android"
    
    Returns success status
    """
    # Verify user can only register tokens for themselves
    if token_data.user_id != current_user.get("uid"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot register token for another user"
        )
    
    # Validate platform
    if token_data.platform not in ["ios", "android"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Platform must be 'ios' or 'android'"
        )
    
    success = await notification_service.register_device_token(
        user_id=token_data.user_id,
        device_token=token_data.device_token,
        platform=token_data.platform
    )
    
    if success:
        return NotificationResponse(
            success=True,
            message="Device token registered successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device token"
        )


@router.post("/send-mass", response_model=NotificationResponse)
async def send_mass_notification(
    request: MassNotificationRequest,
    current_user: Dict = Depends(require_admin),  # Admin only
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Send push notifications to all users or filtered groups (ADMIN ONLY)
    
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Custom data payload (optional)
    - **filter**: Filter criteria (all_users, user_ids, platforms)
    
    Returns number of notifications sent and failed
    """
    try:
        # Prepare data payload
        data_dict = request.data.dict() if request.data else {}
        
        # Send based on filter
        if request.filter.all_users:
            sent, failed = await notification_service.send_to_all(
                title=request.title,
                body=request.body,
                data=data_dict,
                platforms=request.filter.platforms
            )
        elif request.filter.user_ids:
            sent, failed = await notification_service.send_to_users(
                user_ids=request.filter.user_ids,
                title=request.title,
                body=request.body,
                data=data_dict
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify either all_users=true or provide user_ids"
            )
        
        return NotificationResponse(
            success=True,
            sent=sent,
            failed=failed,
            message=f"Notifications sent: {sent} successful, {failed} failed"
        )
        
    except Exception as e:
        print(f"❌ Mass notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notifications: {str(e)}"
        )


@router.post("/send", response_model=NotificationResponse)
async def send_individual_notification(
    request: IndividualNotificationRequest,
    current_user: Dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Send push notification to a specific user
    
    - **user_id**: Target user Firebase ID
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Custom data payload (optional)
    
    Returns number of notifications sent
    """
    try:
        # Prepare data payload
        data_dict = request.data.dict() if request.data else {}
        
        # Send notification
        sent, failed = await notification_service.send_to_user(
            user_id=request.user_id,
            title=request.title,
            body=request.body,
            data=data_dict
        )
        
        if sent == 0 and failed == 0:
            return NotificationResponse(
                success=False,
                sent=0,
                message="No devices registered for this user"
            )
        
        return NotificationResponse(
            success=True,
            sent=sent,
            failed=failed,
            message=f"Notification sent to {sent} device(s)"
        )
        
    except Exception as e:
        print(f"❌ Send notification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.delete("/cleanup", response_model=NotificationResponse)
async def cleanup_invalid_tokens(
    current_user: Dict = Depends(require_admin),  # Admin only
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Remove invalid/expired tokens from Firestore (ADMIN ONLY)
    
    This should be run periodically to clean up old tokens.
    
    Returns number of tokens deleted
    """
    try:
        deleted = await notification_service.cleanup_invalid_tokens()
        
        return NotificationResponse(
            success=True,
            deleted=deleted,
            message=f"Cleaned up {deleted} invalid tokens"
        )
        
    except Exception as e:
        print(f"❌ Token cleanup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup tokens: {str(e)}"
        )


@router.get("/test-token/{token}")
async def test_token_validity(
    token: str,
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Test if a token is a valid Expo push token (for debugging)
    """
    is_valid = notification_service.is_expo_push_token(token)
    
    return {
        "token": token,
        "is_valid": is_valid,
        "token_type": "expo" if token.startswith("ExponentPushToken[") else "fcm" if is_valid else "invalid"
    }
