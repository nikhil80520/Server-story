"""
Admin Router
============
Admin endpoints for managing user account statuses and system administration.

Authentication: HTTP Basic Auth
Username: root
Password: root

All endpoints require admin authentication.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import secrets
import os
from app.services.auth.account_status_service import account_status_service
from app.services.auth.user_service import UserService
from app.models.auth.user import AccountStatus

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()
user_service = UserService()


# ============================================================================
# Authentication
# ============================================================================

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Verify admin credentials (root/root)
    """
    correct_username = secrets.compare_digest(credentials.username, "root")
    correct_password = secrets.compare_digest(credentials.password, "root")
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(admin_username: str = Depends(verify_admin)):
    """
    Serve the admin dashboard HTML interface
    """
    # Use absolute path from project root
    import pathlib
    project_root = pathlib.Path(__file__).parent.parent.parent.parent
    html_path = project_root / "static" / "admin.html"
    
    try:
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin dashboard not found at {html_path}"
        )


@router.get("", response_class=HTMLResponse)
async def admin_dashboard_root(admin_username: str = Depends(verify_admin)):
    """Serve the dashboard for the `/admin` path (no trailing slash)."""
    # Reuse the same implementation as the trailing-slash route
    return await admin_dashboard(admin_username)


# ============================================================================
# Request Models
# ============================================================================

class UpdateAccountStatusRequest(BaseModel):
    user_id: str
    status: AccountStatus
    reason: Optional[str] = None
    subscription_end_date: Optional[str] = None

class MarkAsPaidRequest(BaseModel):
    user_id: str
    subscription_months: int = 1

class DisableAccountRequest(BaseModel):
    user_id: str
    reason: str

class EnableAccountRequest(BaseModel):
    user_id: str

class ExtendSubscriptionRequest(BaseModel):
    user_id: str
    days: int


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/status")
async def admin_status(admin: str = Depends(verify_admin)):
    """
    Check if admin authentication works
    """
    return {
        "status": "authenticated",
        "admin": admin,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/users")
async def list_all_users(
    limit: int = 100,
    offset: int = 0,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    List all users with their account statuses
    """
    try:
        db = user_service.db
        users_ref = db.collection('users').limit(limit).offset(offset)
        users_docs = users_ref.stream()
        
        users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            users.append({
                'user_id': doc.id,
                'email': user_data.get('email', 'N/A'),
                'account_status': user_data.get('account_status', {}),
                'created_at': user_data.get('created_at', 'N/A')
            })
        
        return {
            "total": len(users),
            "limit": limit,
            "offset": offset,
            "users": users
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific user
    """
    try:
        # Get user profile
        profile = await user_service.get_user_profile(user_id)
        
        # Get account status
        status = await account_status_service.get_account_status(user_id)
        
        return {
            "user_id": user_id,
            "profile": profile,
            "account_status": status.model_dump()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {str(e)}")


@router.post("/users/{user_id}/mark-paid")
async def mark_user_as_paid(
    user_id: str,
    request: MarkAsPaidRequest,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Mark a user account as paid/active
    
    This is useful for:
    - Manual subscription activation
    - Compensating users
    - Testing purposes
    """
    try:
        subscription_end = (datetime.utcnow() + timedelta(days=30 * request.subscription_months)).isoformat()
        
        status = await account_status_service.update_to_paid(
            user_id=user_id,
            subscription_end_date=subscription_end
        )
        
        return {
            "success": True,
            "message": f"User {user_id} marked as paid for {request.subscription_months} month(s)",
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark as paid: {str(e)}")


@router.post("/users/{user_id}/disable")
async def disable_user_account(
    user_id: str,
    request: DisableAccountRequest,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Disable a user account
    
    Reasons might include:
    - Policy violation
    - Spam
    - Abuse
    - Security concerns
    """
    try:
        status = await account_status_service.disable_by_admin(
            user_id=user_id,
            reason=request.reason
        )
        
        return {
            "success": True,
            "message": f"User {user_id} has been disabled",
            "reason": request.reason,
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disable account: {str(e)}")


@router.post("/users/{user_id}/enable")
async def enable_user_account(
    user_id: str,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Re-enable a disabled user account
    
    This will restore the account to trial_active status
    """
    try:
        # Re-initialize account status (trial_active)
        status = await account_status_service.initialize_account_status(user_id)
        
        return {
            "success": True,
            "message": f"User {user_id} has been re-enabled with trial status",
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable account: {str(e)}")


@router.post("/users/{user_id}/extend-subscription")
async def extend_subscription(
    user_id: str,
    request: ExtendSubscriptionRequest,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Extend a user's subscription by X days
    
    Useful for:
    - Compensating for service issues
    - Promotional extensions
    - Customer service
    """
    try:
        # Get current status
        current_status = await account_status_service.get_account_status(user_id)
        
        # Calculate new end date
        if current_status.subscription_end_date:
            current_end = datetime.fromisoformat(current_status.subscription_end_date.replace('Z', '+00:00'))
            new_end = current_end + timedelta(days=request.days)
        else:
            new_end = datetime.utcnow() + timedelta(days=request.days)
        
        # Update to paid with new end date
        status = await account_status_service.update_to_paid(
            user_id=user_id,
            subscription_end_date=new_end.isoformat()
        )
        
        return {
            "success": True,
            "message": f"Subscription extended by {request.days} days",
            "new_end_date": new_end.isoformat(),
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extend subscription: {str(e)}")


@router.post("/users/{user_id}/cancel-subscription")
async def cancel_user_subscription(
    user_id: str,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Cancel a user's subscription (admin initiated)
    """
    try:
        status = await account_status_service.cancel_subscription(user_id)
        
        return {
            "success": True,
            "message": f"Subscription cancelled for user {user_id}",
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")


@router.post("/users/{user_id}/reset-trial")
async def reset_trial(
    user_id: str,
    trial_days: int = 14,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Reset user to trial status with new trial period
    
    Useful for:
    - Customer service recovery
    - Testing
    - Special promotions
    """
    try:
        # Initialize with custom trial period
        trial_end = (datetime.utcnow() + timedelta(days=trial_days)).isoformat()
        
        # Get current status and update it
        status = await account_status_service.initialize_account_status(user_id)
        
        # Update trial end date
        from app.utils.firebase_init import get_firestore_client
        db = get_firestore_client()
        doc_ref = db.collection('users').document(user_id)
        doc_ref.set({
            'account_status': {
                **status.model_dump(),
                'trial_end_date': trial_end
            }
        }, merge=True)
        
        # Get updated status
        status = await account_status_service.get_account_status(user_id)
        
        return {
            "success": True,
            "message": f"Trial reset for {trial_days} days",
            "account_status": status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset trial: {str(e)}")


@router.get("/stats")
async def get_system_stats(admin: str = Depends(verify_admin)) -> Dict[str, Any]:
    """
    Get system-wide statistics about account statuses
    """
    try:
        db = user_service.db
        users_ref = db.collection('users')
        users_docs = users_ref.stream()
        
        stats = {
            'total_users': 0,
            'by_status': {
                'trial_active': 0,
                'trial_expired': 0,
                'active_paid': 0,
                'grace_period': 0,
                'suspended_unpaid': 0,
                'cancelled': 0,
                'disabled_by_admin': 0,
                'deleted': 0,
            }
        }
        
        for doc in users_docs:
            stats['total_users'] += 1
            user_data = doc.to_dict()
            account_status = user_data.get('account_status', {})
            status_value = account_status.get('status', 'trial_active')
            
            if status_value in stats['by_status']:
                stats['by_status'][status_value] += 1
        
        return {
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/users/{user_id}/update-status")
async def update_account_status(
    user_id: str,
    request: UpdateAccountStatusRequest,
    admin: str = Depends(verify_admin)
) -> Dict[str, Any]:
    """
    Manually update account status to any state
    
    This is a powerful endpoint that allows direct status manipulation.
    Use with caution!
    """
    try:
        from app.utils.firebase_init import get_firestore_client
        from app.models.auth.user import AccountStatusInfo
        
        db = get_firestore_client()
        doc_ref = db.collection('users').document(user_id)
        
        # Build status info based on target status
        status_info = {
            'status': request.status.value,
            'can_access_content': True,
            'can_create_stories': request.status in [
                AccountStatus.TRIAL_ACTIVE,
                AccountStatus.ACTIVE_PAID,
                AccountStatus.GRACE_PERIOD
            ],
            'requires_payment': request.status in [
                AccountStatus.TRIAL_EXPIRED,
                AccountStatus.GRACE_PERIOD,
                AccountStatus.SUSPENDED_UNPAID
            ]
        }
        
        if request.status == AccountStatus.TRIAL_ACTIVE:
            status_info['trial_end_date'] = (datetime.utcnow() + timedelta(days=14)).isoformat()
            status_info['message'] = "Trial active (admin set)"
            
        elif request.status == AccountStatus.ACTIVE_PAID:
            end_date = request.subscription_end_date or (datetime.utcnow() + timedelta(days=30)).isoformat()
            status_info['subscription_end_date'] = end_date
            status_info['last_payment_date'] = datetime.utcnow().isoformat()
            status_info['message'] = "Subscription active (admin set)"
            
        elif request.status == AccountStatus.DISABLED_BY_ADMIN:
            status_info['disabled_date'] = datetime.utcnow().isoformat()
            status_info['disabled_reason'] = request.reason or "Admin action"
            status_info['can_access_content'] = False
            status_info['can_create_stories'] = False
            status_info['message'] = f"Account disabled: {request.reason or 'Admin action'}"
        
        # Update Firestore
        doc_ref.set({
            'account_status': status_info,
            'updated_at': datetime.utcnow().isoformat()
        }, merge=True)
        
        # Get updated status
        updated_status = await account_status_service.get_account_status(user_id)
        
        return {
            "success": True,
            "message": f"Account status updated to {request.status.value}",
            "account_status": updated_status.model_dump(),
            "admin": admin,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")
