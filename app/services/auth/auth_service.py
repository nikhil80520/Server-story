# File: app/services/auth_service.py - REFACTORED VERSION
from typing import Dict, Any, Optional
from fastapi import HTTPException
from firebase_admin import auth
from app.models.auth.auth import AuthResponse
from app.models.auth.user import UserRegistration, UserProfileUpdate, User
from app.services.auth.user_service import UserService
from app.config import settings
import time


class AuthService:
    """Service for authentication and user token management."""
    
    def __init__(self):
        # Token verification cache (short TTL to balance security and performance)
        self._token_cache: Dict[str, Dict[str, any]] = {}
        self._token_cache_ttl = 60  # 1 minute cache for token verification
    
    async def verify_token(self, token: str) -> str:
        """
        Verify Firebase ID token and return user ID.
        WITH CACHING: 1-minute TTL to reduce Firebase Auth API calls.
        
        Args:
            token: Firebase ID token
            
        Returns:
            User ID (uid)
            
        Raises:
            HTTPException: If token is invalid
        """
        # Local debug bypass: only enable when both debug and explicit allow flag are set
        if getattr(settings, 'debug', False) and getattr(settings, 'allow_local_auth_bypass', False):
            print("⚠️ DEBUG + ALLOW_LOCAL_AUTH_BYPASS: bypassing Firebase token verification and returning debug-user")
            return "debug-user"

        # Check cache first
        if token in self._token_cache:
            cached_data = self._token_cache[token]
            cache_age = time.time() - cached_data['timestamp']
            if cache_age < self._token_cache_ttl:
                return cached_data['uid']
            else:
                del self._token_cache[token]

        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token.get('uid') or decoded_token.get('user_id') or decoded_token.get('sub')
            
            # Cache the result
            self._token_cache[token] = {
                'uid': uid,
                'timestamp': time.time()
            }
            
            # Clean old cache entries (simple cleanup - keep cache size manageable)
            if len(self._token_cache) > 1000:
                current_time = time.time()
                expired_tokens = [
                    t for t, data in self._token_cache.items()
                    if current_time - data['timestamp'] > self._token_cache_ttl
                ]
                for t in expired_tokens:
                    del self._token_cache[t]
            
            return uid
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {str(e)}")
    
    async def verify_token_and_get_user(self, token: str) -> User:
        """
        Verify Firebase token and return User object.
        
        Args:
            token: Firebase ID token
            
        Returns:
            User object with uid, email, name
            
        Raises:
            HTTPException: If token is invalid
        """
        # Local debug bypass
        if getattr(settings, 'debug', False) and getattr(settings, 'allow_local_auth_bypass', False):
            print("⚠️ DEBUG + ALLOW_LOCAL_AUTH_BYPASS: bypassing Firebase token verification and returning debug user")
            return User(
                uid='debug-user',
                email='debug@example.com',
                name='Debug User',
                token={}
            )

        try:
            decoded_token = auth.verify_id_token(token)
            return User(
                uid=decoded_token.get('uid') or decoded_token.get('user_id') or decoded_token.get('sub'),
                email=decoded_token.get('email'),
                name=decoded_token.get('name'),
                token=decoded_token
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {str(e)}")

class UserAuthService:
    """Service for user registration and profile management."""
    
    def __init__(self, user_service: UserService, auth_service: AuthService):
        self.user_service = user_service
        self.auth_service = auth_service
    
    async def register_user(self, request: UserRegistration) -> AuthResponse:
        """Register a new user with parent and child profiles"""
        try:
            # Verify Firebase token
            user_id = await self.auth_service.verify_token(request.firebase_token)
            print(f"✅ Firebase token verified - User ID: {user_id}")
            
            # Check if user already exists
            existing_profile = await self.user_service.get_user_profile(user_id)
            if existing_profile:
                print(f"✅ User {user_id} already has profile, returning existing data")
                return AuthResponse(
                    success=True,
                    message="User profile found. Welcome back!",
                    user_id=user_id,
                    profile=existing_profile
                )
            
            # Create user profile
            profile = await self.user_service.create_user_profile(
                user_id=user_id,
                parent=request.parent,
                child=request.child,
                system_prompt=request.system_prompt,
                child_image_base64=request.child_image_base64
            )
            
            return AuthResponse(
                success=True,
                message="User profile created successfully",
                user_id=user_id,
                profile=profile
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Registration error details: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    # ALSO FIX: Update other methods in AuthService that use verify_firebase_token

    async def get_user_profile(self, firebase_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            # Verify Firebase token
            user_id = await self.auth_service.verify_token(firebase_token)
            
            # Get user profile
            profile = await self.user_service.get_user_profile(user_id)
            
            if not profile:
                raise HTTPException(status_code=404, detail="User profile not found")
            
            return {
                "success": True,
                "user_id": user_id,
                "profile": profile
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

    async def update_user_profile(self, request: UserProfileUpdate) -> AuthResponse:
        """Update user profile information"""
        try:
            # Verify Firebase token
            user_id = await self.auth_service.verify_token(request.firebase_token)
            
            # Update user profile
            updated_profile = await self.user_service.update_user_profile(
                user_id=user_id,
                parent=request.parent,
                child=request.child,
                system_prompt=request.system_prompt,
                child_image_base64=request.child_image_base64
            )
            
            return AuthResponse(
                success=True,
                message="User profile updated successfully",
                user_id=user_id,
                profile=updated_profile
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Profile update failed: {str(e)}")

    async def verify_token_endpoint(self, firebase_token: str) -> Dict[str, Any]:
        """Verify Firebase token and return user info"""
        try:
            # Verify Firebase token
            user_id = await self.auth_service.verify_token(firebase_token)
            
            # Get user profile if exists
            profile = await self.user_service.get_user_profile(user_id)
            
            return {
                "success": True,
                "valid": True,
                "user_info": {
                    "uid": user_id,
                    "email": None,  # Token verification doesn't provide email
                    "email_verified": True  # Assume verified for simplicity
                },
                "has_profile": profile is not None,
                "profile": profile
            }
            
        except HTTPException as e:
            return {
                "success": False,
                "valid": False,
                "error": str(e.detail)
            }
        
    async def delete_user_profile(self, firebase_token: str) -> Dict[str, Any]:
        """Delete user profile and associated data"""
        try:
            # Verify Firebase token
            user_id = await self.auth_service.verify_token(firebase_token)
            
            # Delete user data
            await self.user_service.delete_user_data(user_id)
            
            return {
                "success": True,
                "message": "User profile and associated data deleted successfully",
                "user_id": user_id
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")


# Singleton instances
auth_service = AuthService()
user_auth_service = None  # Will be initialized after UserService is available


def get_user_auth_service() -> UserAuthService:
    """Get or create UserAuthService singleton."""
    global user_auth_service
    if user_auth_service is None:
        from app.services.auth.user_service import user_service
        user_auth_service = UserAuthService(user_service, auth_service)
    return user_auth_service
