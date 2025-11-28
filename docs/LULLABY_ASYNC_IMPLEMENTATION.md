# Lullaby Async Generation - Implementation Summary

## Changes Made

### 1. Created `/app/services/infrastructure/lullaby_websocket_manager.py`
- WebSocket manager for lullaby generation notifications
- Reuses same pattern as story_websocket_manager
- Handles subscribe/unsubscribe to specific lullaby IDs
- Broadcasts progress, completion, and error events

### 2. Updated `/app/services/infrastructure/__init__.py`
- Added exports for `LullabyWebSocketManager` and `lullaby_websocket_manager`

### 3. Need to Update `/app/services/content/lullaby_service.py`
Add async background generation method:

```python
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
    Generate lullaby asynchronously with progress callbacks
    Used by background task service
    """
    try:
        # Notify: Starting
        if progress_callback:
            await progress_callback({
                "status": "starting",
                "progress": 0,
                "message": "Initializing lullaby generation..."
            })
        
        # Get child profile if needed
        child_name, child_age, child_interests = None, None, None
        if child_id:
            try:
                from app.services.content.child_service import child_service
                child_profile = await child_service.get_child(user_id, child_id)
                if child_profile:
                    child_name = child_profile.name
                    child_age = child_profile.age
                    child_interests = child_profile.interests
            except Exception as e:
                print(f"⚠️ Could not fetch child profile: {e}")
        
        # Step 1: Generate lyrics (25% progress)
        if progress_callback:
            await progress_callback({
                "status": "generating_lyrics",
                "progress": 10,
                "message": "Generating personalized lyrics..."
            })
        
        lyrics = await self.generate_lyrics(description, child_name, child_age, child_interests)
        
        if progress_callback:
            await progress_callback({
                "status": "lyrics_complete",
                "progress": 25,
                "message": "Lyrics generated! Creating music...",
                "lyrics": lyrics
            })
        
        # Step 2: Generate music (75% progress)
        prompt = "soft, loving, lullaby, sleep music, gentle piano, calm"
        audio_data = await self.generate_music(lyrics, prompt)
        
        if progress_callback:
            await progress_callback({
                "status": "music_complete",
                "progress": 75,
                "message": "Music generated! Uploading to storage..."
            })
        
        # Step 3: Upload to Firebase Storage (90% progress)
        audio_url = await self.store_lullaby_audio(audio_data, lullaby_id, user_id)
        
        if progress_callback:
            await progress_callback({
                "status": "upload_complete",
                "progress": 90,
                "message": "Upload complete! Saving metadata..."
            })
        
        # Step 4: Save metadata (100% progress)
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
        
        # Notify completion
        if completion_callback:
            await completion_callback({
                "status": "completed",
                "lullaby": metadata.model_dump()
            })
        
        return metadata
        
    except Exception as e:
        print(f"❌ Async lullaby generation failed: {e}")
        if completion_callback:
            await completion_callback({
                "status": "failed",
                "error": str(e)
            })
        raise
```

### 4. Need to Update `/app/routers/content/lullabies.py`
Replace synchronous generation with async:

```python
@router.post("/generate", response_model=LullabyGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_lullaby_async(
    request: LullabyGenerateRequest,
    current_user: User = Depends(require_active_account),
    lullaby_service: LullabyService = Depends(get_lullaby_service),
    user_service: UserService = Depends(get_user_service)
):
    """Start async lullaby generation with WebSocket notifications"""
    try:
        user_id = current_user.uid
        
        # Verify user profile
        user_profile = await user_service.get_user_profile(user_id)
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Validate child if provided
        if request.child_id:
            from app.services.content.child_service import child_service
            child_profile = await child_service.get_child(user_id, request.child_id)
            if not child_profile:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child profile not found: {request.child_id}"
                )
        
        # Generate lullaby ID
        lullaby_id = f"lullaby_{uuid.uuid4().hex[:12]}"
        
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
        
        # WebSocket callbacks
        from app.services.infrastructure import lullaby_websocket_manager
        
        async def on_progress(data):
            await lullaby_websocket_manager.broadcast_to_user(user_id, {
                "event": "lullaby_progress",
                "lullaby_id": lullaby_id,
                "status": data.get("status"),
                "progress": data.get("progress"),
                "message": data.get("message"),
                "lyrics": data.get("lyrics"),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        async def on_completion(data):
            if data.get("status") == "completed":
                await lullaby_websocket_manager.broadcast_to_user(user_id, {
                    "event": "lullaby_completed",
                    "lullaby_id": lullaby_id,
                    "lullaby": data.get("lullaby"),
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
        
        # Start background task
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
            websocket_endpoint=f"/ws/lullabies"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to start lullaby generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {str(e)}"
        )
```

### 5. Need to Create `/app/routers/social/lullaby_websocket.py`

```python
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.dependencies import verify_firebase_token
from app.services.infrastructure import lullaby_websocket_manager

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/lullabies")
async def lullaby_websocket_endpoint(websocket: WebSocket, user_token: str):
    """WebSocket endpoint for lullaby generation notifications"""
    connection = None
    
    try:
        # Verify token
        user_id = await verify_firebase_token(user_token)
        
        # Create WebSocket connection
        connection = await lullaby_websocket_manager.connect(websocket, user_id)
        print(f"✅ Lullaby WebSocket connected for user {user_id}")
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                # Handle client messages
                await lullaby_websocket_manager.handle_message(connection, message)
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({
                        "event": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    print(f"❌ Failed to send heartbeat: {e}")
                    break
            
    except WebSocketDisconnect:
        print(f"🔌 Lullaby WebSocket disconnected for user {user_id}")
        if connection:
            await lullaby_websocket_manager.disconnect(connection)
    except Exception as e:
        print(f"❌ Lullaby WebSocket error: {e}")
        if connection:
            await lullaby_websocket_manager.disconnect(connection)
```

### 6. Register WebSocket Route in `/app/core/app_init.py`

```python
from app.routers.social import lullaby_websocket
app.include_router(lullaby_websocket.router)
```

## Client Usage

### JavaScript/TypeScript Example

```typescript
// Connect to WebSocket
const token = await firebase.auth().currentUser.getIdToken();
const ws = new WebSocket(`wss://your-api.com/ws/lullabies?user_token=${token}`);

ws.onopen = () => {
  console.log('Connected to lullaby notifications');
  
  // Subscribe to specific lullaby (optional)
  ws.send(JSON.stringify({
    action: 'subscribe',
    lullaby_id: 'lullaby_abc123'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.event) {
    case 'connected':
      console.log('WebSocket connected');
      break;
      
    case 'lullaby_progress':
      console.log(`Progress: ${data.progress}% - ${data.message}`);
      if (data.lyrics) {
        console.log('Lyrics generated:', data.lyrics);
      }
      updateProgressBar(data.progress);
      break;
      
    case 'lullaby_completed':
      console.log('Lullaby ready!', data.lullaby);
      playLullaby(data.lullaby.audio_url);
      break;
      
    case 'lullaby_failed':
      console.error('Generation failed:', data.error);
      showError(data.message);
      break;
      
    case 'heartbeat':
      // Connection alive
      break;
  }
};

// Start generation
async function generateLullaby(description, childId) {
  const response = await fetch('/lullabies/generate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ description, child_id: childId })
  });
  
  const data = await response.json();
  console.log('Generation started:', data.lullaby_id);
  
  // WebSocket will handle updates
}
```

## Benefits

1. **Non-blocking**: API responds immediately (202 Accepted)
2. **Real-time updates**: Client gets progress via WebSocket
3. **Scalable**: Multiple lullabies can generate in parallel
4. **User-friendly**: Show progress bar, lyrics preview, status messages
5. **Resilient**: Client can reconnect to check status if connection drops
6. **Reuses infrastructure**: Same pattern as story generation

## Next Steps

1. Implement the async method in `lullaby_service.py`
2. Update the endpoint in `lullabies.py`  
3. Create WebSocket router
4. Register routes
5. Test end-to-end flow
6. Update documentation
