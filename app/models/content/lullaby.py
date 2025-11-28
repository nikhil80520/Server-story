"""Lullaby models for music generation"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class LullabyGenerateRequest(BaseModel):
    """Request to generate a new lullaby"""
    description: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Description of what the lullaby should be about"
    )
    child_id: Optional[str] = Field(
        None,
        description="Optional child ID to personalize the lullaby with child's name and interests"
    )
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()


class LullabyMetadata(BaseModel):
    """Metadata for a generated lullaby"""
    lullaby_id: str = Field(..., description="Unique ID for the lullaby")
    user_id: str = Field(..., description="User who owns this lullaby")
    child_id: Optional[str] = Field(None, description="Child ID if lullaby was personalized for a specific child")
    child_name: Optional[str] = Field(None, description="Child's name if personalized")
    description: str = Field(..., description="Original description provided by user")
    lyrics: str = Field(..., description="Generated lyrics")
    prompt: str = Field(..., description="Music generation prompt used")
    audio_url: str = Field(..., description="Firebase Storage URL for the audio file")
    duration_seconds: Optional[float] = Field(None, description="Duration of the lullaby in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "lullaby_id": "lullaby_123abc",
                "user_id": "user_456def",
                "description": "A gentle lullaby about stars and dreams",
                "lyrics": "[Verse]\nIn the hush of night...",
                "prompt": "soft, loving, lullaby, sleep music",
                "audio_url": "https://firebasestorage.googleapis.com/...",
                "duration_seconds": 180.5,
                "created_at": "2025-11-27T12:00:00Z"
            }
        }


class LullabyResponse(BaseModel):
    """Response containing lullaby data"""
    lullaby: LullabyMetadata
    message: str = Field(default="Lullaby retrieved successfully")


class LullabyListResponse(BaseModel):
    """Response containing list of lullabies"""
    lullabies: List[LullabyMetadata]
    total_count: int
    message: str = Field(default="Lullabies retrieved successfully")


class LullabyGenerateResponse(BaseModel):
    """Response after generating a new lullaby"""
    lullaby: LullabyMetadata
    message: str = Field(default="Lullaby generated successfully")
    websocket_endpoint: Optional[str] = Field(default=None, description="WebSocket endpoint for real-time updates")


class LullabyDeleteResponse(BaseModel):
    """Response after deleting a lullaby"""
    lullaby_id: str
    message: str = Field(default="Lullaby deleted successfully")
