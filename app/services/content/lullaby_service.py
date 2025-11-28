"""Lullaby generation service using OpenAI for lyrics and Replicate for music"""
import uuid
import asyncio
import tempfile
import os
import replicate
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from openai import OpenAI
from firebase_admin import firestore, storage
from app.models.content.lullaby import LullabyMetadata
from app.core.config import settings


class LullabyService:
    """Service for generating lullabies with AI-generated lyrics and music"""
    
    def __init__(self, openai_client: OpenAI, db: firestore.Client):
        self.openai_client = openai_client
        self.db = db
        
        # Initialize Replicate for music generation
        if settings.replicate_api_token:
            os.environ['REPLICATE_API_TOKEN'] = settings.replicate_api_token
            print("✅ LullabyService initialized with Replicate Music-1.5")
        else:
            print("⚠️ Replicate API token not configured - lullaby generation will fail")
    
    async def generate_lyrics(self, description: str, child_name: Optional[str] = None, child_age: Optional[int] = None, child_interests: Optional[List[str]] = None) -> str:
        """Generate lullaby lyrics using OpenAI based on user description
        
        Args:
            description: User's description of what the lullaby should be about
            child_name: Optional child's name for personalization
            child_age: Optional child's age for age-appropriate content
            child_interests: Optional child's interests for themed lyrics
            
        Returns:
            Formatted lyrics with [Verse], [Chorus], [Bridge], [Outro] tags (max 500 chars)
        """
        personalization_info = ""
        if child_name:
            personalization_info = f" (personalized for {child_name}"
            if child_age:
                personalization_info += f", age {child_age}"
            if child_interests:
                personalization_info += f", interests: {', '.join(child_interests[:3])}"
            personalization_info += ")"
        
        print(f"🎵 Generating lullaby lyrics for: {description}{personalization_info}")
        
        # Build personalization context
        personalization_context = ""
        if child_name:
            personalization_context = f"\n\nPERSONALIZATION:\n- Child's name: {child_name} (use their name naturally in the lyrics)"
            if child_age:
                personalization_context += f"\n- Age: {child_age} years old (adjust complexity accordingly)"
            if child_interests:
                interests_str = ", ".join(child_interests[:3])
                personalization_context += f"\n- Interests: {interests_str} (subtly incorporate these themes)"
        
        system_prompt = f"""You are a professional lullaby lyricist. Create gentle, soothing lullaby lyrics that help children (and adults) fall asleep.

CRITICAL REQUIREMENTS:
- Use [Verse], [Chorus], [Bridge], and [Outro] tags to structure the lyrics
- MAXIMUM 450 characters total (including tags and newlines) - THIS IS STRICT
- Keep it short and simple - quality over quantity
- Use simple, calming language with soft imagery
- Include themes of comfort, safety, dreams, and love
- Use gentle metaphors (stars, moonlight, clouds, gentle winds, etc.)
- Maintain a slow, peaceful rhythm suitable for sleep
- Avoid any scary, sad, or stimulating content{personalization_context}

Format example (under 450 characters):
[Verse]
In the hush of night, we find our space,
Wrapped in moonlight's gentle embrace.

[Chorus]
Just you and me, under starry sky,
In this moment, you and I.

[Bridge]
Your voice, a lullaby, soothes my soul,
In this night, we feel whole.

[Outro]
As dawn approaches, stars fade away,
In your arms, I wish to stay.

REMEMBER: Keep it under 450 characters total!"""

        user_prompt = f"Create a SHORT gentle lullaby (under 450 characters) about: {description}"
        
        try:
            # Run OpenAI call in executor to avoid blocking
            loop = asyncio.get_running_loop()
            
            def call_openai():
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=300  # Reduced to encourage shorter lyrics
                )
                return response.choices[0].message.content.strip()
            
            lyrics = await loop.run_in_executor(None, call_openai)
            
            # Strict validation - must be under 500 chars for MiniMax API
            if len(lyrics) > 500:
                print(f"⚠️ Lyrics too long ({len(lyrics)} chars), truncating to 500")
                # Find last complete section before 500 chars
                lyrics = lyrics[:500]
                # Try to end at last newline or space
                last_newline = lyrics.rfind('\n')
                if last_newline > 400:  # Only truncate at newline if reasonable
                    lyrics = lyrics[:last_newline]
            
            print(f"✅ Generated lyrics ({len(lyrics)} characters)")
            return lyrics
            
        except Exception as e:
            print(f"❌ Failed to generate lyrics: {str(e)}")
            raise Exception(f"Lyrics generation failed: {str(e)}")
    
    async def generate_music(self, lyrics: str, prompt: str = "soft, loving, lullaby, sleep music") -> bytes:
        """Generate music using Replicate's MiniMax Music-1.5 model
        
        Args:
            lyrics: The lyrics with structure tags
            prompt: Music style prompt (default: lullaby style)
            
        Returns:
            Audio file bytes (MP3 format)
        """
        print(f"🎼 Generating music with MiniMax Music-1.5")
        print(f"   Prompt: {prompt}")
        print(f"   Lyrics length: {len(lyrics)} characters")
        
        try:
            # Prepare input for Replicate
            input_params = {
                "lyrics": lyrics,
                "prompt": prompt,
                "audio_format": "mp3",
                "sample_rate": 44100,
                "bitrate": 256000
            }
            
            # Run Replicate in executor to avoid blocking
            loop = asyncio.get_running_loop()
            
            def call_replicate():
                output = replicate.run(
                    "minimax/music-1.5",
                    input=input_params
                )
                return output
            
            # Call with timeout (music generation can take 1-3 minutes)
            output = await asyncio.wait_for(
                loop.run_in_executor(None, call_replicate),
                timeout=300.0  # 5 minute timeout
            )
            
            print(f"✅ Music generation complete")
            
            # Output is a FileOutput object with .read() method
            # Download the audio data
            if hasattr(output, 'read'):
                audio_data = output.read()
            elif isinstance(output, (bytes, bytearray)):
                audio_data = bytes(output)
            elif isinstance(output, str) and output.startswith('http'):
                # If it's a URL, download it
                import httpx
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(output)
                    response.raise_for_status()
                    audio_data = response.content
            else:
                raise Exception(f"Unexpected output type from Replicate: {type(output)}")
            
            print(f"✅ Downloaded music: {len(audio_data)} bytes")
            return audio_data
            
        except asyncio.TimeoutError:
            print(f"❌ Music generation timed out after 300s")
            raise Exception("Music generation timed out - please try again")
        except Exception as e:
            print(f"❌ Music generation failed: {str(e)}")
            raise Exception(f"Music generation failed: {str(e)}")
    
    async def store_lullaby_audio(self, audio_data: bytes, lullaby_id: str, user_id: str) -> str:
        """Store lullaby audio to Firebase Storage
        
        Args:
            audio_data: MP3 audio bytes
            lullaby_id: Unique lullaby ID
            user_id: User ID who owns the lullaby
            
        Returns:
            Public Firebase Storage URL
        """
        try:
            bucket = storage.bucket()
            blob_path = f"lullabies/{user_id}/{lullaby_id}.mp3"
            blob = bucket.blob(blob_path)
            
            print(f"☁️ Uploading lullaby to Firebase: {blob_path}")
            
            # Upload with public access
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: blob.upload_from_string(
                    audio_data,
                    content_type='audio/mpeg'
                )
            )
            
            # Make publicly accessible
            await loop.run_in_executor(None, lambda: blob.make_public())
            
            public_url = blob.public_url
            print(f"✅ Lullaby uploaded: {public_url}")
            
            return public_url
            
        except Exception as e:
            print(f"❌ Failed to upload lullaby: {str(e)}")
            raise Exception(f"Failed to upload lullaby: {str(e)}")
    
    async def save_lullaby_metadata(self, metadata: LullabyMetadata) -> None:
        """Save lullaby metadata to Firestore
        
        Args:
            metadata: Lullaby metadata to save
        """
        try:
            doc_ref = self.db.collection('lullabies').document(metadata.lullaby_id)
            
            # Convert to dict
            data = metadata.model_dump()
            data['created_at'] = metadata.created_at
            
            # Save to Firestore
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: doc_ref.set(data))
            
            print(f"✅ Lullaby metadata saved: {metadata.lullaby_id}")
            
        except Exception as e:
            print(f"❌ Failed to save lullaby metadata: {str(e)}")
            raise Exception(f"Failed to save metadata: {str(e)}")
    
    async def generate_lullaby(self, user_id: str, description: str, child_id: Optional[str] = None) -> LullabyMetadata:
        """Complete lullaby generation pipeline
        
        Args:
            user_id: User ID requesting the lullaby
            description: Description of what the lullaby should be about
            child_id: Optional child ID for personalization
            
        Returns:
            LullabyMetadata with all generated content
        """
        print(f"\n{'='*80}")
        print(f"🎵 LULLABY GENERATION STARTED")
        print(f"User: {user_id}")
        print(f"Description: {description}")
        if child_id:
            print(f"Child ID: {child_id} (personalizing lyrics)")
        print(f"{'='*80}\n")
        
        try:
            # Get child profile if child_id provided
            child_name = None
            child_age = None
            child_interests = None
            
            if child_id:
                try:
                    from app.services.content.child_service import child_service
                    child_profile = await child_service.get_child(user_id, child_id)
                    
                    if child_profile:
                        child_name = child_profile.name
                        child_age = child_profile.age
                        child_interests = child_profile.interests
                        print(f"✅ Child profile found: {child_name}, age {child_age}")
                        if child_interests:
                            print(f"   Interests: {', '.join(child_interests[:3])}")
                    else:
                        print(f"⚠️ Child profile not found for ID: {child_id}, generating without personalization")
                except Exception as e:
                    print(f"⚠️ Could not fetch child profile: {str(e)}, continuing without personalization")
            
            # Generate unique ID
            lullaby_id = f"lullaby_{uuid.uuid4().hex[:12]}"
            print(f"📋 Generated lullaby ID: {lullaby_id}")
            
            # Step 1: Generate lyrics
            print(f"\n📝 Step 1/4: Generating lyrics...")
            lyrics = await self.generate_lyrics(description, child_name, child_age, child_interests)
            
            # Step 2: Generate music
            print(f"\n🎼 Step 2/4: Generating music...")
            prompt = "soft, loving, lullaby, sleep music, gentle piano, calm"
            audio_data = await self.generate_music(lyrics, prompt)
            
            # Step 3: Store to Firebase
            print(f"\n☁️ Step 3/4: Uploading to Firebase...")
            audio_url = await self.store_lullaby_audio(audio_data, lullaby_id, user_id)
            
            # Step 4: Save metadata
            print(f"\n💾 Step 4/4: Saving metadata to Firestore...")
            metadata = LullabyMetadata(
                lullaby_id=lullaby_id,
                user_id=user_id,
                child_id=child_id,
                child_name=child_name,
                description=description,
                lyrics=lyrics,
                prompt=prompt,
                audio_url=audio_url,
                duration_seconds=None,  # Could calculate from audio data if needed
                created_at=datetime.utcnow()
            )
            
            # Save metadata to Firestore
            await self.save_lullaby_metadata(metadata)
            
            print(f"\n{'='*80}")
            print(f"✅ LULLABY GENERATION COMPLETE")
            print(f"{'='*80}")
            print(f"Lullaby ID: {lullaby_id}")
            print(f"Audio URL: {audio_url}")
            print(f"Lyrics length: {len(lyrics)} chars")
            print(f"Audio size: {len(audio_data)} bytes")
            print(f"{'='*80}\n")
            
            return metadata
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ LULLABY GENERATION FAILED")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            print(f"{'='*80}\n")
            raise
    
    async def generate_lullaby_async(
        self,
        lullaby_id: str,
        user_id: str,
        description: str,
        child_id: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        completion_callback: Optional[Callable] = None
    ) -> LullabyMetadata:
        """
        Generate lullaby asynchronously with progress callbacks.
        Used for background generation with WebSocket updates.
        
        Args:
            lullaby_id: Pre-generated lullaby ID
            user_id: User ID generating the lullaby
            description: Description/theme for the lullaby
            child_id: Optional child ID for personalization
            progress_callback: Callback for progress updates (receives dict with status, progress, message)
            completion_callback: Callback for completion (receives dict with status and lullaby/error)
        
        Returns:
            LullabyMetadata with all generated content
        """
        try:
            # Notify: Starting
            if progress_callback:
                await progress_callback({
                    "status": "starting",
                    "progress": 0,
                    "message": "Initializing lullaby generation..."
                })
            
            print(f"\n{'='*80}")
            print(f"🎵 ASYNC LULLABY GENERATION STARTED")
            print(f"Lullaby ID: {lullaby_id}")
            print(f"User: {user_id}")
            print(f"Description: {description}")
            if child_id:
                print(f"Child ID: {child_id} (personalizing lyrics)")
            print(f"{'='*80}\n")
            
            # Get child profile if needed
            child_name = None
            child_age = None
            child_interests = None
            
            if child_id:
                try:
                    from app.services.content.child_service import child_service
                    child_profile = await child_service.get_child(user_id, child_id)
                    
                    if child_profile:
                        child_name = child_profile.name
                        child_age = child_profile.age
                        child_interests = child_profile.interests
                        print(f"✅ Child profile found: {child_name}, age {child_age}")
                except Exception as e:
                    print(f"⚠️ Could not fetch child profile: {e}")
            
            # Step 1: Generate lyrics (25% progress)
            if progress_callback:
                await progress_callback({
                    "status": "generating_lyrics",
                    "progress": 10,
                    "message": "Generating personalized lyrics..."
                })
            
            print(f"\n📝 Step 1/4: Generating lyrics...")
            lyrics = await self.generate_lyrics(description, child_name, child_age, child_interests)
            
            if progress_callback:
                await progress_callback({
                    "status": "lyrics_complete",
                    "progress": 25,
                    "message": "Lyrics generated! Creating music...",
                    "lyrics": lyrics
                })
            
            # Step 2: Generate music (75% progress)
            print(f"\n🎼 Step 2/4: Generating music...")
            prompt = "soft, loving, lullaby, sleep music, gentle piano, calm"
            audio_data = await self.generate_music(lyrics, prompt)
            
            if progress_callback:
                await progress_callback({
                    "status": "music_complete",
                    "progress": 75,
                    "message": "Music generated! Uploading to storage..."
                })
            
            # Step 3: Upload to Firebase Storage (90% progress)
            print(f"\n☁️ Step 3/4: Uploading to Firebase...")
            audio_url = await self.store_lullaby_audio(audio_data, lullaby_id, user_id)
            
            if progress_callback:
                await progress_callback({
                    "status": "upload_complete",
                    "progress": 90,
                    "message": "Upload complete! Saving metadata..."
                })
            
            # Step 4: Save metadata (100% progress)
            print(f"\n💾 Step 4/4: Saving metadata to Firestore...")
            metadata = LullabyMetadata(
                lullaby_id=lullaby_id,
                user_id=user_id,
                child_id=child_id,
                child_name=child_name,
                description=description,
                lyrics=lyrics,
                prompt=prompt,
                audio_url=audio_url,
                duration_seconds=None,
                created_at=datetime.utcnow()
            )
            
            await self.save_lullaby_metadata(metadata)
            
            print(f"\n{'='*80}")
            print(f"✅ ASYNC LULLABY GENERATION COMPLETE")
            print(f"{'='*80}")
            print(f"Lullaby ID: {lullaby_id}")
            print(f"Audio URL: {audio_url}")
            print(f"{'='*80}\n")
            
            # Notify completion
            if completion_callback:
                await completion_callback({
                    "status": "completed",
                    "lullaby": metadata.model_dump()
                })
            
            return metadata
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ ASYNC LULLABY GENERATION FAILED")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            print(f"{'='*80}\n")
            
            if completion_callback:
                await completion_callback({
                    "status": "failed",
                    "error": str(e)
                })
            raise
    
    async def get_user_lullabies(self, user_id: str) -> List[LullabyMetadata]:
        """Fetch all lullabies for a user
        
        Args:
            user_id: User ID to fetch lullabies for
            
        Returns:
            List of LullabyMetadata objects sorted by creation date (newest first)
        """
        try:
            loop = asyncio.get_running_loop()
            
            def fetch_lullabies():
                docs = self.db.collection('lullabies')\
                    .where('user_id', '==', user_id)\
                    .stream()
                
                lullabies = []
                for doc in docs:
                    data = doc.to_dict()
                    lullabies.append(LullabyMetadata(**data))
                
                # Sort in Python instead of Firestore (avoids index requirement)
                lullabies.sort(key=lambda x: x.created_at, reverse=True)
                
                return lullabies
            
            lullabies = await loop.run_in_executor(None, fetch_lullabies)
            print(f"✅ Retrieved {len(lullabies)} lullabies for user {user_id}")
            
            return lullabies
            
        except Exception as e:
            print(f"❌ Failed to fetch lullabies: {str(e)}")
            raise Exception(f"Failed to fetch lullabies: {str(e)}")
    
    async def get_lullaby(self, lullaby_id: str, user_id: str) -> Optional[LullabyMetadata]:
        """Fetch a specific lullaby
        
        Args:
            lullaby_id: Lullaby ID to fetch
            user_id: User ID (for authorization check)
            
        Returns:
            LullabyMetadata if found and owned by user, None otherwise
        """
        try:
            loop = asyncio.get_running_loop()
            
            def fetch_lullaby():
                doc = self.db.collection('lullabies').document(lullaby_id).get()
                if not doc.exists:
                    return None
                
                data = doc.to_dict()
                
                # Verify ownership
                if data.get('user_id') != user_id:
                    return None
                
                return LullabyMetadata(**data)
            
            lullaby = await loop.run_in_executor(None, fetch_lullaby)
            
            if lullaby:
                print(f"✅ Retrieved lullaby {lullaby_id}")
            else:
                print(f"⚠️ Lullaby {lullaby_id} not found or not owned by user")
            
            return lullaby
            
        except Exception as e:
            print(f"❌ Failed to fetch lullaby: {str(e)}")
            raise Exception(f"Failed to fetch lullaby: {str(e)}")
    
    async def delete_lullaby(self, lullaby_id: str, user_id: str) -> bool:
        """Delete a lullaby (metadata and audio file)
        
        Args:
            lullaby_id: Lullaby ID to delete
            user_id: User ID (for authorization check)
            
        Returns:
            True if deleted successfully, False if not found or not authorized
        """
        try:
            # First verify ownership
            lullaby = await self.get_lullaby(lullaby_id, user_id)
            if not lullaby:
                return False
            
            loop = asyncio.get_running_loop()
            
            # Delete from Firebase Storage
            try:
                bucket = storage.bucket()
                blob_path = f"lullabies/{user_id}/{lullaby_id}.mp3"
                blob = bucket.blob(blob_path)
                await loop.run_in_executor(None, lambda: blob.delete())
                print(f"✅ Deleted audio file: {blob_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete audio file (may not exist): {str(e)}")
            
            # Delete from Firestore
            def delete_metadata():
                self.db.collection('lullabies').document(lullaby_id).delete()
            
            await loop.run_in_executor(None, delete_metadata)
            print(f"✅ Deleted lullaby metadata: {lullaby_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to delete lullaby: {str(e)}")
            raise Exception(f"Failed to delete lullaby: {str(e)}")
