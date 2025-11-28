"""
Centralized dependency injection for FastAPI.
Separates authentication, authorization, and service dependencies.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from firebase_admin import firestore

from app.models.auth.user import User, AccountStatusInfo
from app.services.storage.storage_service import StorageService
from app.services.auth.account_status_service import account_status_service
from app.services.auth.auth_service import auth_service

# HTTP Bearer security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Singleton service instances
_storage_service_instance = None
_firestore_db_instance = None
_lullaby_service_instance = None


def get_storage_service() -> StorageService:
    """Get shared StorageService instance."""
    global _storage_service_instance
    if _storage_service_instance is None:
        _storage_service_instance = StorageService()
    return _storage_service_instance


async def get_current_user_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Extract and verify Firebase token from Authorization header.
    Returns User object with uid, email, name.
    Uses auth_service for token verification (with caching).
    """
    return await auth_service.verify_token_and_get_user(credentials.credentials)


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(optional_security)
) -> Optional[User]:
    """
    Optional authentication - returns None if no token provided.
    """
    if credentials is None:
        return None
    try:
        return await auth_service.verify_token_and_get_user(credentials.credentials)
    except Exception:
        return None


async def get_account_status(
    user: User = Depends(get_current_user_from_header)
) -> AccountStatusInfo:
    """
    Get account status for authenticated user.
    
    Returns:
        AccountStatusInfo with current account status
    """
    return await account_status_service.get_account_status(user.uid)


async def require_active_account(
    user: User = Depends(get_current_user_from_header),
    account_status: AccountStatusInfo = Depends(get_account_status)
) -> User:
    """
    Require active account (can access content).
    Raises HTTPException if account cannot access content.
    
    Returns:
        User object if account is active
    """
    error = account_status_service.get_http_error_for_status(account_status, "access_content")
    if error:
        raise error
    return user


async def require_story_creation_access(
    user: User = Depends(get_current_user_from_header),
    account_status: AccountStatusInfo = Depends(get_account_status)
) -> User:
    """
    Require story creation access (paid or trial).
    Raises HTTPException if account cannot create stories.
    
    Returns:
        User object if account can create stories
    """
    error = account_status_service.get_http_error_for_status(account_status, "create_story")
    if error:
        raise error
    return user


async def get_user_with_status(
    user: User = Depends(get_current_user_from_header),
    account_status: AccountStatusInfo = Depends(get_account_status)
) -> tuple[User, AccountStatusInfo]:
    """
    Get both user and account status (no validation).
    Use when you want status info but don't want to block access.
    
    Returns:
        Tuple of (User, AccountStatusInfo)
    """
    return user, account_status


def get_firestore_db() -> firestore.firestore.Client:
    """
    Get shared Firestore database instance.
    Returns the same Firestore client used throughout the app.
    """
    global _firestore_db_instance
    if _firestore_db_instance is None:
        _firestore_db_instance = firestore.client()
    return _firestore_db_instance


def get_lullaby_service(
    db: firestore.firestore.Client = Depends(get_firestore_db)
):
    """
    Get shared LullabyService instance.
    """
    global _lullaby_service_instance
    if _lullaby_service_instance is None:
        from openai import OpenAI
        from app.core.config import settings
        from app.services.content.lullaby_service import LullabyService
        
        openai_client = OpenAI(api_key=settings.openai_api_key)
        _lullaby_service_instance = LullabyService(openai_client, db)
    
    return _lullaby_service_instance


async def get_current_user(
    user: User = Depends(get_current_user_from_header)
) -> dict:
    """
    Get current user as dict (compatible with older code expecting dict format).
    Returns dict with uid, email, name.
    """
    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name
    }


async def require_admin(
    user: User = Depends(get_current_user_from_header),
    db: firestore.firestore.Client = Depends(get_firestore_db)
) -> dict:
    """
    Require admin role for the current user.
    Checks Firestore for admin status.
    
    Returns:
        User dict if admin
        
    Raises:
        HTTPException 403 if not admin
    """
    # Check admin status in Firestore users collection
    try:
        user_doc = db.collection("users").document(user.uid).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        user_data = user_doc.to_dict()
        is_admin = user_data.get("is_admin", False) or user_data.get("role") == "admin"
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return {
            "uid": user.uid,
            "email": user.email,
            "name": user.name,
            "is_admin": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error checking admin status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify admin status"
        )
