"""
Parallel Story Generation Service
================================
High-performance story generation with parallel processing and robust error handling
"""

import asyncio
import json
import time
import sys
from typing import List, Dict, Tuple, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
import logging

from app.models.content.story import StoryScene
from app.services.content.story_service import StoryService
from app.services.content.media_service import MediaService
from app.services.storage.storage_service import StorageService
from app.utils.helpers import calculate_audio_duration
from app.config import settings

# Global in-process idempotent media cache.
# This ensures that if a job is retried (same process) we do not re-call
# external providers for already generated assets (audio/images/thumbnail).
# Keyed by (story_id, scene_number) for audio/images and (story_id) for thumbnail.
PARALLEL_MEDIA_CACHE: Dict[str, Dict[tuple, bytes]] = {
    'audio': {},      # (story_id, scene_number) -> audio bytes
    'image': {},      # (story_id, scene_number) -> image bytes
    'thumbnail': {}   # (story_id, 0) -> thumbnail bytes
}

# Track in-flight generation futures to collapse concurrent duplicate requests.
PARALLEL_MEDIA_FUTURES: Dict[tuple, asyncio.Future] = {}

# Async lock to guard cache/futures maps.
PARALLEL_MEDIA_LOCK = asyncio.Lock()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GenerationTask:
    """Data class for tracking generation tasks"""
    task_id: str
    task_type: str  # 'story', 'audio', 'image', 'upload'
    scene_number: Optional[int] = None
    status: str = 'pending'  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

class ParallelStoryService:
    """Enhanced story service with parallel processing capabilities"""
    
    def __init__(self, story_service: StoryService, media_service: MediaService, storage_service: StorageService):
        self.story_service = story_service
        self.media_service = media_service
        self.storage_service = storage_service
        self.max_concurrent_tasks = settings.max_concurrent_tasks if hasattr(settings, 'max_concurrent_tasks') else 8  # Reduced to avoid API rate limits
        self.retry_attempts = 5  # ENHANCED: Increased from 3 to 5 for better recovery from transient failures
        self.retry_backoff_base = 2  # Base for exponential backoff
        self.retry_jitter_max = 1.0  # Max jitter in seconds to avoid thundering herd
        self.timeout_media_phase = 900  # ENHANCED: Increased from 600 to 900 (15 minutes)
        
        # Performance tracking
        self.tasks: List[GenerationTask] = []
        self.total_start_time = None
    
    async def _exponential_backoff_with_jitter(self, attempt: int) -> None:
        """Calculate exponential backoff with jitter to avoid thundering herd"""
        import random
        base_delay = self.retry_backoff_base ** attempt
        jitter = random.uniform(0, self.retry_jitter_max)
        delay = base_delay + jitter
        logger.info(f"⏳ Waiting {delay:.2f}s before retry attempt {attempt + 1}")
        await asyncio.sleep(delay)
        
    async def generate_story_parallel(
        self,
        story_id: str,
        user_prompt: str,
        user_id: str,
        target_scenes: int = 7,
        child_id: str = None,
        child_name: str = None,
        child_age: int = None,
        child_gender: str = None,  # 'boy', 'girl', or None
        morals: List[str] = None,
        story_length: str = "medium",
        art_style: str = "disney",
        voice_option: str = "female",
        dimensions: str = "1024x1024",
        use_cloned_voice: bool = True,
        voice_clone_id: str = None,
        language: str = "english",
        reference_images_metadata: List[Dict[str, Any]] = None,  # NEW: Reference image metadata
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a complete story with maximum parallelization and robustness
        """
        self.total_start_time = time.time()
        self.child_gender = child_gender
        self.art_style = art_style  # Store art_style for thumbnail generation
        
        logger.info(f"🚀 Story {story_id} | Gender: {child_gender or 'None'} | Art Style: {art_style} | Scenes: {target_scenes}")
        
        # Extract reference_image_urls from kwargs
        reference_image_urls = kwargs.get('reference_image_urls', [])
        reference_images_metadata = reference_images_metadata or []
        if reference_images_metadata:
            logger.info(f"📸 {len(reference_images_metadata)} reference image(s) with AI descriptions will be used for ALL scenes")
        
        # Remove reference_image_urls from kwargs before passing to story generation
        # (it's only needed for image generation, not story scene generation)
        story_kwargs = {k: v for k, v in kwargs.items() if k != 'reference_image_urls'}
        
        try:
            # Phase 1: Generate story structure (sequential - dependency)
            logger.info(f"📝 Phase 1: Calling OpenAI for story generation...")
            story_task = GenerationTask("story_generation", "story")
            self._start_task(story_task)
            
            # CRITICAL FIX: Yield control to event loop before CPU-intensive operation
            await asyncio.sleep(0)
            
            scenes, title, thumbnail_prompt = await self._generate_story_scenes_with_retry(
                user_prompt,
                user_id,
                target_scenes=target_scenes,
                child_id=child_id,
                child_name=child_name,
                child_age=child_age,
                morals=morals,
                story_length=story_length,
                art_style=art_style,
                language=language,
                reference_images_metadata=reference_images_metadata,  # NEW: Pass to OpenAI
                **story_kwargs
            )
            
            self._complete_task(story_task, {"scenes": scenes, "title": title, "thumbnail_prompt": thumbnail_prompt})
            
            print(f"✅ Story structure: {len(scenes)} scenes, title: {title}")
            sys.stdout.flush()
            
            
            # CRITICAL FIX: Yield control after story generation
            await asyncio.sleep(0)
            
            # Update story status
            print(f"💾 Updating story status → generating_media")
            sys.stdout.flush()
            await self.storage_service.update_story_status_and_title(story_id, "generating_media", title)
            print(f"✅ Story status updated")
            sys.stdout.flush()
            
            # Get user profile for personalization
            print(f"👤 Getting user profile for {user_id}...")
            sys.stdout.flush()
            user_profile = await self.story_service.user_service.get_user_profile(user_id)
            child_info = user_profile.get('child', {}) if user_profile else {}
            print(f"✅ User profile retrieved")
            sys.stdout.flush()
            
            # Get voice information for metadata storage
            print(f"🎤 Getting voice info...")
            sys.stdout.flush()
            voice_id = await self.media_service.cartesia_service.get_user_voice_id(user_id, use_cloned_voice) if user_id else None
            voice_name = None
            is_cloned = False
            
            if voice_id and voice_id != self.media_service.cartesia_service.default_voice_id:
                # This is a cloned voice - get details
                is_cloned = True
                try:
                    print(f"🔍 Fetching voice clone details...")
                    sys.stdout.flush()
                    active_voice_clone_id = await self.media_service.cartesia_service.get_active_voice_clone_id(user_id)
                    if active_voice_clone_id:
                        voice_clone_ref = self.media_service.cartesia_service.db.collection('users').document(user_id).collection('voice_clones').document(active_voice_clone_id)
                        voice_clone_doc = voice_clone_ref.get()
                        if voice_clone_doc.exists:
                            voice_clone_data = voice_clone_doc.to_dict()
                            voice_name = voice_clone_data.get('name', 'Custom Voice')
                except Exception as e:
                    logger.warning(f"Could not fetch voice name: {e}")
                    voice_name = "Custom Voice"
            else:
                voice_id = self.media_service.cartesia_service.default_voice_id
                voice_name = "British Lady (Default)"  # Cartesia's default voice
                is_cloned = False
            
            print(f"✅ Voice: {voice_name} (Cloned: {is_cloned})")
            sys.stdout.flush()
            
            
            # Phase 2: Parallel media generation with batching
            print(f"🎬 Phase 2: Parallel media generation for {len(scenes)} scenes")
            sys.stdout.flush()
            
            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
            
            # Prepare batch tasks
            audio_tasks = []
            image_tasks = []
            
            # Create audio generation tasks
            for i, scene in enumerate(scenes):
                task = GenerationTask(f"audio_{scene.scene_number}", "audio", scene.scene_number)
                self.tasks.append(task)
                # Convert ambient_sound_keywords string to list for MediaService compatibility
                ambient_keywords = [scene.ambient_sound_keywords] if scene.ambient_sound_keywords else None
                # Get emotion for this scene (default to "neutral" if not set)
                scene_emotion = getattr(scene, 'emotion', 'neutral')
                audio_task = asyncio.create_task(
                    self._generate_audio_with_semaphore(
                        semaphore, task, story_id, scene.text, scene.scene_number, voice_option == "female",
                        user_id, use_cloned_voice, ambient_keywords, language, scene_emotion, voice_clone_id
                    ),
                    name=f"audio_scene_{scene.scene_number}"
                )
                audio_tasks.append(audio_task)
            
            # Build list of ALL reference image URLs to pass to EVERY scene
            all_reference_urls = []
            if reference_images_metadata:
                all_reference_urls = [
                    ref.get('image_url')
                    for ref in reference_images_metadata
                    if ref.get('image_url')
                ]
                if all_reference_urls:
                    logger.info(f"🖼️ Using {len(all_reference_urls)} reference image(s) for ALL scenes")
            
            # Create image generation tasks
            for i, scene in enumerate(scenes):
                task = GenerationTask(f"image_{scene.scene_number}", "image", scene.scene_number)
                self.tasks.append(task)
                
                image_task = asyncio.create_task(
                    self._generate_image_with_semaphore(
                        semaphore, task, story_id, scene.visual_prompt, scene.scene_number,
                        child_info.get('image_url'), dimensions, all_reference_urls, reference_images_metadata
                    ),
                    name=f"image_scene_{scene.scene_number}"
                )
                image_tasks.append(image_task)
            
            # Generate thumbnail in parallel with same reference images and gender for consistency
            thumbnail_task = GenerationTask("thumbnail", "image")
            self.tasks.append(thumbnail_task)
            thumbnail_generation = asyncio.create_task(
                self._generate_thumbnail_with_semaphore(
                    semaphore, thumbnail_task, story_id, thumbnail_prompt, story_id, child_info.get('image_url'),
                    all_reference_urls, reference_images_metadata, art_style  # Pass art_style to thumbnail
                ),
                name="thumbnail_generation"
            )
            
            # Execute all media generation in parallel
            all_tasks = audio_tasks + image_tasks + [thumbnail_generation]
            
            logger.info(f"🎬 Phase 2: Parallel media generation | {len(audio_tasks)} audio + {len(image_tasks)} images + 1 thumbnail | Timeout: {self.timeout_media_phase}s")
            
            done, pending = await asyncio.wait(all_tasks, timeout=self.timeout_media_phase, return_when=asyncio.ALL_COMPLETED)
            
            if pending:
                logger.warning(f"⚠️ {len(pending)} tasks timed out after {self.timeout_media_phase}s - cancelling")
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
            else:
                logger.info(f"✅ All {len(done)} media tasks completed successfully")
                
            
            # Collect results from all tasks
            media_results = []
            for task in all_tasks:
                try:
                    if task.done() and not task.cancelled():
                        result = task.result()
                        media_results.append(result)
                    else:
                        logger.warning(f"⚠️ Task was cancelled or timed out")
                        media_results.append(Exception("Task timed out or cancelled"))
                except Exception as e:
                    logger.error(f"❌ Task failed with exception: {e}")
                    media_results.append(e)
            
            # Process results and separate audio/image data
            audio_data = []
            image_data = []
            thumbnail_data = None
            
            # Extract audio results
            for i, result in enumerate(media_results[:len(audio_tasks)]):
                if isinstance(result, Exception):
                    print(f"❌ Audio generation failed for scene {i+1}")
                    sys.stdout.flush()
                    logger.error(f"❌ Audio generation failed for scene {i+1}: {result}")
                    audio_data.append(None)
                else:
                    audio_data.append(result)
            
            # Extract image results  
            for i, result in enumerate(media_results[len(audio_tasks):len(audio_tasks)+len(image_tasks)]):
                if isinstance(result, Exception):
                    print(f"❌ Image generation failed for scene {i+1}")
                    sys.stdout.flush()
                    logger.error(f"❌ Image generation failed for scene {i+1}: {result}")
                    image_data.append(None)
                else:
                    image_data.append(result)
            
            # Extract thumbnail result
            thumbnail_result = media_results[-1]
            if not isinstance(thumbnail_result, Exception):
                thumbnail_data = thumbnail_result
            
            logger.info(f"📊 Media completed: {len([x for x in audio_data if x])}/{len(scenes)} audio, {len([x for x in image_data if x])}/{len(scenes)} images, thumbnail: {thumbnail_data is not None}")
            
            # CRITICAL FIX: Enforce atomic completion - ALL audio AND images must succeed
            successful_audio = sum(1 for x in audio_data if x)
            successful_images = sum(1 for x in image_data if x)
            total_scenes = len(scenes)
            
            # ATOMIC REQUIREMENT: All scenes must have BOTH audio AND images
            if successful_audio < total_scenes or successful_images < total_scenes:
                missing_audio_scenes = [i+1 for i, x in enumerate(audio_data) if not x]
                missing_image_scenes = [i+1 for i, x in enumerate(image_data) if not x]
                
                error_details = {
                    "total_scenes": total_scenes,
                    "successful_audio": successful_audio,
                    "successful_images": successful_images,
                    "missing_audio_scenes": missing_audio_scenes,
                    "missing_image_scenes": missing_image_scenes
                }
                
                error_msg = f"Story incomplete - ATOMIC VALIDATION FAILED:\n"
                error_msg += f"  Total scenes: {total_scenes}\n"
                error_msg += f"  Successful audio: {successful_audio}/{total_scenes}\n"
                error_msg += f"  Successful images: {successful_images}/{total_scenes}\n"
                if missing_audio_scenes:
                    error_msg += f"  Missing audio in scenes: {missing_audio_scenes}\n"
                if missing_image_scenes:
                    error_msg += f"  Missing images in scenes: {missing_image_scenes}\n"
                
                print(f"❌ ATOMIC VALIDATION FAILED: {error_msg}")
                sys.stdout.flush()
                logger.error(f"❌ {error_msg}")
                logger.error(f"❌ ATOMIC COMPLETION ENFORCED: Story will not be saved with partial content")
                raise Exception(error_msg)
            
            if not thumbnail_data:
                print(f"❌ Thumbnail generation failed")
                sys.stdout.flush()
                logger.error("❌ Thumbnail generation failed - story cannot be completed")
                raise Exception("Thumbnail generation failed")
            
            print(f"✅ All media generated successfully – atomic validation passed")
            print()
            sys.stdout.flush()
            logger.info("✅ All media generated successfully - proceeding with atomic upload")
            
            # Phase 3: Parallel uploads with retry logic
            print(f"☁️ Phase 3: Uploading to Firebase...")
            sys.stdout.flush()
            logger.info("☁️ Phase 3: Parallel uploads to Firebase...")
            logger.info(f"📤 Preparing {successful_audio} audio + {successful_images} image + {'1' if thumbnail_data else '0'} thumbnail uploads")

            
            upload_tasks = []
            
            # Create upload tasks for each scene - upload audio and images independently
            for i, scene in enumerate(scenes):
                # Upload audio if available
                if audio_data[i]:
                    audio_upload_task = GenerationTask(f"upload_audio_{scene.scene_number}", "upload", scene.scene_number)
                    self.tasks.append(audio_upload_task)
                    upload_tasks.append(
                        self._upload_with_retry(audio_upload_task, "audio", audio_data[i], story_id, scene.scene_number)
                    )
                
                # Upload image if available
                if image_data[i]:
                    image_upload_task = GenerationTask(f"upload_image_{scene.scene_number}", "upload", scene.scene_number)
                    self.tasks.append(image_upload_task)
                    upload_tasks.append(
                        self._upload_with_retry(image_upload_task, "image", image_data[i], story_id, scene.scene_number)
                    )
            
            # Thumbnail upload task
            if thumbnail_data:
                thumbnail_upload_task = GenerationTask("upload_thumbnail", "upload")
                self.tasks.append(thumbnail_upload_task)
                upload_tasks.append(
                    self._upload_with_retry(thumbnail_upload_task, "thumbnail", thumbnail_data, story_id)
                )
            
            # Execute all uploads in parallel
            print(f"📤 Executing {len(upload_tasks)} parallel upload tasks...")
            sys.stdout.flush()
            logger.info(f"⚡ Starting {len(upload_tasks)} parallel upload tasks...")
            upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            print(f"✅ All upload tasks completed")
            sys.stdout.flush()
            logger.info(f"✅ All upload tasks completed")
            
            # CRITICAL FIX: Validate atomic upload - ALL uploads must succeed
            print(f"🔍 Validating atomic upload...")
            sys.stdout.flush()
            upload_failures = []
            for i, result in enumerate(upload_results):
                if isinstance(result, Exception):
                    # Determine which scene this upload was for
                    task_desc = f"Upload task {i}"
                    if i < len(scenes) * 2:  # Audio and image uploads for scenes
                        scene_idx = i // 2
                        upload_type = "audio" if i % 2 == 0 else "image"
                        task_desc = f"Scene {scenes[scene_idx].scene_number} {upload_type}"
                    elif i == len(upload_results) - 1:  # Last task is thumbnail
                        task_desc = "Thumbnail"
                    
                    upload_failures.append(f"{task_desc}: {str(result)[:100]}")
            
            if upload_failures:
                error_msg = f"❌ Atomic upload failed - {len(upload_failures)} upload(s) failed:\n"
                error_msg += "\n".join(f"  - {failure}" for failure in upload_failures)
                logger.error(error_msg)
                logger.error("❌ ATOMIC COMPLETION ENFORCED: Story will not be saved with incomplete uploads")
                raise Exception(f"Upload failures: {len(upload_failures)} tasks failed")

            
            # Process upload results and update scenes
            audio_upload_results = {}  # scene_number -> (url, duration_ms)
            audio_durations = {}  # scene_number -> duration_ms
            image_upload_results = {}
            thumbnail_url = None
            
            # Map results back to scenes based on task names
            upload_index = 0
            for i, scene in enumerate(scenes):
                # Check for audio upload result
                if audio_data[i]:
                    audio_result = upload_results[upload_index]
                    if not isinstance(audio_result, Exception) and audio_result:
                        # audio_result is a tuple (url, duration_ms)
                        if isinstance(audio_result, tuple) and len(audio_result) == 2:
                            url, duration_ms = audio_result
                            audio_upload_results[scene.scene_number] = url
                            if duration_ms:
                                audio_durations[scene.scene_number] = duration_ms
                        else:
                            # Fallback for old format (just URL)
                            audio_upload_results[scene.scene_number] = audio_result
                    upload_index += 1
                
                # Check for image upload result
                if image_data[i]:
                    image_result = upload_results[upload_index]
                    if not isinstance(image_result, Exception):
                        image_upload_results[scene.scene_number] = image_result
                    upload_index += 1
            
            # Get thumbnail URL if it was uploaded
            if thumbnail_data and upload_index < len(upload_results):
                thumbnail_result = upload_results[upload_index]
                if not isinstance(thumbnail_result, Exception):
                    thumbnail_url = thumbnail_result
            
            # CRITICAL FIX: Final validation - ensure ALL scenes have audio AND images
            missing_content = []
            for scene in scenes:
                if scene.scene_number not in audio_upload_results:
                    missing_content.append(f"Scene {scene.scene_number}: missing audio URL")
                if scene.scene_number not in image_upload_results:
                    missing_content.append(f"Scene {scene.scene_number}: missing image URL")
            
            if not thumbnail_url:
                missing_content.append("Thumbnail: missing thumbnail URL")
            
            if missing_content:
                error_msg = f"❌ Incomplete story - missing content after uploads:\n"
                error_msg += "\n".join(f"  - {item}" for item in missing_content)
                logger.error(error_msg)
                logger.error("❌ ATOMIC COMPLETION ENFORCED: Story will not be saved")
                raise Exception(f"Incomplete story: {len(missing_content)} missing items")
            
            logger.info(f"✅ Atomic validation passed: All {len(scenes)} scenes have complete audio + images + thumbnail")
            
            logger.info(f"📊 Extracted {len(audio_durations)} actual audio durations from uploaded files")
            
            # Update scenes with upload results
            for i, scene in enumerate(scenes):
                # Set audio URL if available
                if scene.scene_number in audio_upload_results:
                    scene.audio_url = audio_upload_results[scene.scene_number]
                
                # Set image URL if available
                if scene.scene_number in image_upload_results:
                    scene.image_url = image_upload_results[scene.scene_number]
                
                # Calculate timing using actual durations where available
                scene.start_time = 0
                for j in range(i):
                    prev_scene = scenes[j]
                    if prev_scene.scene_number in audio_durations:
                        scene.start_time += audio_durations[prev_scene.scene_number]
                    else:
                        # Fallback to estimation
                        scene.start_time += calculate_audio_duration(prev_scene.text)
            
            # Phase 4: Create final manifest
            print(f"📋 Phase 4: Creating final manifest...")
            sys.stdout.flush()
            logger.info("📋 Phase 4: Creating final manifest...")
            
            scenes_data = []
            total_duration = 0
            
            for scene in scenes:
                # Use actual duration if available, otherwise estimate
                if scene.scene_number in audio_durations:
                    duration = audio_durations[scene.scene_number]
                    logger.info(f"✅ Scene {scene.scene_number}: Using actual duration {duration}ms")
                else:
                    duration = calculate_audio_duration(scene.text)
                    logger.warning(f"⚠️ Scene {scene.scene_number}: Using estimated duration {duration}ms")
                
                scene_data = {
                    "scene_number": scene.scene_number,
                    "text": scene.text,
                    "visual_prompt": scene.visual_prompt,
                    "audio_url": getattr(scene, 'audio_url', None),
                    "image_url": getattr(scene, 'image_url', None),
                    "start_time": getattr(scene, 'start_time', 0),
                    "duration": duration,
                    "includes_child": scene.includes_child,
                    "ambient_sound_keywords": scene.ambient_sound_keywords,
                    "emotion": scene.emotion
                }
                scenes_data.append(scene_data)
                total_duration += duration
            
            logger.info(f"⏱️  Total story duration: {total_duration}ms ({total_duration/1000:.2f}s)")
            
            # Create performance metrics
            total_time = time.time() - self.total_start_time
            performance_metrics = self._generate_performance_metrics(total_time)
            
            manifest = {
                "story_id": story_id,
                "title": title,
                "user_prompt": user_prompt,
                # Parent-centric metadata
                "child_id": child_id,
                "child_name": child_name,
                "child_age": child_age,
                "morals": morals,
                "story_length": story_length,
                "art_style": art_style,
                "voice_option": voice_option,
                "dimensions": dimensions,
                "total_scenes": len(scenes),
                "total_duration": total_duration,
                "thumbnail_url": thumbnail_url,
                "scenes": scenes_data,
                "generated_at": datetime.utcnow().isoformat(),
                "status": "completed",
                "generation_method": "parallel_processing_v2",
                "voice_metadata": {
                    "voice_id": voice_id,
                    "voice_name": voice_name,
                    "is_cloned": is_cloned,
                    "language": language
                },
                "ai_models_used": {
                    "text_generation": "gpt-4o-mini",
                    "audio_generation": "cartesia-sonic-3",
                    "image_generation": "gpt-image-1-mini"
                },
                "image_format": "custom_dimensions_from_deepai",
                "performance_metrics": performance_metrics,
                "optimizations": [
                    "parallel_media_generation",
                    "batch_audio_processing", 
                    "batch_image_processing",
                    "parallel_uploads",
                    "retry_mechanisms",
                    "semaphore_rate_limiting",
                    "exception_handling",
                    "performance_tracking",
                    "opus_audio_optimization"
                ]
            }
            
            # Save final story metadata
            print(f"💾 Saving final story metadata to Firestore...")
            sys.stdout.flush()
            await self.storage_service.save_story_metadata(
                story_id, user_id, title, user_prompt, manifest
            )
            print(f"✅ Story metadata saved to Firestore!")
            sys.stdout.flush()
            
            print(f"🎉 STORY GENERATION COMPLETE in {total_time:.2f}s | id={story_id} | scenes={len(scenes)} | duration={total_duration/1000:.2f}s")
            sys.stdout.flush()
            logger.info(f"🎉 Parallel story generation completed in {total_time:.2f}s")
            return manifest
            
        except Exception as e:
            import traceback
            print(f"❌ STORY GENERATION FAILED: {str(e)}")
            sys.stdout.flush()
            logger.error(f"❌ Parallel story generation failed: {str(e)}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            await self._handle_generation_failure(story_id, user_id, user_prompt, str(e))
            raise
    
    async def _generate_story_scenes_with_retry(self, *args, **kwargs) -> Tuple[List[StoryScene], str, str]:
        """Generate story scenes with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                print(f"🤖 OpenAI story generation attempt {attempt + 1}/{self.retry_attempts}...")
                sys.stdout.flush()
                logger.info(f"🤖 Calling OpenAI for story generation (attempt {attempt + 1}/{self.retry_attempts})...")
                
                result = await self.story_service.generate_story_scenes(*args, **kwargs)
                
                print(f"✅ OpenAI story generation completed successfully")
                sys.stdout.flush()
                logger.info(f"✅ OpenAI story generation completed successfully!")
                return result
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    print(f"❌ Story generation failed after {self.retry_attempts} attempts: {e}")
                    sys.stdout.flush()
                    logger.error(f"❌ Story generation failed after {self.retry_attempts} attempts: {e}")
                    raise
                print(f"⚠️ Story generation attempt {attempt + 1} failed: {e}, retrying...")
                sys.stdout.flush()
                logger.warning(f"⚠️ Story generation attempt {attempt + 1} failed: {e}, retrying...")
                await asyncio.sleep(1)
    
    async def _generate_audio_with_semaphore(
        self, semaphore: asyncio.Semaphore, task: GenerationTask,
        story_id: str, text: str, scene_number: int, is_female: bool, user_id: str, use_cloned_voice: bool,
        ambient_sound_keywords: List[str] = None, language: str = "english", emotion: str = "neutral",
        voice_clone_id: str = None
    ):
        """Generate audio with semaphore control and retry logic - optimized"""
        print(f"🎵 Audio generation for scene {scene_number} (emotion: {emotion})")
        if ambient_sound_keywords:
            print(f"🌿 Ambient keywords: {ambient_sound_keywords}")
        # Check idempotent cache first
        cache_key = (story_id, scene_number)
        async with PARALLEL_MEDIA_LOCK:
            if cache_key in PARALLEL_MEDIA_CACHE['audio']:
                cached = PARALLEL_MEDIA_CACHE['audio'][cache_key]
                self._complete_task(task, cached)
                return cached
            # Collapse duplicate in-flight generation
            in_flight_key = ('audio',) + cache_key
            existing_future = PARALLEL_MEDIA_FUTURES.get(in_flight_key)
            if existing_future:
                result = await existing_future
                self._complete_task(task, result)
                return result
            # Create placeholder future
            loop = asyncio.get_running_loop()
            future: asyncio.Future = loop.create_future()
            PARALLEL_MEDIA_FUTURES[in_flight_key] = future
        async with semaphore:
            self._start_task(task)
            
            last_exception = None
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"🎤 Generating audio for scene {scene_number} (attempt {attempt + 1}/{self.retry_attempts}, emotion: {emotion})")
                    
                    # Try with original parameters
                    audio_data = await self.media_service.generate_audio(
                        text, scene_number, is_female, user_id, use_cloned_voice,
                        ambient_sound_keywords, language, emotion, voice_clone_id
                    )
                    
                    if audio_data and len(audio_data) > 100:  # Validate non-empty audio
                        async with PARALLEL_MEDIA_LOCK:
                            PARALLEL_MEDIA_CACHE['audio'][cache_key] = audio_data
                            in_flight_key = ('audio',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_result(audio_data)
                        self._complete_task(task, audio_data)
                        logger.info(f"✅ Audio generated successfully for scene {scene_number}")
                        return audio_data
                    else:
                        raise Exception("Generated audio data is too small or empty")
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"❌ Audio failed for scene {scene_number}, attempt {attempt + 1}/{self.retry_attempts}: {str(e)[:100]}")
                    
                    # ENHANCED: Try progressive fallbacks after 2 attempts
                    if attempt >= 2 and use_cloned_voice:
                        logger.info(f"🔄 Switching to default voice for scene {scene_number}")
                        try:
                            audio_data = await self.media_service.generate_audio(
                                text, scene_number, is_female, user_id, False,  # use_cloned_voice=False
                                ambient_sound_keywords, language, emotion, None
                            )
                            if audio_data and len(audio_data) > 100:
                                async with PARALLEL_MEDIA_LOCK:
                                    PARALLEL_MEDIA_CACHE['audio'][cache_key] = audio_data
                                    in_flight_key = ('audio',) + cache_key
                                    fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                                    if fut and not fut.done():
                                        fut.set_result(audio_data)
                                self._complete_task(task, audio_data)
                                logger.info(f"✅ Audio generated with default voice for scene {scene_number}")
                                return audio_data
                        except Exception as fallback_e:
                            logger.warning(f"⚠️ Default voice fallback also failed: {str(fallback_e)[:100]}")
                    
                    if attempt == self.retry_attempts - 1:
                        # Final failure - audio is required for atomic completion
                        self._fail_task(task, str(last_exception)[:200])
                        async with PARALLEL_MEDIA_LOCK:
                            in_flight_key = ('audio',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_exception(last_exception)
                        logger.error(f"❌ Audio generation failed permanently for scene {scene_number} after {self.retry_attempts} attempts")
                        raise Exception(f"Audio generation failed for scene {scene_number} after {self.retry_attempts} attempts: {str(last_exception)}")
                
                # Exponential backoff with jitter
                if attempt < self.retry_attempts - 1:
                    await self._exponential_backoff_with_jitter(attempt)
    
    async def _generate_image_with_semaphore(
        self, semaphore: asyncio.Semaphore, task: GenerationTask,
        story_id: str, visual_prompt: str, scene_number: int, child_image_url: str, dimensions: str,
        reference_image_urls: List[str] = None,
        reference_images_metadata: List[Dict[str, Any]] = None
    ):
        """Generate image with semaphore control and retry logic - optimized for 2K"""
        cache_key = (story_id, scene_number)
        async with PARALLEL_MEDIA_LOCK:
            if cache_key in PARALLEL_MEDIA_CACHE['image']:
                cached = PARALLEL_MEDIA_CACHE['image'][cache_key]
                self._complete_task(task, cached)
                return cached
            in_flight_key = ('image',) + cache_key
            existing_future = PARALLEL_MEDIA_FUTURES.get(in_flight_key)
            if existing_future:
                result = await existing_future
                self._complete_task(task, result)
                return result
            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            PARALLEL_MEDIA_FUTURES[in_flight_key] = fut
        async with semaphore:
            self._start_task(task)
            
            last_exception = None
            for attempt in range(self.retry_attempts):
                try:
                    # Parse dimensions
                    if 'x' in str(dimensions):
                        parts = str(dimensions).lower().split('x')
                        width = int(parts[0])
                        height = int(parts[1]) if len(parts) > 1 else width
                    else:
                        dimension_map = {
                            "portrait": (1290, 2796),
                            "landscape": (2796, 1290),
                            "square": (2048, 2048),
                            "2k": (2048, 2048),
                            "4k": (4096, 4096)
                        }
                        width, height = dimension_map.get(str(dimensions).lower(), (2048, 2048))
                    
                    logger.info(f"🎨 Generating image for scene {scene_number} (attempt {attempt + 1}/{self.retry_attempts})")
                    
                    # Try with original parameters
                    image_data = await self.media_service.generate_image(
                        visual_prompt, scene_number, child_image_url, (width, height),
                        reference_image_urls=reference_image_urls,
                        child_gender=getattr(self, 'child_gender', None),
                        reference_images_metadata=reference_images_metadata,
                        art_style_hint=getattr(self, 'art_style', None)
                    )
                    
                    # Validate image data
                    if image_data and len(image_data) > 1000:  # At least 1KB
                        async with PARALLEL_MEDIA_LOCK:
                            PARALLEL_MEDIA_CACHE['image'][cache_key] = image_data
                            in_flight_key = ('image',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_result(image_data)
                        self._complete_task(task, image_data)
                        logger.info(f"✅ Image scene {scene_number}: {len(image_data)} bytes")
                        return image_data
                    else:
                        raise Exception("Generated image data is too small or empty")
                    
                except Exception as e:
                    last_exception = e
                    error_msg = str(e)[:100]
                    
                    # Check if this is a timeout error
                    is_timeout = "timed out" in error_msg.lower() or "timeout" in error_msg.lower()
                    
                    if is_timeout:
                        logger.warning(f"⏱️ Image generation TIMEOUT for scene {scene_number}, attempt {attempt + 1}/{self.retry_attempts}")
                    else:
                        logger.warning(f"❌ Image failed for scene {scene_number}, attempt {attempt + 1}/{self.retry_attempts}: {error_msg}")
                    
                    # ENHANCED: Try without reference images as fallback only after 3 attempts (give references more chances)
                    if attempt >= 3 and (child_image_url or reference_image_urls):
                        logger.warning(f"⚠️ Reference images may be causing issues - retrying without them for scene {scene_number}")
                        try:
                            image_data = await self.media_service.generate_image(
                                visual_prompt, scene_number, None, (width, height), reference_image_urls=None,
                                child_gender=getattr(self, 'child_gender', None),
                                art_style_hint=getattr(self, 'art_style', None)
                            )
                            if image_data and len(image_data) > 1000:
                                async with PARALLEL_MEDIA_LOCK:
                                    PARALLEL_MEDIA_CACHE['image'][cache_key] = image_data
                                    in_flight_key = ('image',) + cache_key
                                    fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                                    if fut and not fut.done():
                                        fut.set_result(image_data)
                                self._complete_task(task, image_data)
                                logger.info(f"✅ Image generated without references for scene {scene_number}")
                                return image_data
                        except Exception as fallback_e:
                            logger.warning(f"⚠️ Image fallback without references also failed: {str(fallback_e)[:100]}")
                    
                    if attempt == self.retry_attempts - 1:
                        self._fail_task(task, str(last_exception)[:200])
                        async with PARALLEL_MEDIA_LOCK:
                            in_flight_key = ('image',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_exception(last_exception)
                        logger.error(f"❌ Image generation failed permanently for scene {scene_number} after {self.retry_attempts} attempts")
                        raise Exception(f"Image generation failed for scene {scene_number} after {self.retry_attempts} attempts: {str(last_exception)}")
                
                # Exponential backoff with jitter
                if attempt < self.retry_attempts - 1:
                    await self._exponential_backoff_with_jitter(attempt)
    
    async def _generate_thumbnail_with_semaphore(
        self, semaphore: asyncio.Semaphore, task: GenerationTask,
        story_id: str, thumbnail_prompt: str, story_id_for_cache: str, child_image_url: str,
        reference_image_urls: List[str] = None,
        reference_images_metadata: List[Dict[str, Any]] = None,
        art_style: str = "disney"
    ):
        """Generate thumbnail with semaphore control and retry logic - optimized"""
        cache_key = (story_id_for_cache, 0)
        async with PARALLEL_MEDIA_LOCK:
            if cache_key in PARALLEL_MEDIA_CACHE['thumbnail']:
                cached = PARALLEL_MEDIA_CACHE['thumbnail'][cache_key]
                self._complete_task(task, cached)
                return cached
            in_flight_key = ('thumbnail',) + cache_key
            existing_future = PARALLEL_MEDIA_FUTURES.get(in_flight_key)
            if existing_future:
                result = await existing_future
                self._complete_task(task, result)
                return result
            loop = asyncio.get_running_loop()
            fut: asyncio.Future = loop.create_future()
            PARALLEL_MEDIA_FUTURES[in_flight_key] = fut
        async with semaphore:
            self._start_task(task)
            
            last_exception = None
            for attempt in range(self.retry_attempts):
                try:
                    logger.info(f"🖼️ Generating thumbnail (attempt {attempt + 1}/{self.retry_attempts})")
                    if reference_image_urls:
                        logger.info(f"📸 Using {len(reference_image_urls)} reference image(s) for thumbnail consistency")
                    
                    thumbnail_data = await self.media_service.generate_story_thumbnail(
                        thumbnail_prompt, story_id, child_image_url,
                        reference_image_urls=reference_image_urls,
                        child_gender=getattr(self, 'child_gender', None),
                        reference_images_metadata=reference_images_metadata,
                        art_style=art_style
                    )
                    
                    if thumbnail_data and len(thumbnail_data) > 1000:  # At least 1KB
                        async with PARALLEL_MEDIA_LOCK:
                            PARALLEL_MEDIA_CACHE['thumbnail'][cache_key] = thumbnail_data
                            in_flight_key = ('thumbnail',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_result(thumbnail_data)
                        self._complete_task(task, thumbnail_data)
                        logger.info(f"✅ Thumbnail generated successfully")
                        return thumbnail_data
                    else:
                        raise Exception("Generated thumbnail is too small or empty")
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"❌ Thumbnail failed, attempt {attempt + 1}/{self.retry_attempts}: {str(e)[:100]}")
                    if attempt == self.retry_attempts - 1:
                        self._fail_task(task, str(last_exception)[:200])
                        async with PARALLEL_MEDIA_LOCK:
                            in_flight_key = ('thumbnail',) + cache_key
                            fut = PARALLEL_MEDIA_FUTURES.pop(in_flight_key, None)
                            if fut and not fut.done():
                                fut.set_exception(last_exception)
                        logger.error(f"❌ Thumbnail generation failed permanently after {self.retry_attempts} attempts")
                        raise Exception(f"Thumbnail generation failed: {str(last_exception)}")
                
                # Exponential backoff with jitter
                if attempt < self.retry_attempts - 1:
                    await self._exponential_backoff_with_jitter(attempt)
    
    async def _upload_with_retry(
        self, task: GenerationTask, upload_type: str, data: bytes, 
        story_id: str, scene_number: int = None
    ):
        """Upload data with ENHANCED retry logic and exponential backoff - returns URL for images/thumbnail, (URL, duration) for audio"""
        if not data or len(data) < 100:
            logger.warning(f"⚠️ Skipping upload of invalid {upload_type} data for scene {scene_number}")
            self._fail_task(task, "Invalid or empty data")
            raise Exception(f"Invalid or empty {upload_type} data")
            
        self._start_task(task)
        
        last_exception = None
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"☁️ Uploading {upload_type} for scene {scene_number} (attempt {attempt + 1}/{self.retry_attempts})")
                
                if upload_type == "audio":
                    result = await self.storage_service.upload_audio(data, story_id, scene_number)
                    self._complete_task(task, result)
                    logger.info(f"✅ Audio uploaded successfully for scene {scene_number}")
                    return result
                elif upload_type == "image":
                    url = await self.storage_service.upload_scene_image(data, story_id, scene_number)
                    self._complete_task(task, url)
                    logger.info(f"✅ Image uploaded successfully for scene {scene_number}")
                    return url
                elif upload_type == "thumbnail":
                    url = await self.storage_service.upload_story_thumbnail(data, story_id)
                    self._complete_task(task, url)
                    logger.info(f"✅ Thumbnail uploaded successfully")
                    return url
                else:
                    raise ValueError(f"Unknown upload type: {upload_type}")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"❌ {upload_type} upload failed for scene {scene_number}, attempt {attempt + 1}/{self.retry_attempts}: {str(e)[:100]}")
                
                if attempt == self.retry_attempts - 1:
                    self._fail_task(task, str(last_exception)[:200])
                    logger.error(f"❌ Upload failed permanently for {upload_type} scene {scene_number} after {self.retry_attempts} attempts")
                    raise Exception(f"{upload_type} upload failed after {self.retry_attempts} attempts: {str(last_exception)}")
                
                # Exponential backoff with jitter for uploads
                await self._exponential_backoff_with_jitter(attempt)
    
    def _start_task(self, task: GenerationTask):
        """Mark task as started"""
        task.status = 'running'
        task.start_time = time.time()
    
    def _complete_task(self, task: GenerationTask, result: Any):
        """Mark task as completed"""
        task.status = 'completed'
        task.end_time = time.time()
        task.result = result
    
    def _fail_task(self, task: GenerationTask, error: str):
        """Mark task as failed"""
        task.status = 'failed'
        task.end_time = time.time()
        task.error = error
    
    def _generate_performance_metrics(self, total_time: float) -> Dict[str, Any]:
        """Generate detailed performance metrics"""
        completed_tasks = [t for t in self.tasks if t.status == 'completed']
        failed_tasks = [t for t in self.tasks if t.status == 'failed']
        
        task_durations = {
            task_type: [t.duration for t in completed_tasks if t.task_type == task_type]
            for task_type in ['story', 'audio', 'image', 'upload']
        }
        
        return {
            "total_generation_time": round(total_time, 2),
            "total_tasks": len(self.tasks),
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": round(len(completed_tasks) / len(self.tasks) * 100, 1) if self.tasks else 0,
            "average_task_durations": {
                task_type: round(sum(durations) / len(durations), 2) if durations else 0
                for task_type, durations in task_durations.items()
            },
            "parallel_efficiency": {
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "audio_generation_parallel": True,
                "image_generation_parallel": True,
                "upload_parallel": True,
                "estimated_sequential_time": sum(t.duration for t in completed_tasks),
                "actual_parallel_time": total_time,
                "speedup_factor": round(sum(t.duration for t in completed_tasks) / total_time, 1) if total_time > 0 else 1
            },
            "task_breakdown": {
                task_type: {
                    "count": len([t for t in self.tasks if t.task_type == task_type]),
                    "completed": len([t for t in completed_tasks if t.task_type == task_type]),
                    "failed": len([t for t in failed_tasks if t.task_type == task_type]),
                    "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0
                }
                for task_type, durations in task_durations.items()
            }
        }
    
    async def _handle_generation_failure(self, story_id: str, user_id: str, user_prompt: str, error: str):
        """Handle generation failure and update story status"""
        error_manifest = {
            "story_id": story_id,
            "title": "Generation Failed",
            "user_prompt": user_prompt,
            "status": "failed",
            "error": error,
            "generated_at": datetime.utcnow().isoformat(),
            "generation_method": "parallel_processing_v2",
            "performance_metrics": self._generate_performance_metrics(time.time() - self.total_start_time) if self.total_start_time else {}
        }
        
        await self.storage_service.save_story_metadata(
            story_id, user_id, "Generation Failed", user_prompt, error_manifest
        )

# Utility functions for backwards compatibility
async def create_parallel_story_service(
    story_service: StoryService, 
    media_service: MediaService, 
    storage_service: StorageService
) -> ParallelStoryService:
    """Factory function to create a parallel story service"""
    return ParallelStoryService(story_service, media_service, storage_service)
