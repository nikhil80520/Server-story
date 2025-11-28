# ===== app/routers/children.py =====
from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any

from app.models.auth.user import (
    ChildCreate,
    ChildUpdate,
    ChildResponse,
    ChildrenListResponse,
    ChildSelectRequest,
    ChildSystemPromptUpdate,
    ChildVoiceCloneSelectRequest,
    ChildReferenceImageLinkRequest,
    ChildProfilePictureUpload,
    ChildProfilePictureDelete,
)
from app.services.content.child_service import child_service
from app.dependencies import verify_firebase_token

router = APIRouter(prefix="/children", tags=["children"])


@router.post("", response_model=Dict[str, Any])
async def create_child(request: ChildCreate):
    """
    Create a new child profile for the authenticated parent
    
    Request body:
    {
        "firebase_token": "...",
        "name": "Emma",
        "age": 8,
        "interests": ["reading", "science", "animals"],
        "image_base64": "..." (optional),
        "avatar_seed": "..." (optional),
        "avatar_style": "avataaars" (optional),
        "system_prompt": "..." (optional)
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Create child profile
        child = await child_service.create_child(
            user_id=user_id,
            name=request.name,
            age=request.age,
            gender=request.gender,
            interests=request.interests,
            image_base64=request.image_base64,
            avatar_seed=request.avatar_seed,
            avatar_style=request.avatar_style,
            system_prompt=request.system_prompt
        )
        
        # Get child with stats
        child_response = await child_service.get_child_with_stats(user_id, child.child_id)
        
        return {
            "success": True,
            "message": "Child profile created successfully",
            "child": child_response.dict() if child_response else child.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create child: {str(e)}")


@router.get("", response_model=ChildrenListResponse)
async def get_children(
    firebase_token: str = None,
    authorization: str = Header(None)
):
    """
    Get all children for the authenticated parent
    
    Authentication:
    - Query param: ?firebase_token=...
    - Header: Authorization: Bearer <token>
    
    Returns:
    {
        "success": true,
        "children": [...],
        "default_child_id": "child_abc123",
        "total_count": 2
    }
    """
    try:
        # Extract token from header or query param
        token = firebase_token
        if not token and authorization:
            if authorization.startswith('Bearer '):
                token = authorization[7:]
            else:
                token = authorization
        
        if not token:
            raise HTTPException(status_code=401, detail="Firebase token required")
        
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(token)
        
        # Get all active children
        children = await child_service.get_all_children(user_id, include_inactive=False)
        
        # Get default child ID
        default_child_id = await child_service.get_default_child_id(user_id)
        
        # Get detailed info for each child
        children_responses = []
        for child in children:
            child_with_stats = await child_service.get_child_with_stats(user_id, child.child_id)
            if child_with_stats:
                children_responses.append(child_with_stats)
        
        return ChildrenListResponse(
            success=True,
            children=children_responses,
            default_child_id=default_child_id,
            total_count=len(children_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get children: {str(e)}")


@router.get("/default", response_model=Dict[str, Any])
async def get_default_child(firebase_token: str = None, authorization: str = Header(None)):
    """Get the default/selected child profile with statistics quickly."""
    try:
        token = firebase_token
        if not token and authorization:
            token = authorization[7:] if authorization.startswith('Bearer ') else authorization
        if not token:
            raise HTTPException(status_code=401, detail="Firebase token required")

        user_id = await verify_firebase_token(token)
        default_child_id = await child_service.get_default_child_id(user_id)
        if not default_child_id:
            return {"success": True, "child": None, "message": "No default child set"}
        child = await child_service.get_child_with_stats(user_id, default_child_id)
        if not child:
            raise HTTPException(status_code=404, detail="Default child profile not found")
        return {"success": True, "child": child.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get default child: {str(e)}")



@router.get("/stats", response_model=Dict[str, Any])
async def get_children_stats(firebase_token: str = None, authorization: str = Header(None)):
    """Get aggregated statistics across all active children for the authenticated parent.

    NOTE: Defined before dynamic /{child_id} route to avoid path shadowing.
    """
    try:
        token = firebase_token
        if not token and authorization:
            token = authorization[7:] if authorization.startswith('Bearer ') else authorization
        if not token:
            raise HTTPException(status_code=401, detail="Firebase token required")

        user_id = await verify_firebase_token(token)
        stats = await child_service.get_children_stats(user_id)
        return {"success": True, "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get children stats: {str(e)}")

@router.get("/{child_id}", response_model=Dict[str, Any])
async def get_child(child_id: str, firebase_token: str):
    """
    Get a specific child profile with statistics
    
    Path params:
    - child_id: The child's unique identifier
    
    Query params:
    - firebase_token: Firebase authentication token
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(firebase_token)
        
        # Get child with stats
        child = await child_service.get_child_with_stats(user_id, child_id)
        
        if not child:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        return {
            "success": True,
            "child": child.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get child: {str(e)}")


@router.put("/{child_id}", response_model=Dict[str, Any])
async def update_child(child_id: str, request: ChildUpdate):
    """
    Update a child profile
    
    Path params:
    - child_id: The child's unique identifier
    
    Request body:
    {
        "firebase_token": "...",
        "name": "Emma" (optional),
        "age": 9 (optional),
        "interests": ["reading", "math"] (optional),
        "image_base64": "..." (optional),
        "avatar_seed": "..." (optional),
        "avatar_style": "..." (optional),
        "system_prompt": "..." (optional)
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Update child profile
        updated_child = await child_service.update_child(
            user_id=user_id,
            child_id=child_id,
            name=request.name,
            age=request.age,
            gender=request.gender,
            interests=request.interests,
            image_base64=request.image_base64,
            avatar_seed=request.avatar_seed,
            avatar_style=request.avatar_style,
            system_prompt=request.system_prompt
        )
        
        if not updated_child:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        # Get updated child with stats
        child_response = await child_service.get_child_with_stats(user_id, child_id)
        
        return {
            "success": True,
            "message": "Child profile updated successfully",
            "child": child_response.dict() if child_response else updated_child.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update child: {str(e)}")


@router.patch("/{child_id}/system-prompt", response_model=Dict[str, Any])
async def update_child_system_prompt(child_id: str, request: ChildSystemPromptUpdate):
    """Update only the child's system prompt."""
    try:
        user_id = await verify_firebase_token(request.firebase_token)
        await child_service.set_child_system_prompt(user_id, child_id, request.system_prompt)
        child = await child_service.get_child_with_stats(user_id, child_id)
        return {"success": True, "message": "System prompt updated", "child": child.dict() if child else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update system prompt: {str(e)}")


@router.post("/{child_id}/voice-clone/select", response_model=Dict[str, Any])
async def select_child_voice_clone(child_id: str, request: ChildVoiceCloneSelectRequest):
    """Select/assign a voice clone for the child."""
    try:
        user_id = await verify_firebase_token(request.firebase_token)
        await child_service.set_child_voice_clone(user_id, child_id, request.voice_clone_id)
        child = await child_service.get_child_with_stats(user_id, child_id)
        return {"success": True, "message": "Voice clone selected", "child": child.dict() if child else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select voice clone: {str(e)}")


@router.post("/{child_id}/reference-images/link", response_model=Dict[str, Any])
async def link_reference_image_to_child(child_id: str, request: ChildReferenceImageLinkRequest):
    """Link an existing user-level reference image to the child."""
    try:
        user_id = await verify_firebase_token(request.firebase_token)
        await child_service.link_child_reference_image(user_id, child_id, request.reference_image_id)
        # Return updated counts
        child = await child_service.get_child_with_stats(user_id, child_id)
        return {"success": True, "message": "Reference image linked", "child": child.dict() if child else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to link reference image: {str(e)}")


@router.post("/{child_id}/profile-picture", response_model=Dict[str, Any])
async def upload_child_profile_picture(child_id: str, request: ChildProfilePictureUpload):
    """
    Upload or update a child's profile picture
    
    Path params:
    - child_id: The child's unique identifier
    
    Request body:
    {
        "firebase_token": "...",
        "image_base64": "base64_encoded_image_data"
    }
    
    Response:
    {
        "success": true,
        "message": "Profile picture uploaded successfully",
        "image_url": "https://storage.googleapis.com/...",
        "child_id": "child_abc123"
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Upload profile picture
        image_url = await child_service.upload_child_profile_picture(
            user_id=user_id,
            child_id=child_id,
            image_base64=request.image_base64
        )
        
        return {
            "success": True,
            "message": "Profile picture uploaded successfully",
            "image_url": image_url,
            "child_id": child_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload profile picture: {str(e)}")


@router.put("/{child_id}/profile-picture", response_model=Dict[str, Any])
async def update_child_profile_picture(child_id: str, request: ChildProfilePictureUpload):
    """
    Update a child's profile picture (alias for upload - replaces existing)
    
    Path params:
    - child_id: The child's unique identifier
    
    Request body:
    {
        "firebase_token": "...",
        "image_base64": "base64_encoded_image_data"
    }
    
    Response:
    {
        "success": true,
        "message": "Profile picture updated successfully",
        "image_url": "https://storage.googleapis.com/...",
        "child_id": "child_abc123"
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Upload/update profile picture (overwrites existing)
        image_url = await child_service.upload_child_profile_picture(
            user_id=user_id,
            child_id=child_id,
            image_base64=request.image_base64
        )
        
        return {
            "success": True,
            "message": "Profile picture updated successfully",
            "image_url": image_url,
            "child_id": child_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile picture: {str(e)}")


@router.get("/{child_id}/profile-picture", response_model=Dict[str, Any])
async def get_child_profile_picture(child_id: str, firebase_token: str = None, authorization: str = Header(None)):
    """
    Get a child's profile picture information
    
    Path params:
    - child_id: The child's unique identifier
    
    Query params or Headers:
    - firebase_token: Firebase authentication token (query param)
    - Authorization: Bearer token (header)
    
    Response:
    {
        "success": true,
        "child_id": "child_abc123",
        "image_url": "https://storage.googleapis.com/...",
        "has_profile_picture": true
    }
    """
    try:
        # Extract token from header or query param
        token = firebase_token
        if not token and authorization:
            if authorization.startswith('Bearer '):
                token = authorization[7:]
            else:
                token = authorization
        
        if not token:
            raise HTTPException(status_code=401, detail="Firebase token required")
        
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(token)
        
        # Get child profile
        child = await child_service.get_child(user_id, child_id)
        
        if not child:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        has_profile_picture = child.image_url is not None and child.image_url != ""
        
        return {
            "success": True,
            "child_id": child_id,
            "image_url": child.image_url if has_profile_picture else None,
            "has_profile_picture": has_profile_picture
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile picture: {str(e)}")


@router.delete("/{child_id}/profile-picture", response_model=Dict[str, Any])
async def delete_child_profile_picture(child_id: str, request: ChildProfilePictureDelete):
    """
    Delete a child's profile picture
    
    Path params:
    - child_id: The child's unique identifier
    
    Request body:
    {
        "firebase_token": "..."
    }
    
    Response:
    {
        "success": true,
        "message": "Profile picture deleted successfully",
        "child_id": "child_abc123"
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Delete profile picture
        success = await child_service.delete_child_profile_picture(
            user_id=user_id,
            child_id=child_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete profile picture")
        
        return {
            "success": True,
            "message": "Profile picture deleted successfully",
            "child_id": child_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile picture: {str(e)}")


@router.delete("/{child_id}", response_model=Dict[str, Any])
async def delete_child(child_id: str, firebase_token: str):
    """
    Soft delete a child profile
    
    Path params:
    - child_id: The child's unique identifier
    
    Query params:
    - firebase_token: Firebase authentication token
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(firebase_token)
        
        # Delete child profile (soft delete)
        success = await child_service.delete_child(user_id, child_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        return {
            "success": True,
            "message": "Child profile deleted successfully",
            "child_id": child_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete child: {str(e)}")


@router.post("/{child_id}/select", response_model=Dict[str, Any])
async def select_child(child_id: str, request: ChildSelectRequest):
    """
    Set a child as the default/selected child for the parent
    
    Path params:
    - child_id: The child's unique identifier
    
    Request body:
    {
        "firebase_token": "..."
    }
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Set as default child
        success = await child_service.set_default_child(user_id, child_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        return {
            "success": True,
            "message": f"Child selected successfully",
            "default_child_id": child_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to select child: {str(e)}")


@router.get("/{child_id}/stories", response_model=Dict[str, Any])
async def get_child_stories(child_id: str, firebase_token: str, limit: int = 20, offset: int = 0):
    """
    Get all stories for a specific child
    
    Path params:
    - child_id: The child's unique identifier
    
    Query params:
    - firebase_token: Firebase authentication token
    - limit: Maximum number of stories to return (default: 20)
    - offset: Number of stories to skip (default: 0)
    
    Note: This endpoint delegates to the stories router with child_id filter.
    For full implementation, see /stories endpoint with child_id query param.
    """
    try:
        # Verify Firebase token and get parent user ID
        user_id = await verify_firebase_token(firebase_token)
        
        # Verify child belongs to parent
        child = await child_service.get_child(user_id, child_id)
        if not child:
            raise HTTPException(status_code=404, detail="Child profile not found")
        
        # Import here to avoid circular dependency
        from app.services.storage.storage_service import StorageService
        storage_service = StorageService()
        
        # Get stories for this child
        stories = await storage_service.get_user_stories(
            user_id=user_id,
            limit=limit,
            offset=offset,
            child_id=child_id  # Filter by child
        )
        
        return {
            "success": True,
            "child_id": child_id,
            "child_name": child.name,
            "stories": stories.get('stories', []),
            "total_count": stories.get('total_count', 0),
            "has_more": stories.get('has_more', False)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get child stories: {str(e)}")


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for children service"""
    try:
        from app.utils.firebase_init import is_firebase_available
        
        return {
            "success": True,
            "service": "children_service",
            "firebase_available": is_firebase_available(),
            "status": "healthy"
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
