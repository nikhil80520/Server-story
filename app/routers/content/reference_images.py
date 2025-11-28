from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import List
import base64
from datetime import datetime
from firebase_admin import firestore
import replicate
import os

from app.models.content.reference_image import (
    ReferenceImageCreate,
    ReferenceImageUpdate,
    ReferenceImageResponse,
    ReferenceImageListResponse
)
from app.dependencies import verify_firebase_token
from app.services.storage.storage_service import StorageService
from app.config import settings

router = APIRouter(prefix="/reference-images", tags=["reference-images"])

# Maximum reference images per user
MAX_REFERENCE_IMAGES = 5

# DEPRECATED: AI description generation removed in favor of relation-based defaults
# This function is kept for reference but is no longer used in the API
async def generate_ai_description(image_url: str) -> str:
    """
    Generate an AI description of the person's appearance and clothing using LLaVA model.
    
    Args:
        image_url: URL of the uploaded image
        
    Returns:
        AI-generated description of the main subject's appearance and clothing
    """
    try:
        # Check if Replicate API token is configured
        if not settings.replicate_api_token:
            print("⚠️ Replicate API token not configured - skipping AI description generation")
            return None
        
        # Set the API token for this request
        os.environ["REPLICATE_API_TOKEN"] = settings.replicate_api_token
        
        input_data = {
            "image": image_url,
            "prompt": "Describe the appearance and clothing of the main subject in this image. Focus on physical features, facial characteristics, hair, clothing style, and any distinctive features."
        }
        
        # Stream the response from LLaVA model
        description = ""
        for event in replicate.stream(
            "yorickvp/llava-13b:80537f9eead1a5bfa72d5ac6ea6414379be41d4d4f6679fd776e9535d1eb58bb",
            input=input_data
        ):
            description += str(event)
        
        return description.strip()
    except Exception as e:
        print(f"⚠️ Failed to generate AI description: {str(e)}")
        # Return None if description generation fails - don't block the upload
        return None

@router.post("/upload", response_model=ReferenceImageResponse)
async def upload_reference_image(
    file: UploadFile = File(...),
    person_name: str = Form(...),
    relation: str = Form(...),
    age: int = Form(None),
    firebase_token: str = Form(...)
):
    """Upload a reference image with file upload (max 5 per user)"""
    try:
        # Verify Firebase token
        user_id = await verify_firebase_token(firebase_token)
        
        # Validate file is an image
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Expected image, got {file.content_type}"
            )
        
        # Check current count
        db = firestore.client()
        ref_images_ref = db.collection('users').document(user_id).collection('reference_images')
        existing_count = len(list(ref_images_ref.stream()))
        
        if existing_count >= MAX_REFERENCE_IMAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_REFERENCE_IMAGES} reference images allowed. Please delete one before adding a new one."
            )
        
        # Read file data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) < 1024:
            raise HTTPException(status_code=400, detail="Image file too small (min 1KB)")
        
        if len(image_data) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        # Upload to Firebase Storage
        storage_service = StorageService()
        reference_image_id = f"ref_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        image_url = await storage_service.upload_image(
            image_data=image_data,
            filename=f"reference_images/{user_id}/{reference_image_id}.jpg",
            content_type="image/jpeg"
        )
        
        # Note: AI description generation removed - using relation-based defaults instead
        print(f"✅ Reference image uploaded: {reference_image_id}")
        
        # Save metadata to Firestore
        now = datetime.utcnow()
        ref_image_data = {
            'reference_image_id': reference_image_id,
            'user_id': user_id,
            'person_name': person_name,
            'relation': relation,
            'age': age,
            'image_url': image_url,
            'ai_description': None,  # Not generated - using relation-based defaults
            'created_at': now,
            'updated_at': now
        }
        
        ref_images_ref.document(reference_image_id).set(ref_image_data)
        
        return ReferenceImageResponse(**ref_image_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload reference image: {str(e)}")

@router.post("/create", response_model=ReferenceImageResponse)
async def create_reference_image(request: ReferenceImageCreate):
    """Create a new reference image for the user (max 5 per user)"""
    try:
        # Verify Firebase token
        user_id = await verify_firebase_token(request.firebase_token)
        
        # Check current count
        db = firestore.client()
        ref_images_ref = db.collection('users').document(user_id).collection('reference_images')
        existing_count = len(list(ref_images_ref.stream()))
        
        if existing_count >= MAX_REFERENCE_IMAGES:
            raise HTTPException(
                status_code=400, 
                detail=f"Maximum {MAX_REFERENCE_IMAGES} reference images allowed. Please delete one before adding a new one."
            )
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(request.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {str(e)}")
        
        # Upload to Firebase Storage
        storage_service = StorageService()
        reference_image_id = f"ref_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        image_url = await storage_service.upload_image(
            image_data=image_data,
            filename=f"reference_images/{user_id}/{reference_image_id}.jpg",
            content_type="image/jpeg"
        )
        
        # Note: AI description generation removed - using relation-based defaults instead
        print(f"✅ Reference image created: {reference_image_id}")
        
        # Save metadata to Firestore
        now = datetime.utcnow()
        ref_image_data = {
            'reference_image_id': reference_image_id,
            'user_id': user_id,
            'person_name': request.person_name,
            'relation': request.relation,
            'age': request.age,
            'image_url': image_url,
            'ai_description': None,  # Not generated - using relation-based defaults
            'created_at': now,
            'updated_at': now
        }
        
        ref_images_ref.document(reference_image_id).set(ref_image_data)
        
        return ReferenceImageResponse(**ref_image_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create reference image: {str(e)}")


@router.get("/list", response_model=ReferenceImageListResponse)
async def list_reference_images(firebase_token: str):
    """Get all reference images for the user"""
    try:
        user_id = await verify_firebase_token(firebase_token)
        
        db = firestore.client()
        ref_images_ref = db.collection('users').document(user_id).collection('reference_images')
        
        reference_images = []
        for doc in ref_images_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream():
            data = doc.to_dict()
            reference_images.append(ReferenceImageResponse(**data))
        
        return ReferenceImageListResponse(
            reference_images=reference_images,
            total=len(reference_images),
            max_allowed=MAX_REFERENCE_IMAGES
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reference images: {str(e)}")


@router.get("/{reference_image_id}", response_model=ReferenceImageResponse)
async def get_reference_image(reference_image_id: str, firebase_token: str):
    """Get a specific reference image"""
    try:
        user_id = await verify_firebase_token(firebase_token)
        
        db = firestore.client()
        ref_doc = db.collection('users').document(user_id).collection('reference_images').document(reference_image_id).get()
        
        if not ref_doc.exists:
            raise HTTPException(status_code=404, detail="Reference image not found")
        
        return ReferenceImageResponse(**ref_doc.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get reference image: {str(e)}")


@router.put("/{reference_image_id}", response_model=ReferenceImageResponse)
async def update_reference_image(reference_image_id: str, request: ReferenceImageUpdate):
    """Update reference image metadata (name and relation only)"""
    try:
        user_id = await verify_firebase_token(request.firebase_token)
        
        db = firestore.client()
        ref_doc_ref = db.collection('users').document(user_id).collection('reference_images').document(reference_image_id)
        ref_doc = ref_doc_ref.get()
        
        if not ref_doc.exists:
            raise HTTPException(status_code=404, detail="Reference image not found")
        
        # Update only provided fields
        update_data = {'updated_at': datetime.utcnow()}
        if request.person_name is not None:
            update_data['person_name'] = request.person_name
        if request.relation is not None:
            update_data['relation'] = request.relation
        if request.age is not None:
            update_data['age'] = request.age
        
        ref_doc_ref.update(update_data)
        
        # Get updated document
        updated_doc = ref_doc_ref.get()
        return ReferenceImageResponse(**updated_doc.to_dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update reference image: {str(e)}")


@router.delete("/{reference_image_id}")
async def delete_reference_image(reference_image_id: str, firebase_token: str):
    """Delete a reference image"""
    try:
        user_id = await verify_firebase_token(firebase_token)
        
        db = firestore.client()
        ref_doc_ref = db.collection('users').document(user_id).collection('reference_images').document(reference_image_id)
        ref_doc = ref_doc_ref.get()
        
        if not ref_doc.exists:
            raise HTTPException(status_code=404, detail="Reference image not found")
        
        # Delete from Firestore
        ref_doc_ref.delete()
        
        # Optionally delete from Firebase Storage (if you want to clean up storage)
        # storage_service = StorageService()
        # await storage_service.delete_file(f"reference_images/{user_id}/{reference_image_id}.jpg")
        
        return {
            "success": True,
            "message": "Reference image deleted successfully",
            "reference_image_id": reference_image_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete reference image: {str(e)}")
