# File: app/routers/auth.py - ENHANCED WITH FIREBASE AUTH ENDPOINTS
import httpx
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, EmailStr
from firebase_admin import auth
from app.models.auth.auth import (
    AuthResponse, 
    TokenVerificationRequest, 
    PasswordResetRequest,
    RefreshTokenRequest,
    ValidateOTPRequest,
    ResetPasswordWithOTPRequest,
    ChangePasswordRequest
)
from app.models.auth.user import UserRegistration, UserProfileUpdate
from app.services.auth.auth_service import AuthService, UserAuthService
from app.services.auth.user_service import UserService
from app.services.auth.email_service import email_service
from app.services.auth.password_reset_service import password_reset_service
from app.config import settings
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["authentication"])

# ===== NEW AUTHENTICATION MODELS =====

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class SignInRequest(BaseModel):
    email: EmailStr
    password: str

class AuthenticationResponse(BaseModel):
    success: bool
    message: str
    firebase_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    user_info: Optional[dict] = None

# ===== DEPENDENCY INJECTION =====

def get_user_service():
    return UserService()

def get_auth_service():
    return AuthService()

def get_user_auth_service(
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    return UserAuthService(user_service, auth_service)

def add_cors_headers(response: Response):
    """Add CORS headers to response"""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"

# ===== NEW FIREBASE AUTHENTICATION ENDPOINTS =====

@router.post("/signup", response_model=AuthenticationResponse)
async def sign_up_user(request: SignUpRequest, response: Response):
    """Create a new Firebase user account"""
    add_cors_headers(response)
    
    try:
        print(f"🔐 Creating new Firebase user: {request.email}")
        
        # Create user with Firebase Admin SDK
        user_record = auth.create_user(
            email=request.email,
            password=request.password,
            display_name=request.display_name,
            email_verified=False
        )
        
        print(f"✅ Firebase user created: {user_record.uid}")
        
        # Send welcome email
        try:
            await email_service.send_welcome_email(
                user_email=user_record.email,
                user_name=user_record.display_name
            )
            print(f"📧 Welcome email sent to {user_record.email}")
        except Exception as e:
            print(f"⚠️ Failed to send welcome email: {str(e)}")
        
        # Generate custom token for immediate sign-in
        custom_token = auth.create_custom_token(user_record.uid)
        
        # Exchange custom token for ID token using Firebase REST API
        firebase_token, refresh_token, expires_in = await exchange_custom_token_for_id_token(custom_token)
        
        return AuthenticationResponse(
            success=True,
            message="User account created successfully",
            firebase_token=firebase_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user_info={
                "uid": user_record.uid,
                "email": user_record.email,
                "display_name": user_record.display_name,
                "email_verified": user_record.email_verified,
                "created_at": user_record.user_metadata.creation_timestamp
            }
        )
        
    except auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    except auth.WeakPasswordError:
        raise HTTPException(status_code=400, detail="Password is too weak")
    except auth.InvalidEmailError:
        raise HTTPException(status_code=400, detail="Invalid email address")
    except Exception as e:
        print(f"❌ Sign-up error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create user account: {str(e)}")

@router.post("/signin", response_model=AuthenticationResponse)
async def sign_in_user(
    request: SignInRequest, 
    response: Response, 
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """Sign in an existing Firebase user"""
    add_cors_headers(response)
    
    try:
        print(f"🔐 Signing in Firebase user: {request.email}")
        
        # Use Firebase REST API to sign in (Admin SDK doesn't have direct sign-in)
        firebase_token, refresh_token, expires_in, user_info = await sign_in_with_email_password(
            request.email, 
            request.password
        )
        
        print(f"✅ User signed in successfully: {user_info.get('localId')}")
        
        # Get user profile from database using the user_id
        try:
            user_id = user_info.get('localId')
            user_profile = await user_service.get_user_profile(user_id)
            if user_profile:
                # Merge Firebase user info with database profile
                user_info['profile'] = user_profile
                print(f"📋 User profile loaded from database")
        except Exception as e:
            print(f"⚠️ Failed to load user profile: {str(e)}")
            # Continue with Firebase data only
        
        # Send login notification email
        try:
            await email_service.send_login_notification(
                user_email=request.email,
                user_name=user_info.get('displayName'),
                login_time=datetime.utcnow()
            )
            print(f"📧 Login notification sent to {request.email}")
        except Exception as e:
            print(f"⚠️ Failed to send login notification: {str(e)}")
        
        return AuthenticationResponse(
            success=True,
            message="User signed in successfully",
            firebase_token=firebase_token,
            refresh_token=refresh_token,
            expires_in=int(expires_in),
            user_info=user_info
        )
        
    except Exception as e:
        print(f"❌ Sign-in error: {str(e)}")
        error_message = str(e)
        
        # Handle specific Firebase errors
        if "INVALID_EMAIL" in error_message:
            raise HTTPException(status_code=400, detail="Invalid email address")
        elif "INVALID_PASSWORD" in error_message or "INVALID_LOGIN_CREDENTIALS" in error_message:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        elif "USER_DISABLED" in error_message:
            raise HTTPException(status_code=403, detail="User account has been disabled")
        elif "TOO_MANY_ATTEMPTS" in error_message:
            raise HTTPException(status_code=429, detail="Too many failed attempts. Please try again later")
        else:
            raise HTTPException(status_code=500, detail="Sign-in failed")

@router.post("/refresh-token")
async def refresh_firebase_token(request: RefreshTokenRequest, response: Response):
    """Refresh Firebase ID token using refresh token"""
    add_cors_headers(response)
    
    try:
        refresh_token = request.refresh_token
        if not refresh_token:
            raise HTTPException(status_code=400, detail="Refresh token is required")
        
        # Log a short prefix of the refresh token for debugging (do not log full token in prod)
        try:
            token_preview = refresh_token[:32]
        except Exception:
            token_preview = str(refresh_token)[:32]
        print(f"🔄 Refreshing Firebase token - token_preview={token_preview} (len={len(refresh_token)})")
        
        # Use Firebase REST API to refresh token
        new_firebase_token, new_refresh_token, expires_in = await refresh_firebase_id_token(refresh_token)
        
        print(f"✅ Token refreshed successfully for token preview: {token_preview}")
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "firebase_token": new_firebase_token,
            "refresh_token": new_refresh_token,
            "expires_in": int(expires_in)
        }
        
    except Exception as e:
        # Log full error and return Firebase's message to client so it can reauthenticate if needed
        err_str = str(e)
        print(f"❌ Token refresh error: {err_str}")
        
        # Check for common errors and provide helpful messages
        if "TOKEN_EXPIRED" in err_str.upper() or "INVALID_REFRESH_TOKEN" in err_str.upper():
            detail_msg = "Refresh token expired or invalid - please log in again"
        elif "USER_NOT_FOUND" in err_str.upper() or "USER_DISABLED" in err_str.upper():
            detail_msg = "User account not found or disabled - please contact support"
        elif err_str.strip() == "":
            detail_msg = "Token refresh failed - token may be expired or invalid, please log in again"
        else:
            detail_msg = err_str
        
        # If Firebase indicated token expiration, return that detail so client can re-login
        # Do not leak sensitive tokens - err_str here is an error message from Firebase endpoint
        raise HTTPException(status_code=401, detail=detail_msg)

@router.post("/password-reset")
async def request_password_reset(request: PasswordResetRequest, response: Response):
    """Send password reset email"""
    add_cors_headers(response)
    
    try:
        print(f"📧 Initiating password reset for: {request.email}")
        
        # Use our custom password reset service
        result = await password_reset_service.initiate_password_reset(request.email)
        
        return {
            "success": result["success"],
            "message": result["message"]
        }
        
    except Exception as e:
        print(f"❌ Password reset error: {str(e)}")
        # Don't reveal if email exists or not for security
        return {
            "success": True,
            "message": "If an account with this email exists, you will receive a 6-digit verification code."
        }

@router.post("/change-password")
async def change_user_password(request: ChangePasswordRequest, response: Response):
    """Change user password (requires authentication)"""
    add_cors_headers(response)
    
    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(request.firebase_token)
        user_id = decoded_token['uid']
        
        print(f"🔐 Changing password for user: {user_id}")
        
        # Update password using Firebase Admin SDK
        auth.update_user(user_id, password=request.new_password)
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
        
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    except auth.WeakPasswordError:
        raise HTTPException(status_code=400, detail="New password is too weak")
    except Exception as e:
        print(f"❌ Password change error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to change password")

@router.post("/validate-otp")
async def validate_reset_otp(request: ValidateOTPRequest, response: Response):
    """Validate a password reset OTP"""
    add_cors_headers(response)
    
    try:
        print(f"🔍 Validating reset OTP for: {request.email}")
        
        result = await password_reset_service.validate_otp(
            otp=request.otp,
            email=request.email
        )
        
        return {
            "success": result["valid"],
            "message": result["message"],
            "valid": result["valid"],
            "otp_verified": result["valid"],
            "next_step": "call_reset_password_endpoint" if result["valid"] else None,
            "email": request.email if result["valid"] else None
        }
        
    except Exception as e:
        print(f"❌ OTP validation error: {str(e)}")
        return {
            "success": False,
            "message": "Unable to validate verification code",
            "valid": False,
            "otp_verified": False
        }

@router.post("/reset-password")
async def reset_password_with_otp(request: ResetPasswordWithOTPRequest, response: Response):
    """Reset password using valid OTP"""
    add_cors_headers(response)
    
    try:
        print(f"🔐 Resetting password for: {request.email}")
        
        result = await password_reset_service.reset_password(
            otp=request.otp,
            email=request.email,
            new_password=request.new_password
        )
        
        return {
            "success": result["success"],
            "message": result["message"]
        }
        
    except Exception as e:
        print(f"❌ Password reset error: {str(e)}")
        return {
            "success": False,
            "message": "Unable to reset password. Please try again or request a new verification code."
        }

@router.post("/signout")
async def sign_out_user(request: TokenVerificationRequest, response: Response):
    """Sign out user (revoke refresh tokens)"""
    add_cors_headers(response)
    
    try:
        # Verify token and get user ID
        decoded_token = auth.verify_id_token(request.firebase_token)
        user_id = decoded_token['uid']
        
        print(f"👋 Signing out user: {user_id}")
        
        # Revoke all refresh tokens for this user
        auth.revoke_refresh_tokens(user_id)
        
        return {
            "success": True,
            "message": "User signed out successfully"
        }
        
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    except Exception as e:
        print(f"❌ Sign-out error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to sign out user")

# ===== FIREBASE REST API HELPER FUNCTIONS =====

async def sign_in_with_email_password(email: str, password: str):
    """Sign in user using Firebase REST API"""
    try:
        # You'll need to get your Firebase Web API Key from Firebase Console
        # For now, we'll get it from settings (you should add this to your .env)
        api_key = getattr(settings, 'firebase_web_api_key', None)
        
        if not api_key:
            raise Exception("Firebase Web API Key not configured. Add FIREBASE_WEB_API_KEY to your .env file")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(error_message)
            
            data = response.json()
            
            return (
                data['idToken'],
                data['refreshToken'], 
                data['expiresIn'],
                {
                    'localId': data['localId'],
                    'email': data['email'],
                    'displayName': data.get('displayName'),
                    'photoUrl': data.get('photoUrl'),
                    'emailVerified': data.get('emailVerified', False)
                }
            )
            
    except Exception as e:
        raise e

async def exchange_custom_token_for_id_token(custom_token: bytes):
    """Exchange custom token for ID token using Firebase REST API"""
    try:
        api_key = getattr(settings, 'firebase_web_api_key', None)
        
        if not api_key:
            raise Exception("Firebase Web API Key not configured")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={api_key}"
        
        payload = {
            "token": custom_token.decode('utf-8'),
            "returnSecureToken": True
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(error_data.get('error', {}).get('message', 'Token exchange failed'))
            
            data = response.json()
            
            return data['idToken'], data['refreshToken'], int(data['expiresIn'])
            
    except Exception as e:
        raise e

async def refresh_firebase_id_token(refresh_token: str):
    """Refresh ID token using refresh token"""
    try:
        api_key = getattr(settings, 'firebase_web_api_key', None)
        
        if not api_key:
            raise Exception("Firebase Web API Key not configured")
        
        url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)
            
            # Debug: log status and body when refresh fails to capture Firebase's error message
            if response.status_code != 200:
                try:
                    body_text = response.text
                except Exception:
                    body_text = '<unreadable response body>'
                print(f"❌ Firebase refresh API returned status={response.status_code} body={body_text}")
                
                # Try to extract error message from various formats
                err_msg = None
                try:
                    error_data = response.json()
                    # Firebase returns different shapes; try common locations
                    if isinstance(error_data, dict):
                        err_msg = (error_data.get('error', {}).get('error_description') or 
                                  error_data.get('error', {}).get('message') or 
                                  error_data.get('error_description') or 
                                  error_data.get('message'))
                        # If error is just a string
                        if not err_msg and 'error' in error_data:
                            error_val = error_data['error']
                            if isinstance(error_val, str):
                                err_msg = error_val
                except Exception as json_err:
                    print(f"⚠️ Could not parse error JSON: {json_err}")
                
                # Fallback to body text or generic message
                if not err_msg or err_msg.strip() == "":
                    if body_text and body_text.strip() != "":
                        err_msg = body_text[:500]  # Limit length
                    else:
                        err_msg = f"HTTP {response.status_code} - Token may be expired or invalid"
                
                raise Exception(f"Token refresh failed: {err_msg}")
            
            data = response.json()
            
            return data['id_token'], data['refresh_token'], int(data['expires_in'])
            
    except Exception as e:
        raise e

async def send_password_reset_email(email: str):
    """Send password reset email using Firebase REST API"""
    try:
        api_key = getattr(settings, 'firebase_web_api_key', None)
        
        if not api_key:
            raise Exception("Firebase Web API Key not configured")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
        
        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(error_data.get('error', {}).get('message', 'Failed to send reset email'))
            
            return True
            
    except Exception as e:
        raise e

# ===== EXISTING ENDPOINTS (KEEP ALL OF THESE) =====

@router.post("/register", response_model=AuthResponse)
async def register_user(request: UserRegistration, response: Response, user_auth_service: UserAuthService = Depends(get_user_auth_service)):
    """Register a new user with parent and child profiles"""
    add_cors_headers(response)
    return await user_auth_service.register_user(request)

@router.get("/profile/{firebase_token}")
async def get_user_profile_endpoint(firebase_token: str, response: Response, user_auth_service: UserAuthService = Depends(get_user_auth_service)):
    """Get user profile information"""
    add_cors_headers(response)
    return await user_auth_service.get_user_profile(firebase_token)

@router.put("/profile", response_model=AuthResponse)
async def update_user_profile_endpoint(request: UserProfileUpdate, response: Response, user_auth_service: UserAuthService = Depends(get_user_auth_service)):
    """Update user profile information"""
    add_cors_headers(response)
    return await user_auth_service.update_user_profile(request)

@router.delete("/profile/{firebase_token}")
async def delete_user_profile(firebase_token: str, response: Response, user_auth_service: UserAuthService = Depends(get_user_auth_service)):
    """Delete user profile and associated data"""
    add_cors_headers(response)
    return await user_auth_service.delete_user_profile(firebase_token)

@router.post("/verify-token")
async def verify_token_endpoint(
    token_request: TokenVerificationRequest,
    response: Response, 
    user_auth_service: UserAuthService = Depends(get_user_auth_service)
):
    """Verify Firebase token and return user info"""
    add_cors_headers(response)
    
    print(f"🔍 verify-token endpoint called")
    print(f"📝 Received token_request: {token_request}")
    print(f"📝 Token (first 20 chars): {token_request.firebase_token[:20] if token_request.firebase_token else 'None'}...")
    
    return await user_auth_service.verify_token_endpoint(token_request.firebase_token)

# ===== DEBUG ENDPOINTS (KEEP THESE) =====

@router.post("/test-simple")
async def test_simple_endpoint(response: Response):
    """Simple test endpoint to verify server is working"""
    add_cors_headers(response)
    return {"message": "Server is working", "timestamp": datetime.utcnow().isoformat()}

@router.post("/test-echo")
async def test_echo_endpoint(request: Request, response: Response):
    """Echo endpoint to test request body parsing"""
    add_cors_headers(response)
    
    body = await request.body()
    headers = dict(request.headers)
    
    return {
        "message": "Echo test",
        "method": request.method,
        "url": str(request.url),
        "headers": headers,
        "body_raw": body.decode('utf-8') if body else None,
        "body_length": len(body) if body else 0,
        "content_type": headers.get('content-type', 'Not set')
    }

# ===== OPTIONS HANDLERS =====

@router.options("/signup")
@router.options("/signin") 
@router.options("/refresh-token")
@router.options("/password-reset")
@router.options("/change-password")
@router.options("/signout")
@router.options("/register")
@router.options("/profile/{firebase_token}")
@router.options("/verify-token")
@router.options("/test-simple")
@router.options("/test-echo")
async def auth_options(response: Response):
    """Handle preflight OPTIONS requests for auth endpoints"""
    add_cors_headers(response)
    return {"message": "OK"}