# ===== app/services/child_service.py =====
import base64
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from firebase_admin import firestore

from app.utils.firebase_init import get_firestore_client, is_firebase_available
from app.services.storage.storage_service import StorageService
from app.models.auth.user import Child, ChildCreate, ChildUpdate, ChildResponse
from app.config import settings


class ChildService:
    """Service for managing child profiles in parent-centric model"""
    
    def __init__(self):
        self._db = None
        self._storage_service = None
    
    @property
    def db(self):
        """Lazy initialization of Firestore client"""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db
    
    @property
    def storage_service(self):
        """Lazy initialization of Storage service"""
        if self._storage_service is None:
            self._storage_service = StorageService()
        return self._storage_service
    
    async def create_child(
        self,
        user_id: str,
        name: str,
        age: int,
        gender: Optional[str] = None,
        interests: List[str] = None,
        image_base64: Optional[str] = None,
        avatar_seed: Optional[str] = None,
        avatar_style: str = "avataaars",
        system_prompt: Optional[str] = None
    ) -> Child:
        """Create a new child profile for a parent"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Generate unique child ID
            child_id = f"child_{uuid.uuid4().hex[:12]}"
            
            # Handle image upload if provided
            image_url = None
            if image_base64:
                try:
                    image_data = base64.b64decode(image_base64)
                    image_url = await self.storage_service.upload_user_image(image_data, f"{user_id}/{child_id}")
                    print(f"✅ Child profile image uploaded: {image_url}")
                except Exception as e:
                    print(f"⚠️ Failed to upload child profile image: {str(e)}")
            
            # Generate personalized system prompt if not provided
            if not system_prompt:
                system_prompt = self._generate_personalized_prompt(name, age, interests)
            
            # Create child data
            child_data = {
                'child_id': child_id,
                'name': name,
                'age': age,
                'gender': gender,
                'interests': interests,
                'image_url': image_url,
                'avatar_seed': avatar_seed,
                'avatar_style': avatar_style,
                'avatar_url': None,
                'system_prompt': system_prompt,
                'is_active': True,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Save to Firestore in children sub-collection
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.set(child_data)
            
            # Update parent's children_count
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                children_count = user_data.get('children_count', 0) + 1
                default_child_id = user_data.get('default_child_id')
                
                # Set as default if this is the first child
                if children_count == 1:
                    default_child_id = child_id
                
                user_ref.update({
                    'children_count': children_count,
                    'default_child_id': default_child_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
            
            print(f"✅ Child profile created: {child_id} for parent {user_id}")
            
            return Child(**child_data)
            
        except Exception as e:
            print(f"❌ Failed to create child profile: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create child profile: {str(e)}")
    
    async def get_child(self, user_id: str, child_id: str) -> Optional[Child]:
        """Get a specific child profile"""
        try:
            if not is_firebase_available() or self.db is None:
                return None
            
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_doc = child_ref.get()
            
            if child_doc.exists and child_doc.to_dict().get('is_active', True):
                return Child(**child_doc.to_dict())
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting child profile: {str(e)}")
            return None
    
    async def get_all_children(self, user_id: str, include_inactive: bool = False) -> List[Child]:
        """Get all children for a parent"""
        try:
            if not is_firebase_available() or self.db is None:
                return []
            
            children_ref = self.db.collection('users').document(user_id).collection('children')
            
            # Query children - removed order_by to avoid composite index requirement
            # We'll sort in Python instead
            if not include_inactive:
                children_ref = children_ref.where('is_active', '==', True)
            
            children_docs = children_ref.stream()
            
            children = []
            for doc in children_docs:
                children.append(Child(**doc.to_dict()))
            
            # Sort by created_at in Python to avoid Firestore composite index
            children.sort(key=lambda c: c.created_at if c.created_at else datetime.min.isoformat())
            
            return children
            
        except Exception as e:
            print(f"❌ Error getting children: {str(e)}")
            return []
    
    async def get_default_child_id(self, user_id: str) -> Optional[str]:
        """Get the default/selected child ID for a parent"""
        try:
            if not is_firebase_available() or self.db is None:
                return None
            
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                return user_doc.to_dict().get('default_child_id')
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting default child ID: {str(e)}")
            return None
    
    async def update_child(
        self,
        user_id: str,
        child_id: str,
        name: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        interests: Optional[List[str]] = None,
        image_base64: Optional[str] = None,
        avatar_seed: Optional[str] = None,
        avatar_style: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Optional[Child]:
        """Update a child profile"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Get existing child data
            existing_child = await self.get_child(user_id, child_id)
            if not existing_child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
            # Prepare updates
            updates = {
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if name is not None:
                updates['name'] = name
            
            if age is not None:
                updates['age'] = age
            
            if gender is not None:
                updates['gender'] = gender
            
            if interests is not None:
                updates['interests'] = interests
            
            if avatar_seed is not None:
                updates['avatar_seed'] = avatar_seed
            
            if avatar_style is not None:
                updates['avatar_style'] = avatar_style
            
            if system_prompt is not None:
                updates['system_prompt'] = system_prompt
            
            # Handle image upload
            if image_base64:
                try:
                    image_data = base64.b64decode(image_base64)
                    image_url = await self.storage_service.upload_user_image(image_data, f"{user_id}/{child_id}")
                    updates['image_url'] = image_url
                    print(f"✅ Child profile image updated: {image_url}")
                except Exception as e:
                    print(f"⚠️ Failed to upload child profile image: {str(e)}")
            
            # Regenerate system prompt if child info changed and no explicit prompt provided
            if (name or age or interests) and system_prompt is None:
                final_name = name if name else existing_child.name
                final_age = age if age else existing_child.age
                final_interests = interests if interests else existing_child.interests
                updates['system_prompt'] = self._generate_personalized_prompt(final_name, final_age, final_interests)
            
            # Update in Firestore
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update(updates)
            
            print(f"✅ Child profile updated: {child_id}")
            
            # Return updated child
            return await self.get_child(user_id, child_id)
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to update child profile: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update child profile: {str(e)}")
    
    async def delete_child(self, user_id: str, child_id: str) -> bool:
        """Soft delete a child profile"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Verify child exists and is active
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
            # Soft delete by setting is_active to False
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Update parent's children_count and default_child_id if needed
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                children_count = max(0, user_data.get('children_count', 1) - 1)
                default_child_id = user_data.get('default_child_id')
                
                # If deleting the default child, find another active child
                if default_child_id == child_id:
                    active_children = await self.get_all_children(user_id, include_inactive=False)
                    default_child_id = active_children[0].child_id if active_children else None
                
                user_ref.update({
                    'children_count': children_count,
                    'default_child_id': default_child_id,
                    'updated_at': datetime.utcnow().isoformat()
                })
            
            print(f"✅ Child profile deleted (soft): {child_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to delete child profile: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete child profile: {str(e)}")
    
    async def set_default_child(self, user_id: str, child_id: str) -> bool:
        """Set a child as the default/selected child for a parent"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Verify child exists and is active
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found or inactive")
            
            # Update parent's default_child_id
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'default_child_id': child_id,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            print(f"✅ Default child set to: {child_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to set default child: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to set default child: {str(e)}")
    
    async def get_child_with_stats(self, user_id: str, child_id: str) -> Optional[ChildResponse]:
        """Get child profile with additional statistics"""
        try:
            child = await self.get_child(user_id, child_id)
            if not child:
                return None
            
            # Get story count for this child
            story_count = 0
            if is_firebase_available() and self.db:
                stories_ref = self.db.collection('stories')
                stories_query = stories_ref.where('user_id', '==', user_id).where('child_id', '==', child_id)
                story_count = len(list(stories_query.stream()))
            
            # Get voice clones count
            voice_clones_count = 0
            if is_firebase_available() and self.db:
                voice_clones_ref = self.db.collection('users').document(user_id).collection('children').document(child_id).collection('voice_clones')
                voice_clones_count = len(list(voice_clones_ref.stream()))
            
            # Get reference images count
            reference_images_count = 0
            if is_firebase_available() and self.db:
                ref_images_ref = self.db.collection('users').document(user_id).collection('children').document(child_id).collection('reference_images')
                reference_images_count = len(list(ref_images_ref.stream()))
            
            return ChildResponse(
                child_id=child.child_id,
                name=child.name,
                age=child.age,
                interests=child.interests,
                image_url=child.image_url,
                avatar_seed=child.avatar_seed,
                avatar_style=child.avatar_style,
                avatar_url=child.avatar_url,
                system_prompt=child.system_prompt,
                voice_clone_id=getattr(child, 'voice_clone_id', None),
                is_active=child.is_active,
                story_count=story_count,
                voice_clones_count=voice_clones_count,
                reference_images_count=reference_images_count,
                created_at=child.created_at,
                updated_at=child.updated_at
            )
            
        except Exception as e:
            print(f"❌ Error getting child with stats: {str(e)}")
            return None
    
    def _generate_personalized_prompt(self, name: str, age: int, interests: List[str]) -> str:
        """Generate a personalized system prompt based on child's profile"""
        interests_str = ", ".join(interests) if interests else "various topics"
        
        age_appropriate_language = {
            range(3, 6): "very simple words and short sentences",
            range(6, 9): "simple language with some new vocabulary",
            range(9, 13): "age-appropriate language with educational elements"
        }
        
        language_level = "simple, engaging language"
        for age_range, description in age_appropriate_language.items():
            if age in age_range:
                language_level = description
                break
        
        personalized_prompt = f"""You are a creative children's storyteller creating stories for {name}, who is {age} years old and loves {interests_str}.

Create engaging, age-appropriate stories that are educational and fun. Use {language_level} that's perfect for a {age}-year-old.

Incorporate themes and elements related to {interests_str} when possible, making {name} feel like the stories are made just for them.

Structure your story into clear scenes that can be visualized. Each scene should be 2-3 sentences long and paint a vivid picture.

Make the stories positive, encouraging, and help build {name}'s imagination and confidence."""

        return personalized_prompt

    # ===== New Extended Child Operations =====

    async def set_child_system_prompt(self, user_id: str, child_id: str, system_prompt: str) -> bool:
        """Explicitly set a child's system prompt (override personalization)."""
        try:
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update({
                'system_prompt': system_prompt,
                'updated_at': datetime.utcnow().isoformat()
            })
            print(f"✅ Updated system_prompt for child {child_id}")
            return True
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to set child system_prompt: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to set child system_prompt: {e}")

    async def set_child_voice_clone(self, user_id: str, child_id: str, voice_clone_id: str) -> bool:
        """Assign a voice_clone_id to the child (used for story generation)."""
        try:
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update({
                'voice_clone_id': voice_clone_id,
                'updated_at': datetime.utcnow().isoformat()
            })
            print(f"✅ Assigned voice_clone_id {voice_clone_id} to child {child_id}")
            return True
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to set child voice_clone_id: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to set child voice_clone_id: {e}")

    async def link_child_reference_image(self, user_id: str, child_id: str, reference_image_id: str) -> bool:
        """Link an existing user-level reference image to the child's reference_images subcollection."""
        try:
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")

            # Fetch reference image from user-level collection
            ref_doc = self.db.collection('users').document(user_id).collection('reference_images').document(reference_image_id).get()
            if not ref_doc.exists:
                raise HTTPException(status_code=404, detail="Reference image not found")
            ref_data = ref_doc.to_dict()

            # Copy minimal metadata into child's reference_images subcollection
            child_ref_collection = self.db.collection('users').document(user_id).collection('children').document(child_id).collection('reference_images')
            child_ref_collection.document(reference_image_id).set({
                'reference_image_id': reference_image_id,
                'image_url': ref_data.get('image_url'),
                'person_name': ref_data.get('person_name'),
                'relation': ref_data.get('relation'),
                'linked_at': datetime.utcnow().isoformat()
            })
            print(f"✅ Linked reference image {reference_image_id} to child {child_id}")
            return True
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to link reference image: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to link reference image: {e}")

    async def get_children_stats(self, user_id: str) -> Dict[str, Any]:
        """Aggregate statistics across all active children for dashboard usage."""
        try:
            children = await self.get_all_children(user_id, include_inactive=False)
            total_children = len(children)
            total_stories = 0
            age_distribution = {}
            interests_frequency = {}

            # For each child, gather story counts
            for child in children:
                try:
                    stories_ref = self.db.collection('stories').where('user_id', '==', user_id).where('child_id', '==', child.child_id)
                    count = len(list(stories_ref.stream()))
                    total_stories += count
                except Exception:
                    pass

                # Age distribution
                age_distribution[str(child.age)] = age_distribution.get(str(child.age), 0) + 1

                # Interests frequency
                for interest in child.interests:
                    interests_frequency[interest] = interests_frequency.get(interest, 0) + 1

            return {
                'total_children': total_children,
                'total_stories_across_children': total_stories,
                'average_stories_per_child': total_stories / total_children if total_children else 0,
                'age_distribution': age_distribution,
                'top_interests': sorted(interests_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
            }
        except Exception as e:
            print(f"❌ Failed to compute children stats: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to compute children stats: {e}")

    async def upload_child_profile_picture(self, user_id: str, child_id: str, image_base64: str) -> str:
        """Upload or update a child's profile picture"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Verify child exists and is active
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
            # Decode and upload image
            try:
                image_data = base64.b64decode(image_base64)
                
                # Validate image size (max 10MB)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(image_data) > max_size:
                    raise HTTPException(status_code=400, detail="Image size exceeds 10MB limit")
                
                # Upload to storage with child-specific path
                image_url = await self.storage_service.upload_user_image(image_data, f"{user_id}/children/{child_id}")
                print(f"✅ Child profile picture uploaded: {image_url}")
                
            except base64.binascii.Error:
                raise HTTPException(status_code=400, detail="Invalid base64 image data")
            except Exception as e:
                print(f"⚠️ Failed to upload child profile picture: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
            
            # Update child document with new image URL
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update({
                'image_url': image_url,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            print(f"✅ Child profile picture updated in database for {child_id}")
            return image_url
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to upload child profile picture: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to upload profile picture: {str(e)}")

    async def delete_child_profile_picture(self, user_id: str, child_id: str) -> bool:
        """Delete a child's profile picture"""
        try:
            if not is_firebase_available() or self.db is None:
                raise HTTPException(status_code=503, detail="Firebase service is not available")
            
            # Verify child exists and is active
            child = await self.get_child(user_id, child_id)
            if not child:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
            # Check if child has a profile picture
            if not child.image_url:
                raise HTTPException(status_code=404, detail="Child has no profile picture to delete")
            
            # Delete from storage if URL exists
            if child.image_url:
                try:
                    # Extract blob path from URL
                    # URL format: https://storage.googleapis.com/bucket-name/path/to/file
                    from urllib.parse import urlparse, unquote
                    parsed_url = urlparse(child.image_url)
                    
                    # Get path after bucket name
                    path_parts = parsed_url.path.split('/', 2)
                    if len(path_parts) >= 3:
                        blob_path = unquote(path_parts[2])
                        
                        # Delete from Firebase Storage
                        bucket = self.storage_service.bucket
                        if bucket:
                            blob = bucket.blob(blob_path)
                            if blob.exists():
                                blob.delete()
                                print(f"✅ Deleted profile picture from storage: {blob_path}")
                            else:
                                print(f"⚠️ Profile picture blob not found in storage: {blob_path}")
                except Exception as e:
                    print(f"⚠️ Failed to delete profile picture from storage: {str(e)}")
                    # Continue to remove URL from database even if storage deletion fails
            
            # Remove image URL from child document
            child_ref = self.db.collection('users').document(user_id).collection('children').document(child_id)
            child_ref.update({
                'image_url': None,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            print(f"✅ Child profile picture reference removed from database for {child_id}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Failed to delete child profile picture: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to delete profile picture: {str(e)}")


# Singleton instance
child_service = ChildService()
