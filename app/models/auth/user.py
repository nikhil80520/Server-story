from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class AccountStatus(str, Enum):
    """Account status enum for subscription and payment states"""
    TRIAL_ACTIVE = "trial_active"  # On free trial, full access
    TRIAL_EXPIRED = "trial_expired"  # Trial ended, no payment yet
    ACTIVE_PAID = "active_paid"  # Fully paid & active
    PAYMENT_FAILED = "payment_failed"  # Payment method invalid
    GRACE_PERIOD = "grace_period"  # Payment failed but grace period active
    SUSPENDED_UNPAID = "suspended_unpaid"  # Account access limited due to unpaid status
    CANCELLED = "cancelled"  # Subscription canceled by user
    DISABLED_BY_ADMIN = "disabled_by_admin"  # Admin/team manually deactivated
    DELETED = "deleted"  # Data permanently deleted or queued for deletion

class AccountStatusInfo(BaseModel):
    """Detailed account status information"""
    status: AccountStatus
    trial_end_date: Optional[str] = None  # ISO 8601 datetime
    subscription_end_date: Optional[str] = None  # ISO 8601 datetime
    grace_period_end_date: Optional[str] = None  # ISO 8601 datetime
    payment_failed_date: Optional[str] = None  # ISO 8601 datetime
    last_payment_date: Optional[str] = None  # ISO 8601 datetime
    cancellation_date: Optional[str] = None  # ISO 8601 datetime
    disabled_date: Optional[str] = None  # ISO 8601 datetime
    disabled_reason: Optional[str] = None  # Reason for admin disable
    can_access_content: bool = True  # Whether user can access stories
    can_create_stories: bool = True  # Whether user can generate new stories
    requires_payment: bool = False  # Whether payment is required
    message: Optional[str] = None  # Human-readable status message
    action_required: Optional[str] = None  # What action user needs to take

class ChildProfile(BaseModel):
    name: str
    age: int
    interests: List[str]
    image_url: Optional[str] = None  # URL to child's profile image
    avatar_seed: Optional[str] = None  # Custom seed for avatar generation
    avatar_style: Optional[str] = "avataaars"  # Avatar style (avataaars, etc.)
    avatar_generated: Optional[bool] = False  # Whether avatar has been generated

# New models for multi-child support
class Child(BaseModel):
    """Full child model with ID (used for database storage)"""
    child_id: str
    name: str
    age: int
    gender: Optional[str] = None  # 'boy', 'girl', or None for unspecified
    interests: List[str]
    image_url: Optional[str] = None
    avatar_seed: Optional[str] = None
    avatar_style: Optional[str] = "avataaars"
    avatar_url: Optional[str] = None
    system_prompt: Optional[str] = None  # Child-specific system prompt
    voice_clone_id: Optional[str] = None  # Selected voice clone for this child
    is_active: bool = True  # For soft deletion
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ChildCreate(BaseModel):
    """Request model for creating a new child"""
    firebase_token: str
    name: str
    age: int
    gender: Optional[str] = None  # 'boy', 'girl', or None for unspecified
    interests: List[str]
    image_base64: Optional[str] = None  # Base64 encoded profile image
    avatar_seed: Optional[str] = None
    avatar_style: Optional[str] = "avataaars"
    system_prompt: Optional[str] = None

class ChildUpdate(BaseModel):
    """Request model for updating a child"""
    firebase_token: str
    name: Optional[str] = None
    gender: Optional[str] = None  # 'boy', 'girl', or None for unspecified
    age: Optional[int] = None
    interests: Optional[List[str]] = None
    image_base64: Optional[str] = None
    avatar_seed: Optional[str] = None
    avatar_style: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_clone_id: Optional[str] = None

class ChildResponse(BaseModel):
    """Response model for child data"""
    child_id: str
    name: str
    age: int
    interests: List[str]
    image_url: Optional[str] = None
    avatar_seed: Optional[str] = None
    avatar_style: Optional[str] = None
    avatar_url: Optional[str] = None
    system_prompt: Optional[str] = None
    voice_clone_id: Optional[str] = None
    is_active: bool
    story_count: Optional[int] = 0
    voice_clones_count: Optional[int] = 0
    reference_images_count: Optional[int] = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ChildrenListResponse(BaseModel):
    """Response for listing all children"""
    success: bool
    children: List[ChildResponse]
    default_child_id: Optional[str] = None
    total_count: int

class ChildSelectRequest(BaseModel):
    """Request to set a child as default/selected"""
    firebase_token: str

class ChildSystemPromptUpdate(BaseModel):
    """Request to update only the child's system prompt"""
    firebase_token: str
    system_prompt: str

class ChildVoiceCloneSelectRequest(BaseModel):
    """Request to assign/select a voice clone for a child"""
    firebase_token: str
    voice_clone_id: str

class ChildReferenceImageLinkRequest(BaseModel):
    """Request to link an existing reference image to a child"""
    firebase_token: str
    reference_image_id: str

class ChildProfilePictureUpload(BaseModel):
    """Request to upload a profile picture for a child"""
    firebase_token: str
    image_base64: str  # Base64 encoded image data

class ChildProfilePictureDelete(BaseModel):
    """Request to delete a child's profile picture"""
    firebase_token: str

class ParentProfile(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    avatar_seed: Optional[str] = None  # Custom seed for parent avatar
    avatar_style: Optional[str] = "avataaars"  # Avatar style
    avatar_generated: Optional[bool] = False  # Whether avatar has been generated

class UserRegistration(BaseModel):
    firebase_token: str
    parent: ParentProfile
    child: ChildProfile
    system_prompt: Optional[str] = None
    child_image_base64: Optional[str] = None  # Base64 encoded image data
    voice_audio_base64: Optional[str] = None  # Base64 encoded audio data for voice cloning (MP3)

class UserProfileUpdate(BaseModel):
    firebase_token: str
    parent: Optional[ParentProfile] = None
    child: Optional[ChildProfile] = None
    system_prompt: Optional[str] = None
    child_image_base64: Optional[str] = None  # Base64 encoded image data
    voice_audio_base64: Optional[str] = None  # Base64 encoded audio data for voice cloning (MP3)

class UserProfileResponse(BaseModel):
    user_id: str
    parent: ParentProfile
    child: ChildProfile
    system_prompt: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    story_count: Optional[int] = 0
    last_active: Optional[str] = None
    account_status: Optional[AccountStatusInfo] = None  # Account subscription/payment status

class AvatarUpdateRequest(BaseModel):
    firebase_token: str
    target: str  # "child" or "parent"
    avatar_seed: str
    avatar_style: Optional[str] = "avataaars"

# New models for unified avatar consistency system
class UserAvatarUpdate(BaseModel):
    avatar_style: str
    avatar_seed: str
    avatar_url: str

class UserAvatarResponse(BaseModel):
    success: bool
    message: str
    avatar_url: Optional[str] = None
    user_id: Optional[str] = None

# Voice Clone Models
class AudioCorruptionCheck(BaseModel):
    null_bytes: int = 0
    base64_length: int
    is_valid_base64: bool

class AudioData(BaseModel):
    base64: str
    format: str  # m4a, wav, mp3
    mime_type: str  # audio/mp4, audio/wav, audio/mpeg
    size_bytes: int
    duration_ms: Optional[int] = None
    sample_rate: Optional[int] = 44100
    channels: Optional[int] = 1
    platform: Optional[str] = None  # ios, android
    corruption_check: AudioCorruptionCheck

class VoiceCloneCreate(BaseModel):
    firebase_token: str
    voice_name: str
    description: str = "Custom voice clone"
    audio_data: AudioData

class VoiceCloneUpdate(BaseModel):
    firebase_token: str
    voice_clone_id: str  # Which voice clone to update
    voice_name: str
    description: str = "Updated voice clone"
    audio_data: AudioData

class VoiceCloneMetadata(BaseModel):
    voice_clone_id: str
    voice_id: str  # Cartesia voice ID
    voice_name: str
    description: Optional[str] = None
    is_active: bool = False  # Which voice is currently selected
    created_at: str
    updated_at: str

class VoiceCloneListResponse(BaseModel):
    user_id: str
    voice_clones: List[VoiceCloneMetadata]
    active_voice_clone_id: Optional[str] = None
    default_voice: Dict[str, Any]  # Default Cartesia voice info

class VoiceCloneSetActiveRequest(BaseModel):
    firebase_token: str
    voice_clone_id: str  # "default" or "vc_xxxxx"

class VoiceCloneDeleteRequest(BaseModel):
    firebase_token: str
    voice_clone_id: str

class VoiceCloneListRequest(BaseModel):
    firebase_token: str

class VoicePreviewRequest(BaseModel):
    firebase_token: str
    voice_clone_id: str  # "default" or "vc_xxxxx"
    preview_text: Optional[str] = None

class User(BaseModel):
    uid: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    token: Optional[Dict[str, Any]] = None