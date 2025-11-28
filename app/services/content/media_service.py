# ===== app/services/media_service.py - SEEDREAM 4 IMPLEMENTATION =====
# Updated: October 27, 2025 - Switched to SeeDream 4 hosted by Replicate for image generation
import io
import json
import time
import base64
import asyncio
import aiohttp
import httpx
import random
import tempfile
from typing import Union, List, Dict, Any
from fastapi import HTTPException
from openai import OpenAI
import replicate
from app.config import settings
from app.services.storage.storage_service import StorageService
from app.services.ai.cartesia_service import CartesiaService
from app.services.content.audio_mixer_service import AudioMixerService
from app.utils.audio_processor import AudioProcessor
from app.utils.async_utils import get_or_create_event_loop
from PIL import Image

class MediaService:
    def __init__(self, openai_client: OpenAI):
        self.openai_client = openai_client
        self.cartesia_service = CartesiaService()  # Cartesia for TTS and voice cloning
        self.audio_mixer_service = AudioMixerService()
        # Initialize async HTTP client for non-blocking requests
        self.http_client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        # Initialize Replicate client for SeeDream 4
        if settings.replicate_api_token:
            import os
            os.environ['REPLICATE_API_TOKEN'] = settings.replicate_api_token
            print("✅ MediaService initialized with SeeDream 4 (Replicate)")
        else:
            print("⚠️ Replicate API token not configured - image generation may not work")
        
        # Face consistency instructions to append to all prompts
        self.face_consistency_instructions = """

⚠️ REFERENCE IMAGE(S) PROVIDED - USE THESE FACES AS PRIMARY VISUAL SOURCE!

Analyze the provided reference image carefully and recreate the person with a face that closely resembles the sample image. Maintain all key physical attributes — including the same skin tone, eye color, hair color, hairstyle, facial structure, and overall appearance. ⁠Image should be {art_style} style
FACE MATCHING:
•⁠ ⁠The reference images show the EXACT face(s) that must appear in this scene
•⁠ ⁠Copy the facial features, structure, and likeness from the reference images precisely
•⁠ ⁠The face in the reference image is THE TRUTH - match it exactly
•⁠ ⁠Do NOT invent new facial features - use ONLY what you see in the reference
•⁠ ⁠Ensure the person remains easily recognizable as the same individual from the reference image

PHYSICAL ATTRIBUTES FROM REFERENCE:
•⁠ ⁠Skin tone: Copy the exact skin tone from the reference image
•⁠ ⁠Hair: Match color, texture, style, and length from reference
•⁠ ⁠Eyes: Match eye color and shape from reference
•⁠ ⁠Face structure: Copy cheekbones, nose, jawline, face shape
•⁠ ⁠All physical characteristics must match the reference exactly

SCENE ADAPTATION:
•⁠ ⁠Keep the SAME FACE from reference in different poses/angles as needed
•⁠ ⁠You may adjust the pose, body position, and facial expression to make the final image more engaging, friendly, and appealing to young children
•⁠ ⁠Change clothing, background, and setting as described in text prompt
•⁠ ⁠But NEVER change the face, skin tone, hair, or core physical features

STYLE AND PRESENTATION:
•⁠ ⁠The composition, colors, and lighting should all contribute to a cheerful, and visually inviting look suitable for children's content
•⁠ ⁠Child-safe and emotionally positive presentation
"""
    
    def _create_placeholder_image(self, dimensions: tuple = (1024, 1024)) -> bytes:
        """Create a simple placeholder image with text overlay at specified dimensions"""
        try:
            width, height = dimensions
            # Create an image with the specified dimensions
            image = Image.new('RGB', (width, height), color='#f0f0f0')
            
            # Add simple text overlay
            try:
                # Try to use a basic font
                from PIL import ImageDraw
                draw = ImageDraw.Draw(image)
                
                # Add centered text
                text = "Story Image\nGenerating..."
                text_bbox = draw.textbbox((0, 0), text)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                x = (width - text_width) // 2
                y = (height - text_height) // 2
                
                draw.text((x, y), text, fill='#666666')
                
            except Exception:
                pass  # Skip text if font issues
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=85)
            return output_buffer.getvalue()
            
        except Exception as e:
            print(f"⚠️ Error creating placeholder: {e}")
            # Return minimal valid JPEG
            width, height = dimensions
            minimal_image = Image.new('RGB', (width, height), color='white')
            buffer = io.BytesIO()
            minimal_image.save(buffer, format='JPEG')
            return buffer.getvalue()
    
    def _process_image_fast(self, image_data: bytes, target_dimensions: tuple = (1024, 1024)) -> bytes:
        """Optimized image processing for speed with custom dimensions"""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Fast resize with lower quality for speed
            resized_image = image.resize(target_dimensions, Image.NEAREST)  # Faster than LANCZOS
            
            if resized_image.mode in ('RGBA', 'LA', 'P'):
                resized_image = resized_image.convert('RGB')
            
            output_buffer = io.BytesIO()
            resized_image.save(output_buffer, format='JPEG', quality=75, optimize=False)  # Lower quality, no optimization for speed
            
            return output_buffer.getvalue()
        except:
            return self._create_placeholder_image(target_dimensions)

    def _normalize_replicate_output(self, output) -> Union[str, bytes, None]:
        """
        Normalize replicate.run() output to either a URL string or raw image bytes.

        Returns:
            - str: a URL that can be fetched with httpx
            - bytes: raw image bytes (already downloaded/saved)
            - None: if nothing usable could be extracted
        """
        try:
            # If it's already a string URL
            if isinstance(output, str):
                return output

            # If it's a list/tuple, recurse on first element
            if isinstance(output, (list, tuple)) and len(output) > 0:
                return self._normalize_replicate_output(output[0])

            # If it's a mapping (dict-like) with 'url'
            if isinstance(output, dict):
                url = output.get('url') or output.get('file') or output.get('path')
                if isinstance(url, str):
                    return url

            # Generic file-like handling (covers replicate.helpers.FileOutput and similar)
            try:
                # Try common URL-like attributes first
                for attr in ('url', '_url', 'path', 'file', 'name'):
                    if hasattr(output, attr):
                        val = getattr(output, attr)
                        if isinstance(val, str) and val:
                            return val

                # Try to save to a temp file if a save method exists
                if hasattr(output, 'save'):
                    try:
                        tmp = tempfile.NamedTemporaryFile(delete=False)
                        tmp_name = tmp.name
                        tmp.close()
                        output.save(tmp_name)
                        with open(tmp_name, 'rb') as f:
                            data = f.read()
                        return data
                    except Exception:
                        pass

                # Some FileOutput objects are file-like and support read()
                if hasattr(output, 'read'):
                    try:
                        data = output.read()
                        if isinstance(data, (bytes, bytearray)):
                            return bytes(data)
                    except Exception:
                        pass
            except Exception:
                # If something goes wrong, continue to other fallbacks
                pass

            # Fallback: try to coerce to str and hope it's a URL
            try:
                s = str(output)
                if s.startswith('http'):
                    return s
            except Exception:
                pass

        except Exception:
            pass

        return None
    
    # FACE SWAP FEATURE - COMMENTED OUT FOR NOW (DEEPIMAGE AI)
    # async def swap_face_deepimage(self, target_image_bytes: bytes, source_image_url: str) -> bytes:
    #     """
    #     Swap face using Deep-Image AI API with face swapping
    #     target_image_bytes: The generated story image where we want to swap the face
    #     source_image_url: The Firebase URL of the child's reference image
    #     Returns: The face-swapped image as bytes
    #     """
    #     # Face swap functionality disabled for now - return original image
    #     return target_image_bytes

    async def generate_audio_batch(self, scene_texts: List[Dict], isfemale: bool = True, user_id: str = None, use_cloned_voice: bool = True, prefer_voice_consistency: bool = True, language: str = "english", voice_clone_id: str = None) -> List[bytes]:
        """Generate audio for multiple scenes using Cartesia TTS with ambient sound mixing - OPTIMIZED
        
        Args:
            voice_clone_id: Optional specific voice clone ID to use (overrides auto-detection)
        """
        try:
            # Map language name to code (expanded for more languages)
            language_code_map = {
                "english": "en",
                "spanish": "es",
                "french": "fr",
                "german": "de",
                "hindi": "hi",
                "chinese": "zh",
                "japanese": "ja",
                "korean": "ko",
                "portuguese": "pt",
                "italian": "it",
                "russian": "ru",
                "arabic": "ar",
                "bengali": "bn",
                "tamil": "ta",
                "telugu": "te",
                "gujarati": "gu",
                "punjabi": "pa",
                "urdu": "ur",
                "marathi": "mr"
            }
            language_code = language_code_map.get(language.lower(), "en")
            
            print(f"🎵 Batch audio generation: {len(scene_texts)} scenes in {language} ({language_code})")
            
            # Use Cartesia service for batch audio generation
            cartesia_audio = await self.cartesia_service.generate_speech_batch_cartesia(scene_texts, user_id, use_cloned_voice, language_code, voice_clone_id)
            
            # Check for failures
            failed_indices = [i for i, audio in enumerate(cartesia_audio) if audio is None]
            
            if failed_indices:
                failure_percentage = len(failed_indices) / len(scene_texts) * 100
                
                # OPTIMIZED: Simplified retry strategy for better latency
                # If >50% failed with voice clone, switch ALL to default voice immediately (no retries)
                if use_cloned_voice and failure_percentage > 50:
                    # Major failure - switch to default voice for all scenes
                    final_audio = await self.cartesia_service.generate_speech_batch_cartesia(
                        scene_texts, user_id, use_cloned_voice=False, language=language_code, voice_clone_id=None
                    )
                else:
                    # Minor failures - retry only failed scenes once
                    failed_scenes = [scene_texts[i] for i in failed_indices]
                    retry_audio = await self.cartesia_service.generate_speech_batch_cartesia(
                        failed_scenes, user_id, use_cloned_voice=use_cloned_voice, language=language_code, voice_clone_id=voice_clone_id
                    )
                    
                    final_audio = cartesia_audio.copy()
                    for i, fallback_idx in enumerate(failed_indices):
                        if i < len(retry_audio) and retry_audio[i] is not None:
                            final_audio[fallback_idx] = retry_audio[i]
                    
                    # Check remaining failures - use OpenAI as last resort
                    still_failed = [i for i, audio in enumerate(final_audio) if audio is None]
                    if still_failed:
                        still_failed_scenes = [scene_texts[i] for i in still_failed]
                        openai_fallback = await self.generate_audio_batch_openai(still_failed_scenes, isfemale=isfemale, skip_ambient_mixing=True)
                        
                        for i, scene_idx in enumerate(still_failed):
                            if i < len(openai_fallback) and openai_fallback[i] is not None:
                                final_audio[scene_idx] = openai_fallback[i]
            else:
                final_audio = cartesia_audio
            
            # Add ambient sounds
            mixed_audio = []
            for i, (voice_audio, scene_data) in enumerate(zip(final_audio, scene_texts)):
                if voice_audio and voice_audio != b"audio_placeholder":
                    ambient_keywords = scene_data.get("ambient_sound_keywords", "").strip()
                    
                    if ambient_keywords:
                        try:
                            # Call mixer directly (no async with - service manages its own sessions)
                            mixed_scene_audio = await self.audio_mixer_service.process_scene_audio(
                                narration_audio=voice_audio,
                                ambient_keywords=ambient_keywords,
                                scene_number=i+1
                            )
                            mixed_audio.append(mixed_scene_audio)
                        except Exception:
                            mixed_audio.append(voice_audio)
                    else:
                        mixed_audio.append(voice_audio)
                else:
                    mixed_audio.append(voice_audio)
            
            return mixed_audio
            
        except Exception as e:
            print(f"Audio batch generation failed: {str(e)}")
            return await self.generate_audio_batch_openai(scene_texts, isfemale=isfemale)
    
    async def generate_audio_batch_openai(self, scene_texts: List[Dict], isfemale: bool = True, skip_ambient_mixing: bool = False) -> List[bytes]:
        """Optimized batch audio generation using OpenAI TTS with ambient sound mixing"""
        try:
            voice = "sage" if isfemale else "onyx"
            
            async def generate_single_audio_fast(scene_data):
                text = scene_data['text']
                scene_number = scene_data['scene_number']
                
                try:
                    loop = get_or_create_event_loop()
                    
                    def create_tts_fast():
                        response = self.openai_client.audio.speech.create(
                            model="tts-1-hd",
                            voice=voice,
                            input=text[:1000],
                            response_format="mp3",
                            speed=1.1
                        )
                        return response.content
                    
                    audio_data = await loop.run_in_executor(None, create_tts_fast)
                    return audio_data
                    
                except Exception:
                    return b"audio_placeholder"
            
            # Parallel execution with timeout
            tasks = [generate_single_audio_fast(scene_data) for scene_data in scene_texts]
            audio_results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=60.0
            )
            
            # Process results
            voice_audio_batch = []
            for i, result in enumerate(audio_results):
                if isinstance(result, Exception):
                    voice_audio_batch.append(b"audio_placeholder")
                else:
                    voice_audio_batch.append(result)
            
            # Add ambient sound mixing if not skipped
            if not skip_ambient_mixing:
                mixed_audio_batch = []
                
                for i, (voice_audio, scene_data) in enumerate(zip(voice_audio_batch, scene_texts)):
                    if voice_audio and voice_audio != b"audio_placeholder":
                        ambient_keywords = scene_data.get("ambient_sound_keywords", "").strip()
                        
                        if ambient_keywords:
                            try:
                                # Call mixer directly (no async with - service manages its own sessions)
                                mixed_scene_audio = await self.audio_mixer_service.process_scene_audio(
                                    narration_audio=voice_audio,
                                    ambient_keywords=ambient_keywords,
                                    scene_number=i+1
                                )
                                mixed_audio_batch.append(mixed_scene_audio)
                            except Exception:
                                mixed_audio_batch.append(voice_audio)
                        else:
                            mixed_audio_batch.append(voice_audio)
                    else:
                        mixed_audio_batch.append(voice_audio)
                
                return mixed_audio_batch
            else:
                return voice_audio_batch
                
        except asyncio.TimeoutError:
            return [b"audio_placeholder" for _ in scene_texts]
        except Exception as e:
            print(f"OpenAI batch processing failed: {str(e)}")
            return [b"audio_placeholder" for _ in scene_texts]
    
    async def generate_image_batch(self, visual_prompts: List[Dict], child_image_url: str = None, target_dimensions: tuple = (2048, 2048)) -> List[bytes]:
        """Generate multiple images in parallel using SeeDream 4 at 2K resolution"""
        try:
            # Force square 2K images for consistency and optimal speed
            target_dimensions = (2048, 2048)
            print(f"🖼️ Batch generating {len(visual_prompts)} images at {target_dimensions[0]}x{target_dimensions[1]} with SeeDream 4 2K")
            
            # Use semaphore to respect API rate limits (increased to 5 for better parallelism)
            semaphore = asyncio.Semaphore(5)
            
            async def generate_single_image(prompt_data):
                """Generate image for a single scene"""
                async with semaphore:
                    try:
                        per_scene_refs = prompt_data.get('reference_image_urls')
                        image_data = await self.generate_image(
                            visual_prompt=prompt_data['visual_prompt'],
                            scene_number=prompt_data['scene_number'],
                            child_image_url=child_image_url,
                            target_dimensions=target_dimensions,
                            reference_image_urls=per_scene_refs
                        )
                        print(f"✅ Scene {prompt_data['scene_number']}: {len(image_data)} bytes")
                        return image_data
                        
                    except Exception as e:
                        print(f"❌ Scene {prompt_data['scene_number']} failed: {str(e)}")
                        return self._create_placeholder_image(target_dimensions)
            
            # Generate all images in parallel
            tasks = [generate_single_image(prompt_data) for prompt_data in visual_prompts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle any exceptions
            images = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"❌ Exception in batch task {i}: {str(result)}")
                    images.append(self._create_placeholder_image(target_dimensions))
                else:
                    images.append(result)
            
            # Process results
            images = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"⚠️ Scene {i+1} error, using placeholder")
                    images.append(self._create_placeholder_image(target_dimensions))
                else:
                    images.append(result)
            
            print(f"✅ Batch generation completed: {len(images)} images")
            return images
            
        except Exception as e:
            print(f"❌ Batch generation failed: {str(e)}")
            return [self._create_placeholder_image(target_dimensions) for _ in visual_prompts]
    
    async def generate_audio(self, text: str, scene_number: int, isfemale: bool = True, user_id: str = None, use_cloned_voice: bool = True, ambient_sound_keywords: List[str] = None, language: str = "english", emotion: str = "neutral", voice_clone_id: str = None) -> bytes:
        """Generate audio using Cartesia TTS (primary) with OpenAI fallback
        
        Args:
            text: Text to convert to speech
            scene_number: Scene number for tracking
            isfemale: Gender for fallback voice (if needed)
            user_id: User ID for voice clone lookup
            use_cloned_voice: Whether to use user's cloned voice
            ambient_sound_keywords: Keywords for ambient sound mixing
            language: Language for speech generation
            emotion: Emotion for speech generation
            voice_clone_id: Specific voice clone ID to use (overrides auto-detection)
        """
        print(f"🎵 MediaService.generate_audio called for scene {scene_number} with emotion: {emotion}")
        if voice_clone_id:
            print(f"🎤 Using provided voice_clone_id: {voice_clone_id}")
        if ambient_sound_keywords:
            print(f"🌿 Ambient keywords received: {ambient_sound_keywords}")
        else:
            print(f"🔇 No ambient keywords provided for scene {scene_number}")
        
        # Map language name to code
        language_code_map = {
            "english": "en",
            "spanish": "es",
            "french": "fr",
            "german": "de",
            "hindi": "hi",
            "chinese": "zh",
            "japanese": "ja",
            "korean": "ko",
            "portuguese": "pt",
            "italian": "it",
            "russian": "ru",
            "arabic": "ar"
        }
        language_code = language_code_map.get(language.lower(), "en")
            
        try:
            print(f"🎤 Using Cartesia TTS for scene {scene_number} (language: {language_code}, emotion: {emotion})")
            # Get user's voice ID and generate with Cartesia
            voice_id = await self.cartesia_service.get_user_voice_id(user_id, use_cloned_voice, voice_clone_id) if user_id else voice_clone_id
            audio_bytes = await self.cartesia_service.generate_speech_cartesia(
                text, 
                voice_id, 
                scene_number, 
                language=language_code,
                emotion=emotion
            )
            
            # Mix with ambient sounds if keywords provided
            if ambient_sound_keywords:
                print(f"🎵 Starting ambient sound mixing for scene {scene_number}")
                print(f"🌿 Keywords: {ambient_sound_keywords}")
                try:
                    # Convert list of keywords to string for AudioMixerService
                    if isinstance(ambient_sound_keywords, list):
                        keywords_str = " ".join(ambient_sound_keywords)
                    else:
                        keywords_str = str(ambient_sound_keywords)
                    
                    print(f"🌿 Converting keywords to string: {keywords_str}")
                    
                    # Call mixer directly (no async with - service manages its own sessions)
                    mixed_audio_bytes = await self.audio_mixer_service.process_scene_audio(
                        narration_audio=audio_bytes,
                        ambient_keywords=keywords_str,
                        scene_number=scene_number
                    )
                    print(f"✅ SUCCESS: Ambient mixing completed for scene {scene_number}")
                    print(f"📊 Mixed audio size: {len(mixed_audio_bytes)} bytes (was {len(audio_bytes)} bytes)")
                    return mixed_audio_bytes
                except Exception as ambient_error:
                    print(f"❌ FAILED: Ambient mixing error for scene {scene_number}: {ambient_error}")
                    import traceback
                    traceback.print_exc()
                    print(f"📁 Fallback: Using voice-only audio")
                    return audio_bytes  # Return original audio if mixing fails
            else:
                print(f"🔇 No ambient keywords for scene {scene_number} - using voice-only audio")
            
            print(f"✅ Cartesia voice-only audio ready for scene {scene_number}: {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            print(f"❌ Cartesia TTS failed for scene {scene_number}: {str(e)}")
            print(f"🔄 VOICE CONSISTENCY: Retrying with Cartesia default voice before OpenAI fallback...")
            
            try:
                # First try: Retry with Cartesia default voice to maintain consistency
                default_voice_id = self.cartesia_service.default_voice_id
                audio_bytes = await self.cartesia_service.generate_speech_cartesia(
                    text, 
                    default_voice_id, 
                    scene_number, 
                    language=language_code,
                    emotion=emotion
                )
                
                print(f"✅ Scene {scene_number} recovered with Cartesia default voice - consistency maintained")
                
                # Mix with ambient sounds if keywords provided
                if ambient_sound_keywords:
                    try:
                        if isinstance(ambient_sound_keywords, list):
                            keywords_str = " ".join(ambient_sound_keywords)
                        else:
                            keywords_str = str(ambient_sound_keywords)
                        
                        # Call mixer directly (no async with - service manages its own sessions)
                        mixed_audio_bytes = await self.audio_mixer_service.process_scene_audio(
                            narration_audio=audio_bytes,
                            ambient_keywords=keywords_str,
                            scene_number=scene_number
                        )
                        return mixed_audio_bytes
                    except Exception as ambient_error:
                        print(f"❌ Ambient mixing failed for default voice: {ambient_error}")
                        return audio_bytes
                else:
                    return audio_bytes
                    
            except Exception as default_error:
                print(f"❌ Cartesia default voice also failed for scene {scene_number}: {str(default_error)}")
                print(f"🔄 LAST RESORT: Falling back to OpenAI TTS...")
                return await self.generate_audio_openai(text, scene_number, isfemale=isfemale, ambient_sound_keywords=ambient_sound_keywords)
    
    async def generate_audio_openai(self, text: str, scene_number: int, isfemale: bool = True, ambient_sound_keywords: List[str] = None) -> bytes:
        """Fallback: Generate audio using OpenAI Text-to-Speech"""
        print(f"🎵 MediaService.generate_audio_openai called for scene {scene_number}")
        if ambient_sound_keywords:
            print(f"🌿 OpenAI ambient keywords received: {ambient_sound_keywords}")
        else:
            print(f"🔇 No ambient keywords for OpenAI scene {scene_number}")
            
        try:
            # Voice mapping: Eve (female) = "sage", Adam (male) = "onyx" (OpenAI TTS voices)
            voice = "sage" if isfemale else "onyx"  # Female = sage, Male = onyx
            print(f"🎵 Using OpenAI TTS for scene {scene_number}")
            print(f"🎤 Voice selected: {voice} ({'Eve (female)' if isfemale else 'Adam (male)'})")
            
            response = self.openai_client.audio.speech.create(
                model="tts-1",  # Standard model
                voice=voice,   # Dynamic voice based on isfemale parameter
                input=text,
                response_format="wav"  # Changed from mp3 to wav
            )
            
            # Convert response to bytes
            audio_bytes = b""
            for chunk in response.iter_bytes():
                audio_bytes += chunk
                
            print(f"✅ OpenAI audio generated for scene {scene_number}: {len(audio_bytes)} bytes")
            
            # Mix with ambient sounds if keywords provided
            if ambient_sound_keywords and ambient_sound_keywords:
                print(f"🎵 OpenAI TTS: Starting ambient sound processing for scene {scene_number}")
                print(f"🌿 Ambient keywords: {ambient_sound_keywords}")
                try:
                    # Convert list of keywords to string for AudioMixerService
                    if isinstance(ambient_sound_keywords, list):
                        keywords_str = " ".join(ambient_sound_keywords)
                    else:
                        keywords_str = str(ambient_sound_keywords)
                    
                    print(f"🌿 Converting keywords to string: {keywords_str}")
                    
                    # Call mixer directly (no async with - service manages its own sessions)
                    mixed_audio_bytes = await self.audio_mixer_service.process_scene_audio(
                        narration_audio=audio_bytes,
                        ambient_keywords=keywords_str,
                        scene_number=scene_number
                    )
                    print(f"✅ SUCCESS: OpenAI ambient mixing completed for scene {scene_number}")
                    print(f"🌐 Mixed audio ready for web delivery: {len(mixed_audio_bytes)} bytes (was {len(audio_bytes)} bytes)")
                    return mixed_audio_bytes
                except Exception as ambient_error:
                    print(f"❌ FAILED: OpenAI ambient mixing error for scene {scene_number}: {ambient_error}")
                    import traceback
                    traceback.print_exc()
                    print(f"📁 Fallback: Using voice-only audio")
                    # Fall through to return original audio
            else:
                print(f"🔇 No ambient keywords for OpenAI scene {scene_number} - using voice-only audio")
            
            # For web delivery, skip ESP32 normalization to preserve quality for Opus encoding
            # The storage service will handle Opus encoding and optimization
            print(f"🌐 Audio ready for web delivery processing: {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            print(f"❌ OpenAI TTS error for scene {scene_number}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Audio generation failed for scene {scene_number}: {str(e)}"
            )
    

    


    async def generate_image(self, visual_prompt: str, scene_number: int, child_image_url: str = None, target_dimensions: tuple = (2048, 2048), reference_image_urls: List[str] = None, child_gender: str = None, reference_images_metadata: List[Dict[str, Any]] = None, art_style_hint: str = None) -> bytes:
        """Generate image using SeeDream 4 via Replicate at 2K resolution (optimized for speed/quality balance)"""
        print(f"🔍 MediaService.generate_image called for scene {scene_number}")
        print(f"   - child_image_url: {child_image_url[:80] if child_image_url else 'None'}...")
        print(f"   - reference_image_urls: {reference_image_urls}")
        print(f"   - child_gender: {child_gender}")
        print(f"   - reference_images_metadata: {len(reference_images_metadata) if reference_images_metadata else 0} items")
        print(f"   - art_style_hint: {art_style_hint}")
        try:
            # Use 2K (2048x2048) for optimal speed/quality balance - 4K is too slow for story generation
            target_dimensions = (2048, 2048)
            # Use SeeDream 4
            print(f"🎨 Attempting SeeDream 4 2K for scene {scene_number}")
            return await self.generate_image_seedream(visual_prompt, scene_number, child_image_url, target_dimensions, reference_image_urls, child_gender, reference_images_metadata, art_style_hint)
        except Exception as e:
            print(f"❌ SeeDream 4 failed for scene {scene_number}: {str(e)}")
            print(f"🔄 Creating placeholder image as fallback...")
            return self._create_placeholder_image(target_dimensions)
    
    def _inject_character_metadata_in_prompt(self, visual_prompt: str, reference_images_metadata: List[Dict[str, Any]]) -> str:
        """Detect character names in visual prompt and inject age/gender from reference metadata"""
        if not reference_images_metadata:
            return visual_prompt
        
        enhanced_prompt = visual_prompt
        from app.services.content.story_service import StoryService
        
        # Create temporary service instance just for accessing _get_character_defaults
        # (This is a utility function, so we don't need full initialization)
        class CharacterDefaults:
            @staticmethod
            def get_defaults(relation: str) -> Dict[str, Any]:
                relation_lower = relation.lower() if relation else ""
                if 'grandfather' in relation_lower or 'grandpa' in relation_lower:
                    return {'gender': 'man', 'age': 65}
                elif 'grandmother' in relation_lower or 'grandma' in relation_lower:
                    return {'gender': 'woman', 'age': 65}
                elif 'father' in relation_lower or 'dad' in relation_lower:
                    return {'gender': 'man', 'age': 40}
                elif 'mother' in relation_lower or 'mom' in relation_lower:
                    return {'gender': 'woman', 'age': 40}
                elif 'parent' in relation_lower:
                    return {'gender': 'woman', 'age': 40}
                elif 'brother' in relation_lower:
                    return {'gender': 'boy', 'age': 8}
                elif 'sister' in relation_lower:
                    return {'gender': 'girl', 'age': 8}
                elif 'child' in relation_lower or 'son' in relation_lower or 'daughter' in relation_lower:
                    if 'son' in relation_lower or 'boy' in relation_lower:
                        return {'gender': 'boy', 'age': 5}
                    elif 'daughter' in relation_lower or 'girl' in relation_lower:
                        return {'gender': 'girl', 'age': 5}
                    else:
                        return {'gender': 'girl', 'age': 5}
                else:
                    return {'gender': 'girl', 'age': 5}
        
        # Check each reference character
        for ref in reference_images_metadata:
            person_name = ref.get('person_name', '')
            relation = ref.get('relation', '')
            
            if not person_name:
                continue
            
            # Check if character name appears in prompt (case-insensitive)
            import re
            name_pattern = re.compile(rf'\b{re.escape(person_name)}\b', re.IGNORECASE)
            
            if name_pattern.search(visual_prompt):
                defaults = CharacterDefaults.get_defaults(relation)
                gender = defaults['gender']
                age = defaults['age']
                
                # Check if name already has age/gender context (more comprehensive patterns)
                # Patterns like: "X year old [gender]" or "[gender], a X year old"
                age_gender_patterns = [
                    rf'{re.escape(person_name)},\s*a\s*\d+\s*year\s*old\s*(boy|girl|man|woman)',  # "Millie, a 5 year old girl"
                    rf'a\s*\d+\s*year\s*old\s*(boy|girl|man|woman)\s*(?:named\s*)?{re.escape(person_name)}',  # "a 5 year old girl named Millie"
                    rf'\d+\s*year\s*old\s*(boy|girl|man|woman)\s*{re.escape(person_name)}',  # "5 year old girl Millie"
                ]
                
                has_age_gender = any(re.search(pattern, visual_prompt, re.IGNORECASE) for pattern in age_gender_patterns)
                
                if not has_age_gender:
                    # Name appears without proper age/gender - enhance it
                    replacement = f"{person_name}, a {age} year old {gender}"
                    enhanced_prompt = name_pattern.sub(replacement, enhanced_prompt, count=1)
                    print(f"✨ Enhanced prompt: '{person_name}' → '{person_name}, a {age} year old {gender}'")
        
        return enhanced_prompt
    
    async def generate_image_seedream(self, visual_prompt: str, scene_number: int, child_image_url: str = None, target_dimensions: tuple = (2048, 2048), reference_image_urls: List[str] = None, child_gender: str = None, reference_images_metadata: List[Dict[str, Any]] = None, art_style_hint: str = None) -> bytes:
        """Generate image using SeeDream 4 hosted on Replicate with 2K resolution (optimized balance)"""
        print(f"🎨 Using SeeDream 4 2K for scene {scene_number}")
        print(f"🔍 Debug - reference_image_urls parameter: {reference_image_urls}")
        print(f"🔍 Debug - reference_image_urls type: {type(reference_image_urls)}")
        print(f"🔍 Debug - reference_image_urls is None: {reference_image_urls is None}")
        print(f"🔍 Debug - reference_image_urls is empty: {reference_image_urls == []}")
        print(f"🔍 Debug - child_gender: {child_gender}")
        print(f"🔍 Debug - reference_images_metadata: {len(reference_images_metadata) if reference_images_metadata else 0} items")
        
        # Extract base prompt
        base_prompt = visual_prompt
        art_style_hint = None
        try:
            if isinstance(visual_prompt, dict):
                base_prompt = visual_prompt.get('visual_prompt', '')
                art_style_hint = visual_prompt.get('art_style')
            elif isinstance(visual_prompt, str):
                pass
        except Exception:
            base_prompt = str(visual_prompt)
        
        # INJECT CHARACTER METADATA: Detect character names and enhance with age/gender
        if reference_images_metadata:
            base_prompt = self._inject_character_metadata_in_prompt(base_prompt, reference_images_metadata)
        
        # EXPLICITLY ADD ART STYLE to the base prompt (don't rely on OpenAI including it)
        if art_style_hint:
            art_style_descriptions = {
                "disney": "Disney animation style",
                "ghibli": "Studio Ghibli style",
                "pixar": "Pixar 3D animation style",
                "watercolors": "watercolor painting style"
            }
            style_description = art_style_descriptions.get(art_style_hint.lower(), art_style_hint)
            # Append art style instruction to ensure it's always in the prompt
            base_prompt = f"{base_prompt} Image should be {style_description}."
            print(f"✅ Explicitly added art style to prompt: '{style_description}'")

        # Add gender-specific instruction if gender is provided
        gender_instruction = ""
        if child_gender:
            if child_gender.lower() in ['boy', 'male']:
                gender_instruction = " CRITICAL: The child character MUST be a BOY (male child) with masculine features in ALL images. DO NOT depict as a girl. "
            elif child_gender.lower() in ['girl', 'female']:
                gender_instruction = " CRITICAL: The child character MUST be a GIRL (female child) with feminine features in ALL images. DO NOT depict as a boy. "
        
        # Reference image instructions (applied to all images with references)
        # Map art style to proper image generation style modifier
        art_style_map = {
            "disney": "Disney animation style",
            "ghibli": "Studio Ghibli style",
            "pixar": "Pixar 3D animation style",
            "watercolors": "watercolor painting style"
        }
        
        # Get the full style description or use the hint as-is if not in map
        if art_style_hint:
            full_style = art_style_map.get(art_style_hint.lower(), art_style_hint)
            style_text = full_style
        else:
            style_text = "children's illustration"
        
        reference_image_instructions = f"""

Analyze the provided reference image carefully and recreate the person with a face that closely resembles the sample image. Maintain all key physical attributes — including the same skin tone, eye color, hair color, hairstyle, facial structure, and overall appearance.

FACE MATCHING:
•⁠ ⁠The reference images show the EXACT face(s) that must appear in this scene
•⁠ ⁠Copy the facial features, structure, and likeness from the reference images precisely
•⁠ ⁠The face in the reference image is THE TRUTH - match it exactly
•⁠ ⁠Do NOT invent new facial features - use ONLY what you see in the reference
•⁠ ⁠Ensure the person remains easily recognizable as the same individual from the reference image

PHYSICAL ATTRIBUTES FROM REFERENCE:
•⁠ ⁠Skin tone: Copy the exact skin tone from the reference image
•⁠ ⁠Hair: Match color, texture, style, and length from reference
•⁠ ⁠Eyes: Match eye color and shape from reference
•⁠ ⁠Face structure: Copy cheekbones, nose, jawline, face shape
•⁠ ⁠All physical characteristics must match the reference exactly

SCENE ADAPTATION:
•⁠ ⁠Keep the SAME FACE from reference in different poses/angles as needed
•⁠ ⁠You may adjust the pose, body position, and facial expression to make the final image more engaging, friendly, and appealing to young children
•⁠ ⁠Change clothing, background, and setting as described in text prompt
•⁠ ⁠But NEVER change the face, skin tone, hair, or core physical features

STYLE AND PRESENTATION:
•⁠ ⁠The composition, colors, and lighting should all contribute to a cheerful, and visually inviting look suitable for children's content
•⁠ ⁠Child-safe and emotionally positive presentation
•⁠ ⁠Image should be {style_text}"""
        
        # Compose enhanced prompt with instructions
        # Get the full style description for prefix
        if art_style_hint:
            full_style = art_style_map.get(art_style_hint.lower(), art_style_hint)
            style_prefix = f"{full_style}, "
            print(f"🎨 Art Style Applied: {art_style_hint} -> {full_style}")
        else:
            style_prefix = ""
            print(f"⚠️ No art style provided - using default")
        
        # Add explicit reference image instruction if images are provided
        reference_instruction = ""
        if reference_image_urls and len(reference_image_urls) > 0:
            reference_instruction = f" ⚠️ {len(reference_image_urls)} REFERENCE IMAGE(S) PROVIDED - USE THESE FACES AS PRIMARY VISUAL SOURCE! "
        
        enhanced_prompt = f"Children's book illustration, {style_prefix}colorful and friendly, high quality digital art. {base_prompt}{gender_instruction}{reference_instruction}{reference_image_instructions}"
        
        # Determine aspect ratio: 16:9 for thumbnails (scene 0), 1:1 for regular scenes
        aspect_ratio = "16:9" if scene_number == 0 else "1:1"
        
        # Prepare input parameters - use 2K for speed/quality balance
        # CRITICAL: Disable prompt enhancement when reference images exist to prevent SeeDream from rewriting the prompt
        has_references = bool(reference_image_urls and len(reference_image_urls) > 0)
        input_params = {
            "prompt": enhanced_prompt,
            "aspect_ratio": aspect_ratio,
            "size": "2K",
            "enhance_prompt": not has_references
        }
        
        # Build image_input array combining child_image_url and reference_image_urls
        image_inputs = []
        if child_image_url:
            image_inputs.append(child_image_url)
        if reference_image_urls:
            image_inputs.extend(reference_image_urls)
        if image_inputs:
            input_params["image_input"] = image_inputs
        
        # Log comprehensive API call details for debugging
        print(f"\n{'='*100}")
        print(f"🎨 SEEDREAM 4 API CALL - Scene {scene_number} {'(THUMBNAIL)' if scene_number == 0 else ''}")
        print(f"{'='*100}")
        print(f"\n📐 Configuration:")
        print(f"  • Aspect Ratio: {aspect_ratio}")
        print(f"  • Size: 2K (2048px)")
        print(f"  • Prompt Enhancement: {'DISABLED' if has_references else 'ENABLED'} {('(references present)' if has_references else '')}")
        if child_gender:
            print(f"  • Gender Enforcement: {child_gender.upper()}")
        
        if image_inputs:
            print(f"\n📸 Reference Images ({len(image_inputs)} total):")
            for idx, img_url in enumerate(image_inputs, 1):
                img_type = "Child Profile" if idx == 1 and child_image_url else f"Reference {idx - (1 if child_image_url else 0)}"
                print(f"  [{idx}] {img_type}: {img_url}")
        
        print(f"\n📝 Full Prompt with Instructions:")
        print(f"{enhanced_prompt}")
        print(f"\n{'='*100}\n")
        
        # SeeDream 4 API call - Run in executor to avoid blocking event loop
        print(f"⏱️ Calling SeeDream 4 API for scene {scene_number}...")
        loop = asyncio.get_running_loop()
        
        # Wrap the blocking replicate.run call with timeout (increased for reference images)
        try:
            output = await asyncio.wait_for(
                loop.run_in_executor(
                    None,  # Use default ThreadPoolExecutor
                    lambda: replicate.run(
                        "bytedance/seedream-4",
                        input=input_params
                    )
                ),
                timeout=180.0  # 3 minute timeout (increased for reference image processing)
            )
        except asyncio.TimeoutError:
            print(f"⚠️ SeeDream 4 API call timed out after 180s for scene {scene_number}")
            raise Exception(f"SeeDream 4 API call timed out after 180s")
        
        # Output is a list of URLs
        if not output or len(output) == 0:
            raise Exception("SeeDream 4 returned no images")
        
        # Get the first output item and normalize it to either a URL or raw bytes
        image_output = output[0]

        # Normalize output: may be a URL string, a replicate.helpers.FileOutput, dict, or bytes
        normalized = self._normalize_replicate_output(image_output)
        if normalized is None:
            raise Exception("SeeDream 4 returned an unsupported output type")

        # If normalized returned raw bytes, use them directly; else fetch the URL
        if isinstance(normalized, (bytes, bytearray)):
            image_data = bytes(normalized)
            print(f"✅ Obtained image bytes directly from Replicate output: {len(image_data)} bytes")
        else:
            image_url = normalized
            print(f"🔗 SeeDream 4 image URL: {image_url}")
            print(f"📥 Downloading image from Replicate CDN...")
            response = await self.http_client.get(image_url)
            response.raise_for_status()
            image_data = response.content
            print(f"✅ Downloaded SeeDream 4 2K image: {len(image_data)} bytes")
        
        # Load image to check dimensions
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        actual_aspect_ratio = width / height
        
        print(f"\n{'='*80}")
        print(f"📏 IMAGE DIMENSIONS - Scene {scene_number}")
        print(f"{'='*80}")
        print(f"  Original Width:  {width}px")
        print(f"  Original Height: {height}px")
        print(f"  Aspect Ratio: {actual_aspect_ratio:.4f}")
        
        # Verify aspect ratio matches expectation
        if scene_number == 0:
            expected_ratio = 16/9
            print(f"  Expected (16:9): {expected_ratio:.4f}")
            if abs(actual_aspect_ratio - expected_ratio) < 0.01:
                print(f"  ✅ Correct 16:9 aspect ratio!")
            else:
                print(f"  ⚠️ WARNING: Not 16:9! Difference: {abs(actual_aspect_ratio - expected_ratio):.4f}")
        else:
            expected_ratio = 1.0
            print(f"  Expected (1:1): {expected_ratio:.4f}")
            if abs(actual_aspect_ratio - expected_ratio) < 0.01:
                print(f"  ✅ Correct 1:1 aspect ratio!")
            else:
                print(f"  ⚠️ WARNING: Not 1:1! Difference: {abs(actual_aspect_ratio - expected_ratio):.4f}")
        print(f"{'='*80}\n")
        
        # DO NOT RESIZE - Keep the aspect ratio from the API!
        # The API already generated the image at the correct aspect ratio
        # Resizing would distort the image
        print(f"✅ Keeping original aspect ratio from API")
        
        # Convert to JPEG with optimized quality for 2K
        output_buffer = io.BytesIO()
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        image.save(output_buffer, format='JPEG', quality=95, optimize=True)
        final_image_data = output_buffer.getvalue()
        
        print(f"✅ Scene {scene_number} 2K image: {len(final_image_data)} bytes ({target_dimensions[0]}x{target_dimensions[1]})")
        return final_image_data
    
    async def generate_image_openai(self, visual_prompt: str, scene_number: int, child_image_url: str = None, target_dimensions: tuple = (2048, 2048)) -> bytes:
        """DEPRECATED: Old OpenAI image generation - kept for compatibility"""
        print(f"⚠️ OpenAI image generation is deprecated, using SeeDream 4 2K instead")
        return await self.generate_image_seedream(visual_prompt, scene_number, child_image_url, target_dimensions)
    
    def _sanitize_visual_prompt(self, prompt: str) -> str:
        """Apply child safety filters to visual prompts"""
        # Remove potentially inappropriate keywords
        inappropriate_words = [
            'scary', 'dark', 'violent', 'weapon', 'gun', 'knife', 'blood', 'death',
            'monster', 'evil', 'demon', 'horror', 'nightmare', 'spooky', 'creepy',
            'sad', 'crying', 'angry', 'mean', 'dangerous', 'hurt', 'pain'
        ]
        
        safe_prompt = prompt.lower()
        for word in inappropriate_words:
            safe_prompt = safe_prompt.replace(word, '')
        
        # Add positive descriptors
        safe_descriptors = [
            'happy', 'colorful', 'bright', 'cheerful', 'friendly', 'smiling', 
            'magical', 'wonderful', 'beautiful', 'peaceful', 'joyful'
        ]
        
        # Clean up extra spaces
        safe_prompt = ' '.join(safe_prompt.split())
        
        # Add a random positive descriptor if the prompt seems too plain
        if len(safe_prompt.split()) < 5:
            import random
            safe_prompt += f" {random.choice(safe_descriptors)}"
        
        return safe_prompt
    
    async def generate_story_thumbnail(self, thumbnail_prompt: str, story_id: str, child_image_url: str = None, reference_image_urls: List[str] = None, child_gender: str = None, reference_images_metadata: List[Dict[str, Any]] = None, art_style: str = "disney") -> bytes:
        """
        Generate a 16:9 widescreen thumbnail image for the story using SeeDream 4 at 2K
        
        Args:
            thumbnail_prompt: Description for the thumbnail image
            story_id: Story ID for logging
            child_image_url: Optional child image for personalization
            reference_image_urls: Optional reference image URLs
            child_gender: Optional child gender
            reference_images_metadata: Optional metadata for character name detection
            art_style: Art style for the thumbnail (disney, ghibli, pixar, watercolors)
            
        Returns:
            thumbnail image bytes in 16:9 format at 2K resolution (optimal for thumbnails)
        """
        try:
            # Use 16:9 aspect ratio at 2K resolution (1920x1080)
            thumbnail_dimensions = (1920, 1080)

            print(f"🖼️ Generating 16:9 widescreen story thumbnail for story {story_id} with SeeDream 4")
            print(f"📐 Thumbnail dimensions: {thumbnail_dimensions[0]}x{thumbnail_dimensions[1]} (16:9 aspect ratio)")
            print(f"🎨 Thumbnail art style: {art_style}")

            # Map art style to description
            art_style_map = {
                "disney": "Disney animation style",
                "ghibli": "Studio Ghibli style",
                "pixar": "Pixar 3D animation style",
                "watercolors": "watercolor painting style"
            }
            style_desc = art_style_map.get(art_style.lower(), art_style)

            # Enhance the prompt for thumbnail generation with art style
            enhanced_prompt = {
                "visual_prompt": f"Widescreen 16:9 thumbnail cover image, children's book illustration, {style_desc}, colorful and engaging, digital illustration, soft shading, semi-realistic: {thumbnail_prompt}",
                "art_style": art_style
            }

            print(f"🖼️ Generating thumbnail | References: {len(reference_image_urls) if reference_image_urls else 0} | Gender: {child_gender or 'None'}")

            # Generate thumbnail using SeeDream 4 with same references as story scenes for consistency
            thumbnail_data = await self.generate_image(
                visual_prompt=enhanced_prompt,
                scene_number=0,  # Use 0 to indicate thumbnail
                child_image_url=child_image_url,
                target_dimensions=thumbnail_dimensions,
                reference_image_urls=reference_image_urls,
                child_gender=child_gender,
                reference_images_metadata=reference_images_metadata
            )

            print(f"✅ Story thumbnail generated: {len(thumbnail_data)} bytes ({thumbnail_dimensions[0]}x{thumbnail_dimensions[1]}, 16:9)")
            return thumbnail_data
            
        except Exception as e:
            print(f"❌ Thumbnail generation failed for story {story_id}: {str(e)}")
            # Create a placeholder thumbnail
            return self._create_placeholder_thumbnail(thumbnail_dimensions)
    
    def _create_placeholder_thumbnail(self, dimensions: tuple = (1920, 1080)) -> bytes:
        """Create a placeholder thumbnail image in 16:9 format"""
        try:
            width, height = dimensions
            print(f"🖼️ Creating placeholder thumbnail: {width}x{height} (16:9)")
            
            # Create thumbnail with gradient background
            image = Image.new('RGB', (width, height), color='#4a90e2')  # Nice blue color
            
            # Add text overlay
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(image)
                
                # Add centered text
                title_text = "Story Thumbnail"
                subtitle_text = "Generating..."
                
                # Calculate positions for centered text
                title_bbox = draw.textbbox((0, 0), title_text)
                title_width = title_bbox[2] - title_bbox[0]
                title_height = title_bbox[3] - title_bbox[1]
                
                subtitle_bbox = draw.textbbox((0, 0), subtitle_text)
                subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
                
                title_x = (width - title_width) // 2
                title_y = (height - title_height) // 2 - 20
                
                subtitle_x = (width - subtitle_width) // 2
                subtitle_y = title_y + title_height + 10
                
                draw.text((title_x, title_y), title_text, fill='white')
                draw.text((subtitle_x, subtitle_y), subtitle_text, fill='white')
                
            except Exception:
                pass  # Skip text if font issues
            
            # Convert to bytes
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='JPEG', quality=85)
            return output_buffer.getvalue()
            
        except Exception as e:
            print(f"⚠️ Error creating placeholder thumbnail: {e}")
            # Return minimal valid JPEG
            width, height = dimensions
            minimal_image = Image.new('RGB', (width, height), color='#f0f0f0')
            buffer = io.BytesIO()
            minimal_image.save(buffer, format='JPEG')
            return buffer.getvalue()

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services"""
        health = {
            "openai_tts": False,
            "gpt_image_1_mini": False,
            "overall": False
        }
        
        try:
            # Quick OpenAI TTS test
            test_response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice="sage",
                input="test",
                response_format="mp3"
            )
            health["openai_tts"] = len(test_response.content) > 0
            
            # GPT-Image-1-Mini test (quick prompt)
            try:
                test_image_response = self.openai_client.images.generate(
                    model="gpt-image-1-mini",
                    prompt="test image",
                    size="1024x1024",
                    quality="high",
                    n=1
                )
                health["gpt_image_1_mini"] = bool(test_image_response.data and test_image_response.data[0].url)
            except:
                health["gpt_image_1_mini"] = False
            
            health["overall"] = health["openai_tts"] and health["gpt_image_1_mini"]
            
        except Exception as e:
            print(f"Health check failed: {str(e)}")
        
        return health