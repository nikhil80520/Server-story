"""WebSocket endpoint for lullaby generation real-time notifications"""
import json
import asyncio
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.dependencies import verify_firebase_token
from app.services.infrastructure import lullaby_websocket_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/lullabies/{user_token}")
async def lullaby_websocket_endpoint(websocket: WebSocket, user_token: str):
    """
    WebSocket endpoint for lullaby generation notifications.
    
    Client connects to this endpoint to receive real-time updates about lullaby generation.
    
    Connection URL:
        ws://your-api.com/ws/lullabies/<firebase_token>
    
    Events received by client:
        - connected: Confirmation of successful connection
        - subscribed: Confirmation of subscription to a lullaby
        - lullaby_progress: Progress updates during generation
            - status: Current generation stage (starting, generating_lyrics, lyrics_complete, music_complete, upload_complete)
            - progress: Percentage complete (0-100)
            - message: Human-readable status message
            - lyrics: Lyrics text (when lyrics_complete)
        - lullaby_completed: Generation finished successfully
            - lullaby: Complete lullaby metadata with audio_url
        - lullaby_failed: Generation failed
            - error: Error message
        - heartbeat: Keep-alive ping (every 30 seconds)
    
    Client can send:
        - {"action": "subscribe", "lullaby_id": "..."}: Subscribe to updates for specific lullaby
        - {"action": "unsubscribe", "lullaby_id": "..."}: Unsubscribe from lullaby updates
        - {"action": "ping"}: Request heartbeat response
    
    Args:
        websocket: WebSocket connection
        user_token: Firebase authentication token (query parameter)
    
    Example client usage:
        ```javascript
        const token = await firebase.auth().currentUser.getIdToken();
        const ws = new WebSocket(`wss://api.example.com/ws/lullabies/${token}`);
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Event:', data.event, data);
            
            if (data.event === 'lullaby_completed') {
                playAudio(data.lullaby.audio_url);
            }
        };
        ```
    """
    connection = None
    user_id = None
    
    try:
        # Verify Firebase token
        user_id = await verify_firebase_token(user_token)
        print(f"🔌 Lullaby WebSocket: Token verified for user {user_id}")
        
        # Create WebSocket connection
        connection = await lullaby_websocket_manager.connect(websocket, user_id)
        print(f"✅ Lullaby WebSocket connected for user {user_id}")
        
        # Main message loop
        while True:
            try:
                # Wait for message from client with 30-second timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                # Handle client messages (subscribe, unsubscribe, ping)
                await lullaby_websocket_manager.handle_message(connection, message)
                
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "event": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    print(f"❌ Failed to send heartbeat: {e}")
                    break
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid JSON received: {e}")
                try:
                    await websocket.send_text(json.dumps({
                        "event": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except:
                    break
    
    except WebSocketDisconnect:
        print(f"🔌 Lullaby WebSocket disconnected for user {user_id if connection else 'unknown'}")
        if connection:
            await lullaby_websocket_manager.disconnect(connection)
    
    except Exception as e:
        print(f"❌ Lullaby WebSocket error: {e}")
        if connection:
            await lullaby_websocket_manager.disconnect(connection)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
