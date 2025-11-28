# File: app/models/auth.py - Add proper token verification model
from pydantic import BaseModel
from typing import Dict, Any, Optional

class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: str
    profile: Optional[Dict[str, Any]] = None

class TokenVerification(BaseModel):
    firebase_token: str

# NEW: Add this model for the verify-token endpoint
class TokenVerificationRequest(BaseModel):
    firebase_token: str

# Refresh Token Request Model
class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Password Reset Request Models (OTP-based)
class PasswordResetRequest(BaseModel):
    email: str

class ValidateOTPRequest(BaseModel):
    otp: str
    email: str

class ResetPasswordWithOTPRequest(BaseModel):
    otp: str
    email: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    firebase_token: str
    new_password: str