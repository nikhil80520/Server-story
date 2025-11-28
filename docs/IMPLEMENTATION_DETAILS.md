# Implementation Details - Technical Deep Dive

## Table of Contents
1. [Story Generation Pipeline](#story-generation-pipeline)
2. [Queue Management System](#queue-management-system)
3. [Conversational AI (WebRTC)](#conversational-ai-webrtc)
4. [IoT Device Management](#iot-device-management)
5. [Media Processing](#media-processing)
6. [Authentication & Security](#authentication--security)
7. [Performance Optimization](#performance-optimization)
8. [Error Handling & Resilience](#error-handling--resilience)

---

## Story Generation Pipeline

### Architecture Overview

The story generation system uses a **parallel processing pipeline** to generate text, audio, and images concurrently, reducing total generation time from ~3 minutes to ~45 seconds.

```
Story Request
      ↓
┌─────────────────────────┐
│ 1. Request Validation   │
│    • User auth          │
│    • Input sanitization │
│    • Quota check        │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 2. Job Initialization   │
│    • Generate story_id  │
│    • Create Firestore   │
│    • Return 202 Accepted│
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 3. Queue System         │
│    • Priority assignment│
│    • Worker allocation  │
│    • Heartbeat start    │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 4. Text Generation      │
│    • GPT-4 prompt       │
│    • Scene structure    │
│    • Character creation │
└──────────┬──────────────┘
           ↓
    ┌──────┴──────┐
    ↓             ↓
┌────────┐    ┌─────────┐
│ Audio  │    │ Images  │
│ (TTS)  │    │ (AI Art)│
└───┬────┘    └────┬────┘
    │              │
    └──────┬───────┘
           ↓
┌─────────────────────────┐
│ 5. Storage Upload       │
│    • Firebase Storage   │
│    • URL generation     │
│    • CDN distribution   │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 6. Manifest Creation    │
│    • Scene metadata     │
│    • URLs & durations   │
│    • Firestore update   │
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│ 7. WebSocket Notify     │
│    • Progress updates   │
│    • Completion event   │
│    • Error handling     │
└─────────────────────────┘
```

### Implementation Details

#### 1. Request Validation (`app/routers/stories.py`)

```python
@router.post("/generate")
async def generate_story(
    request: StoryGenerationRequest,
    user_id: str = Depends(get_current_user)
):
    # Input sanitization
    sanitized_prompt = sanitize_input(request.user_prompt)
    
    # Quota validation
    user_usage = await check_user_quota(user_id)
    if user_usage >= MAX_STORIES_PER_MONTH:
        raise HTTPException(403, "Monthly quota exceeded")
    
    # Content safety check
    if await is_inappropriate_content(sanitized_prompt):
        raise HTTPException(400, "Inappropriate content detected")
    
    # Generate unique story ID
    story_id = str(uuid.uuid4())
    
    # Initialize Firestore document
    await db.collection("stories").document(story_id).set({
        "user_id": user_id,
        "status": "queued",
        "created_at": firestore.SERVER_TIMESTAMP,
        "parameters": request.dict()
    })
    
    # Add to queue
    job_id = await queue_story_generation(story_id, request)
    
    return {
        "success": True,
        "story_id": story_id,
        "job_id": job_id,
        "status": "processing"
    }
```

#### 2. Parallel Story Service (`app/services/parallel_story_service.py`)

**Key Innovation**: Uses `asyncio.gather()` to generate audio and images in parallel after text generation completes.

```python
class ParallelStoryService:
    async def generate_story(self, params: StoryGenerationRequest) -> StoryManifest:
        story_id = params.story_id
        
        # Phase 1: Text Generation (sequential, required first)
        start_time = time.time()
        await self._update_progress(story_id, 10, "Generating story text...")
        
        story_structure = await self._generate_story_text(params)
        
        # Phase 2: Parallel Media Generation
        await self._update_progress(story_id, 30, "Generating audio and images...")
        
        # Create tasks for parallel execution
        audio_tasks = [
            self._generate_audio(scene, params.voice_option, params.voice_clone_id)
            for scene in story_structure.scenes
        ]
        
        image_tasks = [
            self._generate_image(scene, params.art_style, params.reference_images)
            for scene in story_structure.scenes
        ]
        
        # Execute in parallel with progress tracking
        audio_results, image_results = await asyncio.gather(
            self._execute_with_progress(audio_tasks, story_id, 30, 60),
            self._execute_with_progress(image_tasks, story_id, 60, 90)
        )
        
        # Phase 3: Upload and finalize
        await self._update_progress(story_id, 90, "Uploading media files...")
        manifest = await self._create_manifest(
            story_structure, audio_results, image_results
        )
        
        # Phase 4: Store in Firestore
        await self._save_manifest(story_id, manifest)
        await self._update_progress(story_id, 100, "Story complete!")
        
        total_time = time.time() - start_time
        logger.info(f"Story {story_id} generated in {total_time:.2f}s")
        
        return manifest
    
    async def _execute_with_progress(
        self, 
        tasks: List[Coroutine], 
        story_id: str,
        start_progress: int,
        end_progress: int
    ):
        """Execute tasks and update progress incrementally"""
        results = []
        total = len(tasks)
        progress_range = end_progress - start_progress
        
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            results.append(result)
            
            # Update progress
            current_progress = start_progress + int((i + 1) / total * progress_range)
            await self._update_progress(
                story_id, 
                current_progress, 
                f"Processing {i+1}/{total}..."
            )
        
        return results
```

#### 3. Text Generation with GPT-4

**Prompt Engineering**: Carefully crafted system prompts ensure appropriate, engaging content.

```python
async def _generate_story_text(self, params: StoryGenerationRequest) -> StoryStructure:
    system_prompt = f"""You are an expert children's storyteller creating personalized stories.

Story Requirements:
- Target audience: {params.child_age} year old child named {params.child_name}
- Theme: {params.user_prompt}
- Moral lessons: {', '.join(params.morals)}
- Length: {params.story_length} ({self._get_scene_count(params.story_length)} scenes)
- Style: Age-appropriate, engaging, educational

Structure each scene with:
1. Scene number
2. Narrative text (2-3 paragraphs)
3. Dialogue (if applicable)
4. Visual description (for image generation)
5. Ambient keywords (for audio)

Important:
- Use the child's name frequently
- Keep language appropriate for age
- Ensure positive, educational content
- Include moments of conflict and resolution
- End with satisfying conclusion and moral lesson"""

    user_prompt = f"""Create a {params.story_length} story about {params.user_prompt} 
for {params.child_name}, a {params.child_age} year old {params.child_gender or 'child'}.
Incorporate these moral lessons: {', '.join(params.morals)}"""

    response = await self.openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.8,  # Creative but controlled
        max_tokens=3000,
        response_format={"type": "json_object"}  # Structured output
    )
    
    story_data = json.loads(response.choices[0].message.content)
    return StoryStructure.parse_obj(story_data)
```

#### 4. Audio Generation Strategy

**Two-Tier System**:
- **Cartesia Sonic**: Ultra-low latency for conversational AI
- **ElevenLabs**: High quality for story narration

```python
async def _generate_audio(
    self, 
    scene: Scene, 
    voice_option: str,
    voice_clone_id: Optional[str] = None
) -> AudioResult:
    """Generate audio with fallback strategy"""
    
    # Try Cartesia first (faster, lower cost)
    try:
        audio_data = await self.cartesia_service.generate_speech(
            text=scene.text,
            voice_id=voice_option,
            speed=1.0,
            emotion="storytelling"
        )
        
        return AudioResult(
            audio_bytes=audio_data,
            duration=self._calculate_duration(audio_data),
            provider="cartesia"
        )
    
    except CartesiaError as e:
        logger.warning(f"Cartesia failed, falling back to ElevenLabs: {e}")
        
        # Fallback to ElevenLabs
        audio_data = await self.elevenlabs_service.generate_speech(
            text=scene.text,
            voice_id=voice_clone_id or self._get_elevenlabs_voice(voice_option),
            stability=0.5,
            similarity_boost=0.8
        )
        
        return AudioResult(
            audio_bytes=audio_data,
            duration=self._calculate_duration(audio_data),
            provider="elevenlabs"
        )

async def _generate_audio_with_ambient(
    self, 
    scene: Scene
) -> AudioResult:
    """Generate narration + ambient sounds (future feature)"""
    
    # Generate narration
    narration = await self._generate_audio(scene, ...)
    
    # Generate ambient sounds based on keywords
    ambient_sounds = []
    for keyword in scene.ambient_keywords:
        sound = await self.ambient_service.get_sound(keyword)
        ambient_sounds.append(sound)
    
    # Mix narration with ambient
    mixed_audio = await self._mix_audio(
        narration, 
        ambient_sounds,
        narration_volume=1.0,
        ambient_volume=0.3
    )
    
    return mixed_audio
```

#### 5. Image Generation with SeeDream

**Character Consistency**: Maintains visual consistency across scenes using reference images.

```python
async def _generate_image(
    self, 
    scene: Scene, 
    art_style: str,
    reference_images: List[str] = None
) -> ImageResult:
    """Generate scene image with style consistency"""
    
    # Construct detailed image prompt
    image_prompt = self._build_image_prompt(scene, art_style)
    
    # Add reference images for character consistency
    if reference_images:
        image_prompt += f"\nReference style from: {reference_images[0]}"
    
    try:
        image_data = await self.seedream_service.generate_image(
            prompt=image_prompt,
            style=art_style,
            width=1024,
            height=1024,
            quality="high",
            reference_images=reference_images
        )
        
        # Post-process: resize for different devices
        optimized_images = await self._optimize_image(image_data)
        
        return ImageResult(
            image_bytes=optimized_images['original'],
            thumbnail_bytes=optimized_images['thumbnail'],
            width=1024,
            height=1024
        )
    
    except SeeDreamError as e:
        logger.error(f"Image generation failed: {e}")
        # Use fallback placeholder image
        return await self._get_placeholder_image()

def _build_image_prompt(self, scene: Scene, art_style: str) -> str:
    """Construct detailed image generation prompt"""
    
    style_modifiers = {
        "magical": "whimsical, dreamy, sparkles, fantasy lighting",
        "realistic": "photorealistic, detailed, natural lighting",
        "cartoon": "animated, colorful, expressive, child-friendly",
        "watercolor": "soft, painted, artistic, gentle colors"
    }
    
    prompt = f"""
{scene.visual_description}

Art style: {art_style} - {style_modifiers.get(art_style, '')}
Composition: Well-balanced, child-appropriate, engaging
Lighting: {scene.time_of_day or 'natural'}
Mood: {scene.mood or 'happy and adventurous'}
Characters: {scene.characters}
Setting: {scene.setting}

Quality: High detail, vibrant colors, sharp focus
Negative prompt: scary, dark, violent, inappropriate
"""
    return prompt.strip()
```

#### 6. Storage Upload Strategy

**Parallel Uploads**: All media files uploaded concurrently to minimize latency.

```python
async def _upload_media_files(
    self, 
    story_id: str,
    audio_results: List[AudioResult],
    image_results: List[ImageResult]
) -> List[MediaURLs]:
    """Upload all media files in parallel"""
    
    upload_tasks = []
    
    # Create upload tasks for audio
    for i, audio in enumerate(audio_results):
        task = self.storage_service.upload_file(
            file_bytes=audio.audio_bytes,
            path=f"stories/{story_id}/audio/scene_{i+1}.wav",
            content_type="audio/wav"
        )
        upload_tasks.append(("audio", i, task))
    
    # Create upload tasks for images
    for i, image in enumerate(image_results):
        # Upload original
        task_original = self.storage_service.upload_file(
            file_bytes=image.image_bytes,
            path=f"stories/{story_id}/images/scene_{i+1}.png",
            content_type="image/png"
        )
        upload_tasks.append(("image", i, task_original))
        
        # Upload thumbnail
        task_thumb = self.storage_service.upload_file(
            file_bytes=image.thumbnail_bytes,
            path=f"stories/{story_id}/images/scene_{i+1}_thumb.png",
            content_type="image/png"
        )
        upload_tasks.append(("thumbnail", i, task_thumb))
    
    # Execute all uploads in parallel
    results = await asyncio.gather(*[task for _, _, task in upload_tasks])
    
    # Organize results by scene
    media_urls = [MediaURLs() for _ in audio_results]
    
    for (media_type, scene_idx, _), url in zip(upload_tasks, results):
        if media_type == "audio":
            media_urls[scene_idx].audio_url = url
        elif media_type == "image":
            media_urls[scene_idx].image_url = url
        elif media_type == "thumbnail":
            media_urls[scene_idx].thumbnail_url = url
    
    return media_urls
```

---

## Queue Management System

### Architecture

The queue system provides **priority-based job scheduling** with **automatic worker failover** and **exponential backoff** for retries.

```
┌────────────────────────────────────────────────┐
│            Queue Manager                        │
│  • Priority queues (high/normal/low)           │
│  • Worker pool management                      │
│  • Job tracking (pending/processing/completed) │
│  • Heartbeat monitoring                        │
└────────────┬───────────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────┐      ┌────▼────┐
│ Worker 1│      │ Worker 2│
│ Idle    │      │ Busy    │
└────┬────┘      └────┬────┘
     │                │
     │          ┌─────▼──────┐
     │          │ Story Job  │
     │          │ (Running)  │
     │          └────────────┘
     │
┌────▼─────────────────────┐
│  Job Lifecycle           │
│  1. Queued               │
│  2. Processing           │
│  3. Completed/Failed     │
│  4. Cleanup              │
└──────────────────────────┘
```

### Implementation

#### 1. Queue Manager (`app/services/enhanced_background_service.py`)

```python
class EnhancedBackgroundService:
    def __init__(self):
        # Priority queues
        self.high_priority_queue = asyncio.PriorityQueue()
        self.normal_priority_queue = asyncio.PriorityQueue()
        self.low_priority_queue = asyncio.PriorityQueue()
        
        # Worker management
        self.workers = []
        self.max_workers = 5
        self.active_jobs = {}
        
        # Heartbeat tracking
        self.job_heartbeats = {}
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [10, 30, 60]  # seconds (exponential)
    
    async def start(self):
        """Initialize workers and monitoring tasks"""
        # Start worker pool
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        
        # Start heartbeat monitor
        asyncio.create_task(self._heartbeat_monitor())
        
        logger.info(f"Started {self.max_workers} workers")
    
    async def add_job(
        self, 
        job_id: str, 
        job_func: Callable,
        priority: str = "normal"
    ) -> str:
        """Add job to appropriate queue"""
        
        job = Job(
            job_id=job_id,
            func=job_func,
            priority=priority,
            created_at=time.time(),
            retries=0
        )
        
        # Select queue based on priority
        if priority == "high":
            await self.high_priority_queue.put((0, job))  # Lower number = higher priority
        elif priority == "normal":
            await self.normal_priority_queue.put((1, job))
        else:
            await self.low_priority_queue.put((2, job))
        
        self.job_heartbeats[job_id] = time.time()
        
        logger.info(f"Job {job_id} added to {priority} priority queue")
        return job_id
    
    async def _worker(self, worker_id: int):
        """Worker processes jobs from queues"""
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Check queues in priority order
                job = await self._get_next_job()
                
                if job:
                    logger.info(f"Worker {worker_id} processing job {job.job_id}")
                    self.active_jobs[job.job_id] = worker_id
                    
                    try:
                        # Execute job with timeout
                        await asyncio.wait_for(
                            job.func(),
                            timeout=300  # 5 minute timeout
                        )
                        
                        logger.info(f"Job {job.job_id} completed")
                        await self._mark_complete(job.job_id)
                    
                    except asyncio.TimeoutError:
                        logger.error(f"Job {job.job_id} timed out")
                        await self._handle_job_failure(job, "timeout")
                    
                    except Exception as e:
                        logger.error(f"Job {job.job_id} failed: {e}")
                        await self._handle_job_failure(job, str(e))
                    
                    finally:
                        self.active_jobs.pop(job.job_id, None)
                
                else:
                    # No jobs available, sleep briefly
                    await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)
    
    async def _get_next_job(self) -> Optional[Job]:
        """Get next job from highest priority non-empty queue"""
        
        # Try high priority first
        if not self.high_priority_queue.empty():
            _, job = await self.high_priority_queue.get()
            return job
        
        # Then normal priority
        if not self.normal_priority_queue.empty():
            _, job = await self.normal_priority_queue.get()
            return job
        
        # Finally low priority
        if not self.low_priority_queue.empty():
            _, job = await self.low_priority_queue.get()
            return job
        
        return None
    
    async def _handle_job_failure(self, job: Job, error: str):
        """Handle job failure with retry logic"""
        
        job.retries += 1
        
        if job.retries < self.max_retries:
            # Exponential backoff
            delay = self.retry_delays[min(job.retries - 1, len(self.retry_delays) - 1)]
            
            logger.info(
                f"Retrying job {job.job_id} in {delay}s "
                f"(attempt {job.retries}/{self.max_retries})"
            )
            
            # Re-queue with delay
            await asyncio.sleep(delay)
            await self.add_job(job.job_id, job.func, job.priority)
        
        else:
            # Max retries exceeded
            logger.error(f"Job {job.job_id} failed after {self.max_retries} attempts")
            await self._mark_failed(job.job_id, error)
    
    async def _heartbeat_monitor(self):
        """Monitor job heartbeats and trigger failover"""
        
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            
            current_time = time.time()
            
            for job_id, last_heartbeat in list(self.job_heartbeats.items()):
                time_since_heartbeat = current_time - last_heartbeat
                
                if time_since_heartbeat > self.heartbeat_timeout:
                    logger.warning(
                        f"Job {job_id} heartbeat timeout "
                        f"({time_since_heartbeat:.0f}s)"
                    )
                    
                    # Check if job is still active
                    if job_id in self.active_jobs:
                        worker_id = self.active_jobs[job_id]
                        logger.error(
                            f"Worker {worker_id} appears stuck on job {job_id}. "
                            f"Triggering failover..."
                        )
                        
                        # Mark job as failed for retry
                        await self._trigger_failover(job_id)
    
    async def update_heartbeat(self, job_id: str):
        """Update job heartbeat timestamp"""
        self.job_heartbeats[job_id] = time.time()
```

#### 2. Job Status Tracking

```python
class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

async def _mark_complete(self, job_id: str):
    """Mark job as complete in Firestore"""
    await db.collection("jobs").document(job_id).update({
        "status": JobStatus.COMPLETED,
        "completed_at": firestore.SERVER_TIMESTAMP
    })
    
    # Clean up heartbeat
    self.job_heartbeats.pop(job_id, None)
    
    # Notify via WebSocket
    await self._notify_completion(job_id)

async def _mark_failed(self, job_id: str, error: str):
    """Mark job as failed in Firestore"""
    await db.collection("jobs").document(job_id).update({
        "status": JobStatus.FAILED,
        "error": error,
        "failed_at": firestore.SERVER_TIMESTAMP
    })
    
    # Clean up heartbeat
    self.job_heartbeats.pop(job_id, None)
    
    # Notify via WebSocket
    await self._notify_failure(job_id, error)
```

---

## Conversational AI (WebRTC)

### Architecture

The conversational AI system uses **Pipecat** framework for WebRTC orchestration with **pipeline-based audio processing**.

```
Mobile App                     Server (Pipecat)                  AI Services
    │                                │                                │
    │  1. Start Session              │                                │
    ├───────────────────────────────>│                                │
    │  {user_id, child_name}         │                                │
    │                                │                                │
    │  2. Session Created            │                                │
    │<───────────────────────────────┤                                │
    │  {session_id, ice_servers}     │                                │
    │                                │                                │
    │  3. WebRTC Offer (SDP)         │                                │
    ├───────────────────────────────>│                                │
    │                                │                                │
    │  4. WebRTC Answer (SDP)        │                                │
    │<───────────────────────────────┤                                │
    │                                │                                │
    │  5. ICE Candidates             │                                │
    ├──────────────────────────────> │                                │
    │<───────────────────────────────┤                                │
    │                                │                                │
    │  === Connection Established ===                                │
    │                                │                                │
    │  6. Audio Stream (User Speech) │                                │
    ├───────────────────────────────>│   7. Speech-to-Text           │
    │                                ├──────────────────────────────>│
    │                                │   (Deepgram)                   │
    │                                │                                │
    │                                │   8. Text Response             │
    │                                │<───────────────────────────────┤
    │                                │   "Once upon a time..."        │
    │                                │                                │
    │                                │   9. LLM Processing            │
    │                                ├──────────────────────────────>│
    │                                │   (OpenAI)                     │
    │                                │                                │
    │                                │   10. Response Text            │
    │                                │<───────────────────────────────┤
    │                                │                                │
    │                                │   11. Text-to-Speech           │
    │                                ├──────────────────────────────>│
    │                                │   (Cartesia)                   │
    │                                │                                │
    │  12. Audio Stream (AI Speech)  │   13. Audio Data               │
    │<───────────────────────────────┤<───────────────────────────────┤
    │                                │                                │
```

### Implementation

#### 1. Pipecat Pipeline Setup (`app/services/conversation_service.py`)

```python
from pipecat.transports.webrtc import SmallWebRTCTransport
from pipecat.processors import (
    STTProcessor,
    LLMProcessor,
    TTSProcessor,
    PipelineProcessor
)

class ConversationService:
    async def create_session(
        self, 
        user_id: str, 
        child_name: str,
        config: SessionConfig
    ) -> ConversationSession:
        """Create new conversational AI session"""
        
        session_id = str(uuid.uuid4())
        
        # Initialize transport (WebRTC)
        transport = SmallWebRTCTransport(
            ice_servers=[
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]}
            ]
        )
        
        # Build processing pipeline
        pipeline = await self._build_pipeline(child_name, config)
        
        # Create session
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            transport=transport,
            pipeline=pipeline,
            created_at=time.time()
        )
        
        # Store session
        self.active_sessions[session_id] = session
        
        # Start pipeline
        await pipeline.start()
        
        logger.info(f"Conversation session {session_id} created")
        
        return session
    
    async def _build_pipeline(
        self, 
        child_name: str, 
        config: SessionConfig
    ) -> PipelineProcessor:
        """Build Pipecat processing pipeline"""
        
        # Speech-to-Text processor (Deepgram)
        stt = STTProcessor(
            api_key=settings.DEEPGRAM_API_KEY,
            model="nova-2",
            language="en-US",
            interim_results=True
        )
        
        # Language Model processor (OpenAI)
        llm = LLMProcessor(
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4",
            system_prompt=self._get_system_prompt(child_name),
            temperature=0.7,
            max_tokens=150
        )
        
        # Text-to-Speech processor (Cartesia)
        tts = TTSProcessor(
            api_key=settings.CARTESIA_API_KEY,
            voice_id=config.voice_id or "default",
            speed=1.0,
            emotion="friendly"
        )
        
        # Assemble pipeline
        pipeline = PipelineProcessor([
            stt,      # Audio in → Text
            llm,      # Text → Response Text
            tts       # Response Text → Audio out
        ])
        
        return pipeline
    
    def _get_system_prompt(self, child_name: str) -> str:
        """Get LLM system prompt for storytelling character"""
        return f"""You are June, a friendly and wise storytelling owl. 
You love telling stories to children and answering their questions.

You are currently talking to {child_name}, a curious and imaginative child.

Guidelines:
- Keep responses short (2-3 sentences)
- Use age-appropriate language
- Be encouraging and positive
- Stay in character as June the owl
- When asked about stories, offer to tell one
- When telling a story, make it interactive
- Ask questions to engage the child

Current conversation context: Interactive storytelling session
"""
```

#### 2. WebRTC Signaling (`app/routers/conversation.py`)

```python
@router.post("/{session_id}/offer")
async def handle_webrtc_offer(
    session_id: str,
    offer: WebRTCOffer
) -> WebRTCAnswer:
    """Handle WebRTC offer from client"""
    
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Process offer through transport
    answer = await session.transport.handle_offer(
        sdp=offer.sdp,
        type=offer.type
    )
    
    logger.info(f"WebRTC offer processed for session {session_id}")
    
    return WebRTCAnswer(
        sdp=answer["sdp"],
        type=answer["type"]
    )

@router.patch("/{session_id}/candidate")
async def add_ice_candidate(
    session_id: str,
    candidate: ICECandidate
):
    """Add ICE candidate for WebRTC connection"""
    
    session = conversation_service.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    await session.transport.add_ice_candidate(
        candidate=candidate.candidate,
        sdp_mid=candidate.sdpMid,
        sdp_mline_index=candidate.sdpMLineIndex
    )
    
    return {"success": True}
```

#### 3. Context Management

**Maintaining conversation context across turns**:

```python
class ContextManager:
    def __init__(self):
        self.contexts = {}  # session_id -> context
    
    async def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str
    ):
        """Add message to conversation history"""
        if session_id not in self.contexts:
            self.contexts[session_id] = []
        
        self.contexts[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # Keep last 10 messages only
        if len(self.contexts[session_id]) > 10:
            self.contexts[session_id] = self.contexts[session_id][-10:]
    
    async def get_context(self, session_id: str) -> List[Dict]:
        """Get conversation history for LLM"""
        return self.contexts.get(session_id, [])
    
    async def clear_context(self, session_id: str):
        """Clear conversation history"""
        self.contexts.pop(session_id, None)
```

---

## IoT Device Management

### Architecture

ESP32 devices use **HMAC-based authentication** and maintain **persistent sessions** with **heartbeat monitoring**.

```
Device Lifecycle:
1. Admin creates device → QR code generated
2. User scans QR code → Claim token generated
3. Device claims with token → Authenticated
4. Device establishes session → Heartbeat starts
5. Device receives commands → Executes actions
6. Device reports status → Updates Firestore
```

### Implementation

#### 1. Device Creation (`app/routers/iot.py`)

```python
@router.post("/devices/create")
async def create_device(
    request: DeviceCreateRequest,
    user_id: str = Depends(require_admin)
):
    """Create new IoT device (admin only)"""
    
    device_id = str(uuid.uuid4())
    device_secret = secrets.token_urlsafe(32)
    
    # Store in Firestore
    await db.collection("iot_devices").document(device_id).set({
        "device_id": device_id,
        "device_name": request.device_name,
        "mac_address": request.mac_address,
        "device_secret_hash": hash_secret(device_secret),
        "status": "unclaimed",
        "created_at": firestore.SERVER_TIMESTAMP,
        "created_by": user_id
    })
    
    # Generate QR code data
    qr_data = f"STDEV:{device_id}:{device_secret}"
    
    return {
        "success": True,
        "device_id": device_id,
        "device_secret": device_secret,  # Show once only
        "qr_code_data": qr_data
    }
```

#### 2. Device Authentication Middleware

```python
# app/middleware/iot_auth.py

import hmac
import hashlib

async def verify_device_signature(
    device_id: str,
    device_secret: str,
    request_data: Dict
) -> bool:
    """Verify HMAC signature from device"""
    
    # Get device from Firestore
    device_doc = await db.collection("iot_devices").document(device_id).get()
    
    if not device_doc.exists:
        return False
    
    device_data = device_doc.to_dict()
    stored_secret_hash = device_data["device_secret_hash"]
    
    # Verify secret
    if not verify_password(device_secret, stored_secret_hash):
        return False
    
    # Verify HMAC signature
    expected_signature = hmac.new(
        device_secret.encode(),
        json.dumps(request_data, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    
    received_signature = request_data.get("signature")
    
    return hmac.compare_digest(expected_signature, received_signature)

def require_device_auth(
    device_id: str = Body(...),
    device_secret: str = Body(...),
    request: Request = None
):
    """Dependency for device authentication"""
    
    async def _verify():
        request_data = await request.json()
        
        is_valid = await verify_device_signature(
            device_id,
            device_secret,
            request_data
        )
        
        if not is_valid:
            raise HTTPException(403, "Invalid device credentials")
        
        return device_id
    
    return _verify
```

#### 3. Device Claiming Flow

```python
@router.post("/devices/claim-token")
async def get_claim_token(
    firebase_token: str,
    user_id: str = Depends(get_current_user)
):
    """Generate claim token for user"""
    
    # Create short-lived JWT
    claim_token = jwt.encode(
        {
            "user_id": user_id,
            "type": "device_claim",
            "exp": datetime.utcnow() + timedelta(minutes=10)
        },
        settings.JWT_SECRET,
        algorithm="HS256"
    )
    
    return {
        "claim_token": claim_token,
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
    }

@router.post("/devices/claim")
async def claim_device(
    device_id: str = Body(...),
    device_secret: str = Body(...),
    claim_token: str = Body(...)
):
    """Claim device to user account"""
    
    # Verify device credentials
    device_valid = await verify_device_signature(device_id, device_secret, {})
    if not device_valid:
        raise HTTPException(403, "Invalid device credentials")
    
    # Verify claim token
    try:
        payload = jwt.decode(
            claim_token,
            settings.JWT_SECRET,
            algorithms=["HS256"]
        )
        user_id = payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Claim token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid claim token")
    
    # Update device ownership
    await db.collection("iot_devices").document(device_id).update({
        "claimed_by": user_id,
        "claimed_at": firestore.SERVER_TIMESTAMP,
        "status": "active"
    })
    
    return {"success": True, "message": "Device claimed successfully"}
```

#### 4. Device Session Management

```python
class DeviceSessionManager:
    def __init__(self):
        self.active_sessions = {}
        self.heartbeat_timeout = 60  # seconds
    
    async def start_session(
        self, 
        device_id: str, 
        session_data: Dict
    ) -> str:
        """Start new device session"""
        
        session_id = str(uuid.uuid4())
        
        session = DeviceSession(
            session_id=session_id,
            device_id=device_id,
            started_at=time.time(),
            last_heartbeat=time.time(),
            data=session_data
        )
        
        self.active_sessions[device_id] = session
        
        # Start heartbeat monitor
        asyncio.create_task(self._monitor_heartbeat(device_id))
        
        return session_id
    
    async def update_heartbeat(self, device_id: str):
        """Update device heartbeat"""
        if device_id in self.active_sessions:
            self.active_sessions[device_id].last_heartbeat = time.time()
    
    async def _monitor_heartbeat(self, device_id: str):
        """Monitor device heartbeat"""
        while device_id in self.active_sessions:
            await asyncio.sleep(self.heartbeat_timeout / 2)
            
            session = self.active_sessions[device_id]
            time_since_heartbeat = time.time() - session.last_heartbeat
            
            if time_since_heartbeat > self.heartbeat_timeout:
                logger.warning(f"Device {device_id} heartbeat timeout")
                await self._end_session(device_id)
                break
    
    async def _end_session(self, device_id: str):
        """End device session"""
        session = self.active_sessions.pop(device_id, None)
        
        if session:
            # Update Firestore
            await db.collection("iot_devices").document(device_id).update({
                "status": "offline",
                "last_seen": firestore.SERVER_TIMESTAMP
            })
```

---

## Media Processing

### Audio Processing

**Format Conversion & Optimization**:

```python
import pydub
from pydub import AudioSegment

class AudioProcessor:
    async def process_audio(
        self, 
        audio_bytes: bytes,
        output_format: str = "wav"
    ) -> bytes:
        """Process and optimize audio"""
        
        # Load audio
        audio = AudioSegment.from_file(
            io.BytesIO(audio_bytes),
            format="wav"
        )
        
        # Normalize volume
        audio = self._normalize_volume(audio)
        
        # Apply fade in/out
        audio = audio.fade_in(100).fade_out(100)
        
        # Convert to target format
        output = io.BytesIO()
        audio.export(
            output,
            format=output_format,
            parameters=[
                "-ar", "44100",  # Sample rate
                "-ac", "1",      # Mono
                "-b:a", "128k"   # Bitrate
            ]
        )
        
        return output.getvalue()
    
    def _normalize_volume(self, audio: AudioSegment) -> AudioSegment:
        """Normalize audio volume"""
        target_dBFS = -20.0
        change_in_dBFS = target_dBFS - audio.dBFS
        return audio.apply_gain(change_in_dBFS)
    
    async def calculate_duration(self, audio_bytes: bytes) -> float:
        """Calculate audio duration in seconds"""
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        return len(audio) / 1000.0  # milliseconds to seconds
```

### Image Processing

**Resizing & Optimization**:

```python
from PIL import Image
import io

class ImageProcessor:
    async def process_image(
        self, 
        image_bytes: bytes,
        sizes: Dict[str, Tuple[int, int]] = None
    ) -> Dict[str, bytes]:
        """Process and resize images for different devices"""
        
        if sizes is None:
            sizes = {
                "original": (1024, 1024),
                "large": (800, 800),
                "medium": (512, 512),
                "thumbnail": (256, 256)
            }
        
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        results = {}
        
        for size_name, (width, height) in sizes.items():
            # Resize maintaining aspect ratio
            resized = image.copy()
            resized.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Create canvas for exact dimensions
            canvas = Image.new("RGB", (width, height), (255, 255, 255))
            
            # Center image on canvas
            x = (width - resized.width) // 2
            y = (height - resized.height) // 2
            canvas.paste(resized, (x, y))
            
            # Save to bytes
            output = io.BytesIO()
            canvas.save(
                output,
                format="PNG",
                optimize=True,
                quality=85
            )
            
            results[size_name] = output.getvalue()
        
        return results
```

---

## Authentication & Security

### JWT Token Management

```python
import jwt
from datetime import datetime, timedelta

class TokenManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=30)
    
    def create_access_token(self, user_id: str) -> str:
        """Create JWT access token"""
        payload = {
            "user_id": user_id,
            "type": "access",
            "exp": datetime.utcnow() + self.access_token_expire
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + self.refresh_token_expire
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
```

### Input Sanitization

```python
import re
import html

class InputSanitizer:
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize user input text"""
        # Remove HTML tags
        text = html.escape(text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        
        # Limit length
        max_length = 5000
        text = text[:max_length]
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
```

---

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
import asyncio

class CacheManager:
    def __init__(self):
        self.cache = {}
        self.ttl = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if key in self.cache:
            if time.time() < self.ttl.get(key, 0):
                return self.cache[key]
            else:
                # Expired
                del self.cache[key]
                del self.ttl[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set cached value with TTL"""
        self.cache[key] = value
        self.ttl[key] = time.time() + ttl
    
    async def invalidate(self, key: str):
        """Invalidate cached value"""
        self.cache.pop(key, None)
        self.ttl.pop(key, None)

# Usage
cache = CacheManager()

@lru_cache(maxsize=1000)
async def get_user_profile(user_id: str):
    """Get user profile with caching"""
    cached = await cache.get(f"user:{user_id}")
    if cached:
        return cached
    
    profile = await db.collection("users").document(user_id).get()
    await cache.set(f"user:{user_id}", profile.to_dict(), ttl=600)
    
    return profile.to_dict()
```

### Database Query Optimization

```python
# Batch reads
async def get_multiple_stories(story_ids: List[str]):
    """Fetch multiple stories in single batch"""
    docs = await db.collection("stories").where(
        "__name__", "in", story_ids
    ).get()
    return [doc.to_dict() for doc in docs]

# Pagination
async def list_stories_paginated(
    user_id: str,
    limit: int = 20,
    start_after: Optional[str] = None
):
    """List stories with cursor-based pagination"""
    query = db.collection("stories") \\
        .where("user_id", "==", user_id) \\
        .order_by("created_at", direction="DESCENDING") \\
        .limit(limit)
    
    if start_after:
        # Get start_after document
        doc = await db.collection("stories").document(start_after).get()
        query = query.start_after(doc)
    
    docs = await query.get()
    stories = [doc.to_dict() for doc in docs]
    
    return {
        "stories": stories,
        "next_cursor": stories[-1]["story_id"] if stories else None
    }
```

---

## Error Handling & Resilience

### Retry Mechanism

```python
import asyncio
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0
):
    """Decorator for retry with exponential backoff"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    
                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator

# Usage
@retry_with_backoff(max_retries=3)
async def generate_image(prompt: str):
    return await seedream_service.generate(prompt)
```

### Circuit Breaker

```python
class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker"""
        
        # Check if circuit is open
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failures
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            
            return result
        
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
                logger.error(f"Circuit breaker opened after {self.failures} failures")
            
            raise
```

---

This completes the comprehensive technical deep-dive documentation covering all major implementation details of the ESP32 Storytelling Server system.
