"""Lullaby generation endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
import uuid
from app.models.content.lullaby import (
    LullabyGenerateRequest,
    LullabyGenerateResponse,
    LullabyResponse,
    LullabyListResponse,
    LullabyDeleteResponse,
    LullabyMetadata
)
from app.models.auth.user import User
from app.services.content.lullaby_service import LullabyService
from app.services.auth.user_service import UserService
from app.core.dependencies import get_lullaby_service, get_current_user, require_active_account


def get_user_service():
    """Get UserService instance"""
    return UserService()


router = APIRouter(prefix="/lullabies", tags=["Lullabies"])


@router.post("/generate", response_model=LullabyGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_lullaby(
    request: LullabyGenerateRequest,
    current_user: User = Depends(require_active_account),
    lullaby_service: LullabyService = Depends(get_lullaby_service),
    user_service: UserService = Depends(get_user_service)
):
    """Start async lullaby generation with WebSocket notifications
    
    Requires an active account (trial or paid subscription).
    
    The lullaby generation process:
    1. Validates user and child profiles
    2. Creates initial lullaby metadata (status: processing)
    3. Starts background generation task
    4. Returns immediately with lullaby_id and WebSocket endpoint (HTTP 202)
    5. Sends progress updates via WebSocket (0% → 25% → 75% → 90% → 100%)
    6. Broadcasts completion event with audio URL
    
    If child_id is provided, the lyrics will be personalized with the child's:
    - Name (incorporated into the lullaby)
    - Age (appropriate themes and complexity)
    - Interests (referenced in the story/lyrics)
    
    Client should connect to WebSocket endpoint to receive:
    - lullaby_progress events (with progress percentage and status)
    - lullaby_completed event (with final audio URL)
    - lullaby_failed event (if generation fails)
    
    Args:
        request: Description of what the lullaby should be about (10-500 chars)
        
    Returns:
        LullabyGenerateResponse with initial metadata and WebSocket endpoint (HTTP 202)
        
    Raises:
        HTTPException: If validation fails or task cannot be started
    """
    import asyncio
    
    try:
        user_id = current_user.uid
        print(f"\n🔍 Verifying user profile for: {user_id}")
        
        # Verify user profile exists
        user_profile = await user_service.get_user_profile(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        print(f"✅ User profile verified: {user_profile.get('display_name', 'N/A')}")
        
        # Validate child if provided
        if request.child_id:
            from app.services.content.child_service import child_service
            child_profile = await child_service.get_child(user_id, request.child_id)
            if not child_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child profile not found: {request.child_id}"
                )
            print(f"✅ Child profile validated: {child_profile.name}")
        
        # Generate lullaby ID
        lullaby_id = f"lullaby_{uuid.uuid4().hex[:12]}"
        print(f"📋 Generated lullaby ID: {lullaby_id}")
        
        # Save initial metadata (status: processing)
        initial_metadata = {
            "lullaby_id": lullaby_id,
            "user_id": user_id,
            "child_id": request.child_id,
            "child_name": None,
            "description": request.description,
            "lyrics": "",
            "prompt": "soft, loving, lullaby, sleep music, gentle piano, calm",
            "audio_url": "",
            "duration_seconds": None,
            "status": "processing",
            "created_at": datetime.utcnow()
        }
        
        doc_ref = lullaby_service.db.collection('lullabies').document(lullaby_id)
        doc_ref.set(initial_metadata)
        print(f"💾 Initial metadata saved with status: processing")
        
        # WebSocket callbacks
        from app.services.infrastructure import lullaby_websocket_manager
        
        async def on_progress(data):
            """Send progress updates via WebSocket"""
            try:
                await lullaby_websocket_manager.broadcast_to_user(user_id, {
                    "event": "lullaby_progress",
                    "lullaby_id": lullaby_id,
                    "status": data.get("status"),
                    "progress": data.get("progress"),
                    "message": data.get("message"),
                    "lyrics": data.get("lyrics"),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"⚠️ Failed to send progress update: {e}")
        
        async def on_completion(data):
            """Send completion notification via WebSocket"""
            try:
                if data.get("status") == "completed":
                    # Serialize lullaby metadata to dict for JSON compatibility
                    lullaby_dict = data.get("lullaby")
                    if isinstance(lullaby_dict, dict):
                        # Convert datetime to string if present
                        if "created_at" in lullaby_dict and lullaby_dict["created_at"]:
                            lullaby_dict = lullaby_dict.copy()
                            lullaby_dict["created_at"] = lullaby_dict["created_at"].isoformat() if hasattr(lullaby_dict["created_at"], "isoformat") else str(lullaby_dict["created_at"])
                    
                    await lullaby_websocket_manager.broadcast_to_user(user_id, {
                        "event": "lullaby_completed",
                        "lullaby_id": lullaby_id,
                        "lullaby": lullaby_dict,
                        "message": "Your lullaby is ready!",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await lullaby_websocket_manager.broadcast_to_user(user_id, {
                        "event": "lullaby_failed",
                        "lullaby_id": lullaby_id,
                        "error": data.get("error"),
                        "message": f"Generation failed: {data.get('error')}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            except Exception as e:
                print(f"⚠️ Failed to send completion notification: {e}")
        
        # Start background task
        print(f"🚀 Starting background generation task")
        asyncio.create_task(
            lullaby_service.generate_lullaby_async(
                lullaby_id=lullaby_id,
                user_id=user_id,
                description=request.description,
                child_id=request.child_id,
                progress_callback=on_progress,
                completion_callback=on_completion
            )
        )
        
        return LullabyGenerateResponse(
            lullaby=LullabyMetadata(**initial_metadata),
            message="Lullaby generation started! Connect via WebSocket for real-time updates.",
            websocket_endpoint="/ws/lullabies"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to start lullaby generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {str(e)}"
        )


@router.get("/", response_model=LullabyListResponse)
async def get_user_lullabies(
    current_user: User = Depends(require_active_account),
    lullaby_service: LullabyService = Depends(get_lullaby_service)
):
    """Get all lullabies for the current user
    
    Requires an active account.
    
    Returns:
        List of all lullabies owned by the user, sorted by creation date (newest first)
    """
    try:
        user_id = current_user.uid
        
        lullabies = await lullaby_service.get_user_lullabies(user_id)
        
        return LullabyListResponse(
            lullabies=lullabies,
            total_count=len(lullabies),
            message=f"Retrieved {len(lullabies)} lullabies"
        )
        
    except Exception as e:
        print(f"❌ Failed to fetch lullabies: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lullabies: {str(e)}"
        )


@router.get("/{lullaby_id}", response_model=LullabyResponse)
async def get_lullaby(
    lullaby_id: str,
    current_user: User = Depends(require_active_account),
    lullaby_service: LullabyService = Depends(get_lullaby_service)
):
    """Get a specific lullaby by ID
    
    Requires an active account.
    
    Args:
        lullaby_id: The unique ID of the lullaby
        
    Returns:
        Lullaby metadata with audio URL
        
    Raises:
        HTTPException: If lullaby not found or not owned by user
    """
    try:
        user_id = current_user.uid
        
        lullaby = await lullaby_service.get_lullaby(lullaby_id, user_id)
        
        if not lullaby:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lullaby {lullaby_id} not found or you don't have access"
            )
        
        return LullabyResponse(
            lullaby=lullaby,
            message="Lullaby retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to fetch lullaby: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lullaby: {str(e)}"
        )


@router.delete("/{lullaby_id}", response_model=LullabyDeleteResponse)
async def delete_lullaby(
    lullaby_id: str,
    current_user: User = Depends(require_active_account),
    lullaby_service: LullabyService = Depends(get_lullaby_service)
):
    """Delete a lullaby
    
    Requires an active account.
    
    Deletes both the audio file from Firebase Storage and the metadata from Firestore.
    
    Args:
        lullaby_id: The unique ID of the lullaby to delete
        
    Returns:
        Confirmation message
        
    Raises:
        HTTPException: If lullaby not found or not owned by user
    """
    try:
        user_id = current_user.uid
        
        success = await lullaby_service.delete_lullaby(lullaby_id, user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lullaby {lullaby_id} not found or you don't have access"
            )
        
        return LullabyDeleteResponse(
            lullaby_id=lullaby_id,
            message="Lullaby deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to delete lullaby: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lullaby: {str(e)}"
        )
