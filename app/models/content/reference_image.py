from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReferenceImageCreate(BaseModel):
    """Request model for creating a reference image"""
    firebase_token: str
    person_name: str
    relation: str  # e.g., "self", "parent", "sibling", "friend", "pet"
    age: Optional[int] = None  # Age of the person in the image (optional)
    image_base64: str  # Base64 encoded image
    
class ReferenceImageUpdate(BaseModel):
    """Request model for updating a reference image"""
    firebase_token: str
    person_name: Optional[str] = None
    relation: Optional[str] = None
    age: Optional[int] = None
    
class ReferenceImageResponse(BaseModel):
    """Response model for reference image"""
    reference_image_id: str
    user_id: str
    person_name: str
    relation: str
    age: Optional[int] = None  # Age of the person in the image
    image_url: str
    ai_description: Optional[str] = None  # AI-generated description of appearance and clothing
    created_at: datetime
    updated_at: datetime
    
class ReferenceImageListResponse(BaseModel):
    """Response model for listing reference images"""
    reference_images: list[ReferenceImageResponse]
    total: int
    max_allowed: int = 5
