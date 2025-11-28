# ===== app/routers/websocket.py =====
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.dependencies import verify_firebase_token
from app.services.storage.storage_service import StorageService
from app.services.infrastructure.story_websocket_manager import story_websocket_manager

router = APIRouter(tags=["websocket"])
storage_service = StorageService()

@router.websocket("/ws/stories/{user_token}")
async def story_websocket_endpoint(websocket: WebSocket, user_token: str):
    """WebSocket endpoint for story generation notifications"""
    connection = None
    
    try:
        # Verify token - this returns user_id string directly
        user_id = await verify_firebase_token(user_token)
        
        # Create WebSocket connection
        connection = await story_websocket_manager.connect(websocket, user_id)
        print(f"✅ WebSocket connected for user {user_id}")
        
        while True:
            # Wait for messages from client with timeout to allow heartbeat
            # Use asyncio.wait_for to prevent indefinite blocking
            import asyncio
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                # Handle client messages
                await story_websocket_manager.handle_message(connection, message)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_text(json.dumps({
                        "event": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    print(f"❌ Failed to send heartbeat to user {user_id}: {e}")
                    break
            
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected for user {user_id}")
        if connection:
            await story_websocket_manager.disconnect(connection)
    except Exception as e:
        print(f"❌ Story WebSocket error for user {user_token}: {str(e)}")
        if connection:
            await story_websocket_manager.disconnect(connection)

@router.websocket("/ws/{user_token}")
async def websocket_endpoint(websocket: WebSocket, user_token: str):
    """WebSocket endpoint for real-time communication with ESP32"""
    await websocket.accept()
    
    try:
        # Verify token - this returns user_id string directly
        user_id = await verify_firebase_token(user_token)
        
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "user_id": user_id,
            "message": "Connected successfully"
        }))
        
        while True:
            # Wait for messages from ESP32
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "story_status":
                # Handle story playback status from ESP32
                story_id = message.get("story_id")
                status = message.get("status")
                
                # Update story status
                await storage_service.update_story_status(story_id, status)
                
                # Send acknowledgment
                await websocket.send_text(json.dumps({
                    "type": "status_received",
                    "story_id": story_id,
                    "status": status
                }))
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.close()

@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics (for debugging)"""
    return story_websocket_manager.get_connection_stats()
